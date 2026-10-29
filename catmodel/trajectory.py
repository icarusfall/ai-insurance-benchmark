"""How the mutual fares year by year as AI capability grows.

    python -m catmodel.trajectory                    # every trajectory, central settings
    python -m catmodel.trajectory --level pessimistic

Capability is METR's 50% time horizon, in hours. From a shared anchor (the best measured model, April 2026) it follows
one of four paths:

- ai2027: AI 2027's superexponential trend, each doubling 10% shorter than the last, slowed by a pace factor. It reaches
  an infinite horizon in finite time.
- metr_2023: METR's exponential trend for models since 2023 (a 129-day doubling).
- metr_long_run: METR's trend for all models since 2019 (188 days).
- plateau: starts at the metr_2023 slope, then flattens towards a ceiling. In log hours it closes the gap to the ceiling
  exponentially, which is the top half of a sigmoid.

Each year's peril rates are today's times min(cap, (H(year) / H(now)) ^ elasticity), with H read at mid-year. Members'
revenue grows by a constant factor a year. The projection stops in the first year the horizon reaches `stop_hours`:
past that the AI 2027 authors expect AGI within about a year, and loss of control is out of scope.
"""
import argparse
import math
from dataclasses import dataclass, replace
from datetime import date

import yaml

from .model import DEFAULTS, Settings, _pick, load, simulate
from .pricing import build_stack
from .capital_s2 import solvency2
from .reserves import reserves

TRAJECTORIES = ("ai2027", "metr_2023", "metr_long_run", "plateau")
LABELS = {"ai2027": "AI 2027", "metr_2023": "METR trend since 2023", "metr_long_run": "METR long-run trend",
          "plateau": "Plateau"}


@dataclass(frozen=True)
class Capability:
    anchor_date: date
    anchor_hours: float
    now: date
    first_year: int
    last_year: int
    trajectory: str
    metr_2023_doubling_days: float
    metr_long_run_doubling_days: float
    ai2027_doubling_days: float
    ai2027_shrink: float
    ai2027_pace: float
    plateau_ceiling_hours: float
    stop_hours: float
    revenue_growth: float
    elasticity: dict
    cap_multiple: dict


def load_capability(level: str = "central", path: str = DEFAULTS) -> Capability:
    with open(path, encoding="utf-8") as f:
        c = yaml.safe_load(f)["capability"]
    flat = {k: _pick(v, level) for k, v in c.items() if k not in ("elasticity", "cap_multiple")}
    for k in ("anchor_date", "now"):
        flat[k] = date.fromisoformat(str(flat[k]))
    return Capability(**flat, elasticity={p: _pick(v, level) for p, v in c["elasticity"].items()},
                      cap_multiple={p: _pick(v, level) for p, v in c["cap_multiple"].items()})


def horizon(c: Capability, trajectory: str, when: date) -> float:
    """50% time horizon in hours on a date, under a trajectory. Infinite once a superexponential path blows up."""
    t = (when - c.anchor_date).days
    h0 = c.anchor_hours
    if trajectory == "metr_2023":
        return h0 * 2 ** (t / c.metr_2023_doubling_days)
    if trajectory == "metr_long_run":
        return h0 * 2 ** (t / c.metr_long_run_doubling_days)
    if trajectory == "ai2027":
        d, s = c.ai2027_doubling_days / c.ai2027_pace, c.ai2027_shrink
        x = 1 - t * (1 - s) / d                  # n doublings take d (1 - s^n) / (1 - s) days
        return math.inf if x <= 0 else h0 * 2 ** (math.log(x) / math.log(s))
    if trajectory == "plateau":
        gap = math.log2(c.plateau_ceiling_hours / h0)
        if gap <= 0:
            return h0
        return 2 ** (math.log2(c.plateau_ceiling_hours) - gap * math.exp(-t / (c.metr_2023_doubling_days * gap)))
    raise ValueError(f"unknown trajectory {trajectory!r}")


def multipliers(c: Capability, trajectory: str, year: int) -> dict:
    """Mid-year horizon, each peril's rate multiplier, and the revenue multiplier, relative to now."""
    mid, h_now = date(year, 7, 1), horizon(c, trajectory, c.now)
    h = horizon(c, trajectory, mid)
    ratio = h / h_now
    rates = {p: min(c.cap_multiple[p], ratio ** k) for p, k in c.elasticity.items()}
    return dict(year=year, horizon=h, stopped=h >= c.stop_hours, rates=rates,
                revenue=c.revenue_growth ** ((mid - c.now).days / 365.25))


def year_settings(s: Settings, m: dict) -> Settings:
    perils = tuple(replace(p, rate=p.rate * m["rates"].get(p.name, 1.0)) for p in s.perils)
    return replace(s, perils=perils, revenue=s.revenue * m["revenue"])


def project(s: Settings, c: Capability, trajectory: str | None = None, n_years: int = 50_000, seed: int = 0) -> list:
    """One row per year from first_year to last_year; rows past the stop carry no simulated results."""
    trajectory = trajectory or c.trajectory
    rows = []
    for year in range(c.first_year, c.last_year + 1):
        m = multipliers(c, trajectory, year)
        row = dict(m)
        if not m["stopped"] and not (rows and rows[-1]["stopped"]):
            sy = year_settings(s, m)
            y = simulate(sy, n_years, seed + year)
            st = build_stack(sy, y)
            gross = float(st.claims.mean())
            res = reserves(sy, y, float(st.net.mean()) / gross if gross else 1.0)
            s2 = solvency2(sy, st, res)
            harm = sum(p.rate * p.severity.mean() for p in sy.perils)
            row.update(expected_harm=harm, expected_claims=gross, share_paid=gross / harm if harm else 0.0,
                       premium=st.premium, premium_share=st.premium / sy.members / sy.revenue,
                       scr=s2["scr"], solvency_ratio=s2["solvency_ratio"], p_unpaid=float((st.unpaid > 0).mean()))
        else:
            row["stopped"] = True
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="central")
    ap.add_argument("--years", type=int, default=50_000)
    a = ap.parse_args()
    s, c = load(a.level), load_capability(a.level)
    for traj in TRAJECTORIES:
        print(f"\n{LABELS[traj]} (horizon now {horizon(c, traj, c.now):.0f}h)")
        print("  year  horizon    bio  cyber  agents    harm  claims  paid   premium/rev  SII ratio")
        for r in project(s, c, traj, a.years):
            h = "inf" if math.isinf(r["horizon"]) else f"{r['horizon']:.0f}h"
            if "premium" not in r:
                print(f"  {r['year']}  {h:>8}   past the stop ({c.stop_hours:g}h)")
                continue
            m = r["rates"]
            print(f"  {r['year']}  {h:>8} {m['bio_misuse']:6.2f} {m['cyber_misuse']:6.2f} {m['agent_runaway']:7.2f}"
                  f"  {r['expected_harm']:6.1f}  {r['expected_claims']:6.2f} {r['share_paid']:5.2%}  {r['premium_share']:10.2%}  {r['solvency_ratio']:8.0%}")


if __name__ == "__main__":
    main()
