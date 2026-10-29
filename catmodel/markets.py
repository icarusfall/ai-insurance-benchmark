"""The market lens: prediction-market prices turned into model inputs, and the Markets preset built from them.

    python -m catmodel.markets            # what the snapshot implies, against the central settings
    python -m catmodel.markets --fetch    # refresh prices from Manifold, Polymarket and Kalshi (and Metaculus, with a token)

How each kind of question maps (see the header of sources/market_snapshot.yaml):

- rate: P(at least one event before the question closes) gives a Poisson intensity over the window, -ln(1 - P). Part
  of the growth over the window is capability, which the Over time chapter already models, so the intensity is divided
  by the integral of the peril's rate multiplier on the central capability path rather than by the window's length.
  That gives today's rate at the question's damage threshold; the peril's Pareto tail moves it to the peril's own event
  threshold xm: rate(xm) = rate(T) (T / xm) ^ alpha.
- agi: each question's median date for AGI. The preset stops the model at the horizon the central path reaches at the
  median of those medians.
- default: P(bankruptcy announced by a date) gives an annual hazard, -ln(1 - P) / years. The preset scales member
  calls by one minus the average hazard. That is generous: calls are needed in bad years, when members are weakest.
"""
import argparse
import json
import math
import os
import urllib.request
from datetime import date, timedelta
from statistics import median

import yaml

from .model import load
from .trajectory import horizon, load_capability

SNAPSHOT = os.path.join(os.path.dirname(__file__), "sources", "market_snapshot.yaml")
UA = {"User-Agent": "maim-catmodel/1.0"}


def load_snapshot(path: str = SNAPSHOT) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _d(s) -> date:
    return date.fromisoformat(str(s))


def rate_multiplier(c, trajectory: str, peril: str, when: date) -> float:
    ratio = horizon(c, trajectory, when) / horizon(c, trajectory, c.now)
    return min(c.cap_multiple[peril], ratio ** c.elasticity[peril])


def growth_years(c, trajectory: str, peril: str, start: date, end: date, step_days: int = 15) -> float:
    """Integral of the peril's rate multiplier from start to end, in years (equal to the years if nothing grows)."""
    total, d = 0.0, start
    while d < end:
        nxt = min(d + timedelta(days=step_days), end)
        mid = d + (nxt - d) / 2
        total += rate_multiplier(c, trajectory, peril, mid) * (nxt - d).days
        d = nxt
    return total / 365.25


def median_date(points: list) -> date | None:
    """Where a market's cumulative probability crosses 50%, by linear interpolation between its dates."""
    pts = sorted((_d(p["date"]), p["p"]) for p in points)
    prev_d, prev_p = None, 0.0
    for d, p in pts:
        if p >= 0.5:
            if prev_d is None:
                return d
            return prev_d + (d - prev_d) * ((0.5 - prev_p) / (p - prev_p))
        prev_d, prev_p = d, max(prev_p, p)
    return None


def implied(snapshot: dict | None = None, settings=None, capability=None) -> dict:
    """Every mapped question's implication, and the overrides that make up the Markets preset."""
    snap = snapshot or load_snapshot()
    s, c = settings or load(), capability or load_capability()
    taken = _d(snap["taken"])
    perils = {p.name: p for p in s.perils}
    rows, rates, medians, hazards = [], {}, [], []
    for q in snap["questions"]:
        m = q["mapping"]
        row = dict(id=q["id"], kind=m["kind"])
        if m["kind"] == "rate":
            p = perils[m["peril"]]
            closes = _d(q["closes"])
            years = (closes - taken).days / 365.25
            exposure = growth_years(c, c.trajectory, p.name, taken, closes)
            intensity = -math.log(1 - q["probability"]) * m["share"]
            at_threshold_now = intensity / exposure
            at_xm = at_threshold_now * (m["threshold_bn"] / p.severity.xm) ** p.severity.alpha
            model_at_threshold = p.rate * float(p.severity.sf(m["threshold_bn"]))
            row.update(peril=p.name, years=years, average_rate=intensity / years, rate_now=at_threshold_now,
                       implied_rate=at_xm, model_rate=p.rate, model_rate_at_threshold=model_at_threshold,
                       ratio=at_xm / p.rate)
            rates.setdefault(p.name, []).append(at_xm)
        elif m["kind"] == "agi":
            md = _d(q["median"]) if "median" in q else median_date(q["points"])
            row.update(median=md.isoformat() if md else None)
            if md:
                medians.append(md)
        elif m["kind"] == "default":
            pts = sorted((_d(p["date"]), p["p"]) for p in q["points"])
            d, p = pts[-1]
            h = -math.log(1 - p) / ((d - taken).days / 365.25)
            row.update(hazard=h, by=d.isoformat(), p=p)
            hazards.append(h)
        rows.append(row)
    preset = {}
    for peril, vals in rates.items():                  # geometric mean where two questions bear on one peril
        preset[f"{peril}.rate"] = math.exp(sum(math.log(v) for v in vals) / len(vals))
    agi = date.fromordinal(round(median(d.toordinal() for d in medians))) if medians else None
    if agi:
        preset["capability.stop_hours"] = horizon(c, c.trajectory, agi)
    if hazards:
        preset["callable_per_member"] = s.callable_per_member * (1 - sum(hazards) / len(hazards))
    return dict(taken=snap["taken"], rows=rows, agi_median=agi.isoformat() if agi else None,
                hazard=sum(hazards) / len(hazards) if hazards else None, preset=preset)


def apply_preset(settings, capability, preset: dict):
    """The central settings with the Markets preset's overrides."""
    from dataclasses import replace
    s, c = settings, capability
    for key, v in preset.items():
        if key.startswith("capability."):
            c = replace(c, **{key.split(".", 1)[1]: v})
        elif "." in key:
            peril, field = key.split(".")
            s = s.with_peril(peril, **{field: v})
        else:
            s = replace(s, **{key: v})
    return s, c


# ---- refreshing prices
def _get(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _manifold(slug: str) -> float:
    return float(_get(f"https://api.manifold.markets/v0/slug/{slug}")["probability"])


def _polymarket_points(slug: str) -> dict:
    ev = _get(f"https://gamma-api.polymarket.com/events?slug={slug}")[0]
    out = {}
    for m in ev["markets"]:
        if m.get("closed") or not m.get("outcomePrices"):
            continue
        end = (m.get("endDate") or "")[:10]
        out[end] = float(json.loads(m["outcomePrices"])[0])
    return out


def _kalshi_points(series: str) -> dict:
    ms = _get(f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series}&status=open&limit=100")["markets"]
    out = {}
    for m in ms:
        bid, ask = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
        if bid is None or ask is None:
            continue
        out[m["close_time"][:10]] = round((float(bid) + float(ask)) / 2, 4)
    return out


def _metaculus(post_id: int, token: str):
    d = _get(f"https://www.metaculus.com/api/posts/{post_id}/", {"Authorization": f"Token {token}"})
    latest = d["question"]["aggregations"]["recency_weighted"]["latest"]
    return latest["centers"][0]


def fetch(path: str = SNAPSHOT) -> list:
    """Refresh every question that has a public source; returns (id, old, new) for anything that changed."""
    snap = load_snapshot(path)
    token = os.environ.get("METACULUS_TOKEN")
    if not token:
        try:
            from agents.env import load_env              # the repo's .env loader, if present
            load_env()
            token = os.environ.get("METACULUS_TOKEN")
        except Exception:
            pass
    changes = []
    for q in snap["questions"]:
        f = q.get("fetch", {})
        try:
            if "manifold" in f:
                new = round(_manifold(f["manifold"]), 3)
                changes.append((q["id"], q.get("probability"), new)); q["probability"] = new
            elif "polymarket" in f:
                ev = _get(f"https://gamma-api.polymarket.com/events?slug={f['polymarket']}")[0]
                new = float(json.loads(ev["markets"][0]["outcomePrices"])[0])
                changes.append((q["id"], q.get("probability"), new)); q["probability"] = new
            elif "manifold_points" in f:
                pts = [{"date": d, "p": round(_manifold(slug), 3)} for d, slug in f["manifold_points"].items()]
                changes.append((q["id"], q.get("points"), pts)); q["points"] = pts
            elif "polymarket_points" in f or "kalshi_series" in f:
                got = _polymarket_points(f["polymarket_points"]) if "polymarket_points" in f else _kalshi_points(f["kalshi_series"])
                pts = [{"date": d, "p": p} for d, p in sorted(got.items())]
                if pts:
                    changes.append((q["id"], q.get("points"), pts)); q["points"] = pts
            elif f.get("manual") and token and "metaculus.com/questions/" in q["url"]:
                pid = int(q["url"].split("/questions/")[1].split("/")[0])
                v = _metaculus(pid, token)
                if "median" in q:
                    new = date.fromtimestamp(v).isoformat(); changes.append((q["id"], q["median"], new)); q["median"] = new
                else:
                    changes.append((q["id"], q["probability"], v)); q["probability"] = v
        except Exception as e:                            # one failed source should not lose the others
            changes.append((q["id"], "error", str(e)[:80]))
    snap["taken"] = date.today().isoformat()
    _write(snap, path)
    return changes


def _write(snap: dict, path: str):
    """Rewrite the snapshot, keeping the explanatory header."""
    with open(path, encoding="utf-8") as f:
        header = "".join(line for line in f if line.startswith("#"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(snap, f, sort_keys=False, allow_unicode=True, width=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        for qid, old, new in fetch():
            print(f"  {qid:34} {old!s:>12.40} -> {new!s:.60}")
    r = implied()
    print(f"\nSnapshot {r['taken']}")
    for row in r["rows"]:
        if row["kind"] == "rate":
            print(f"  {row['id']:34} {row['peril']:14} average {row['average_rate']:.3f}/yr at threshold, today {row['rate_now']:.3f};"
                  f" implied rate at xm {row['implied_rate']:.3f} vs model {row['model_rate']:.3f} ({row['ratio']:.1f}x)")
        elif row["kind"] == "agi":
            print(f"  {row['id']:34} AGI median {row['median']}")
        elif row["kind"] == "default":
            print(f"  {row['id']:34} bankruptcy {row['p']:.1%} by {row['by']}: hazard {row['hazard']:.1%} a year")
    print(f"\nMarkets preset (median AGI date {r['agi_median']}):")
    for k, v in r["preset"].items():
        print(f"  {k} = {v:.4g}")


if __name__ == "__main__":
    main()
