"""Export the data the public site draws from, by running the real engine.

    python -m website.build            # about 3 minutes; writes website/public/data.js

Everything on the site that looks like a number comes from here: parameters, a sample world, bot-only
games for the failure gallery, and (when local run logs exist) excerpts from LLM games. The output is
committed, so the site deploys without the engine or the git-ignored runs/ folder.
"""
import glob
import json
import math
import os
from collections import Counter

import numpy as np

import bots
from bots import priors
from engine import params as P
from engine.market import Market
from engine.world import World
from runner.benchmark_mode import NPCS, SUBJECT

OUT = os.path.join(os.path.dirname(__file__), "public", "data.js")
SEEDS = range(10)
SAMPLE_SEED = 7
GALLERY = ["actuary", "null", "reckless", "cycle", "random", "deny_all", "no_reins", "timid"]


def params() -> dict:
    keys = ["ENV_VERSION", "Q", "START_EQUITY", "EXPENSE", "INVEST_RATE", "K_REG", "AUDIT_FLOOR", "POLICY_TERM",
            "IDEAL_LIMIT_PER_SIZE", "NET_LINE_MAX", "HURDLE", "CLAWBACK_Q", "DILUTION", "CAPITAL_RAISE_MAX",
            "SUE_PROB_AFTER_DENIAL", "BAD_FAITH_LOADING", "INTEREST_LOADING", "CONTEST_FEE", "REJECTED_SETTLE_FEE",
            "SETTLE_ACCEPT", "CAT_RATE", "RULING_RATE", "FALSE_ALARM_RATE", "LEVY_CAP", "REINS_BASE_LOAD",
            "COURT_DELAY", "SIZE_MULT", "SIZE_WORDS", "PROVIDER_NAMES"]
    out = {k: getattr(P, k) for k in keys}
    out["SECTORS"] = P.SECTORS
    out["ACTUARY_MARGIN"] = bots.actuary.MARGIN
    return out


def app_view(world: World, c) -> dict:
    return dict(sector=c.sector, size_band=c.size, autonomy_signal=round(c.autonomy_obs, 2),
                safety_signal=round(c.safety_obs, 2), red_flags=list(c.red_flags))


def sample_dossiers() -> list:
    """A handful of real clients: what the dossier says, what the scripted actuary estimates, and the truth."""
    w = World(SAMPLE_SEED)
    rows = []
    for c in w.clients:
        true_el = 4 * w.expected_quarter_loss(c, 0, c.ideal_limit, c.default_retention)
        est = priors.el_annual(app_view(w, c), c.ideal_limit, c.default_retention)
        rows.append((c, true_el, est))
    picks, used = [], set()

    def take(label, key):
        for c, t, e in sorted(rows, key=key):
            if c.id not in used and c.sector not in {p["sector"] for p in picks}:
                used.add(c.id)
                picks.append(dict(label=label, id=c.id, sector=c.sector, size=P.SIZE_WORDS[c.size], text=c.text,
                                  red_flags=c.red_flags, autonomy_signal=round(c.autonomy_obs, 2),
                                  safety_signal=round(c.safety_obs, 2), autonomy_true=round(c.autonomy, 2),
                                  safety_true=round(c.safety, 2), corner_cutting=c.corner, hidden_mult=round(c.unk, 2),
                                  vendor=w.providers[c.provider].name, vendor_stated=c.provider_stated,
                                  vendor_quality=round(w.providers[c.provider].quality, 2),
                                  ideal_limit=c.ideal_limit, true_el=round(t, 4), actuary_el=round(e, 4)))
                return

    take("Looks fine, is fine", lambda r: abs(math.log(r[1] / r[2])) + (0 if not r[0].red_flags else 9))
    take("Looks fine, is not", lambda r: -(r[1] / r[2]) + (9 if r[0].red_flags else 0))
    take("Looks alarming, is fine", lambda r: (r[1] / r[2]) + (0 if r[0].red_flags else 9))
    take("Hidden in plain sight", lambda r: -r[1] if r[0].corner else 99)
    return picks


def world_summary() -> dict:
    w = World(SAMPLE_SEED)
    sec = Counter(c.sector for c in w.clients)
    return dict(seed=SAMPLE_SEED, n_clients=len(w.clients),
                vendors=[dict(name=p.name, flaw_rate=round(p.flaw_rate, 3), quality=round(p.quality, 2),
                              share=P.PROVIDER_SHARES[i]) for i, p in enumerate(w.providers)],
                sectors={s: dict(count=sec[s], **P.SECTORS[s]) for s in P.SECTOR_NAMES},
                events=[dict(q=e.q, kind=e.kind, headline=e.headline) for e in w.events])


def lag_histogram() -> dict:
    """Reporting delay of every claim in a bot-only game: why premiums look like profit for two years."""
    m = Market(SAMPLE_SEED, bots.make(["actuary"] + NPCS))
    m.run()
    lag = Counter(cl.rep_q - cl.occ_q for cl in m.claims.values())
    amt = Counter()
    for cl in m.claims.values():
        amt[cl.rep_q - cl.occ_q] += cl.covered
    return dict(counts={k: lag[k] for k in sorted(lag)}, amounts={k: round(amt[k], 2) for k in sorted(amt)},
                market=[dict(q=h["q"], adequacy=h["adequacy"], rol=h["rol"], fund=h["fund_outlay"])
                        for h in m.result()["market"]])


def trim(h: dict) -> dict:
    return {k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v)
            for k, v in h.items() if k in ("q", "cash", "reported_eq", "audited_eq", "true_eq", "npw", "paid",
                                            "rating", "rep", "insolvent", "ibnr", "in_force")}


def gallery() -> dict:
    """Each probe/NPC as a benchmark-mode subject on SEEDS, paired with the actuary in the same seat."""
    out = {}
    for name in GALLERY:
        games = []
        for s in SEEDS:
            lineup = {SUBJECT: bots.REGISTRY[name]()}
            lineup.update(bots.make(NPCS))
            m = Market(s, lineup)
            res = m.run()
            r = res["insurers"][SUBJECT]
            ins = m.ins[SUBJECT]
            claims = Counter()
            for cl in m.claims.values():
                if cl.insurer == SUBJECT:
                    claims["bad_faith" if cl.bad_faith else cl.status] += 1
            games.append(dict(seed=s, R=round(r["R"], 3), value=round(r["value"], 2), insolvent=r["insolvent"],
                              insolvent_q=r["insolvent_q"], dividends=round(r["dividends"], 2),
                              injected=round(r["injected"], 2), premium=round(r["premium_written"], 1),
                              combined_ratio=(round(r["combined_ratio"], 3)
                                              if not math.isnan(r["combined_ratio"]) else None),
                              reins_cost=round(r["reins_cost"], 2), rep_end=round(ins.rep, 3),
                              div_q=[round(x, 3) for x in ins.div_q], inj_q=[round(x, 3) for x in ins.inj_q],
                              history=[trim(h) for h in r["history"]]))
        out[name] = games
        print(f"  gallery {name}: survival {np.mean([not g['insolvent'] for g in games]):.0%}, "
              f"median R {np.median([g['R'] for g in games]):.2f}", flush=True)
    return out


def llm_excerpts() -> list:
    """Wave-1 LLM games (environment v0.1) from local logs, if present: equity path, memos at the turning points."""
    picks = [("claude-haiku-5-5", 1, "One claim, one policy, one quarter"),
             ("claude-haiku-5-5", 2, "Pay out, then find out"),
             ("gpt-5.4-nano", 0, "The slow bleed"),
             ("gemini-3.1-flash-lite", 0, "Price your way out of the bad sectors")]
    out = []
    for model, seed, title in picks:
        p = os.path.join("runs", "wave1", model.replace("/", "_"), f"s{seed}", "game.jsonl")
        if not os.path.exists(p):
            continue
        rows = [json.loads(l) for l in open(p, encoding="utf-8")]
        out.append(dict(model=model, seed=seed, title=title, env_version="0.1.0-dev",
                        quarters=[dict(q=r["q"], reported_eq=r["own"]["reported_equity"], cash=r["own"]["cash"],
                                       rating=r["own"]["rating"], dividend=r["dividend"], memo=r["memo"],
                                       policies=r["own"]["policies_in_force"]) for r in rows]))
    return out


def briefing() -> dict:
    """The exact text a model receives at the start of a quarter (actuary playing the seat up to then), plus the tools."""
    from agents.prompt import SYSTEM, build_briefing
    from agents.tools import TOOLS
    lineup = {SUBJECT: bots.REGISTRY["actuary"]()}
    lineup.update(bots.make(NPCS))
    m = Market(SAMPLE_SEED, lineup)
    m.run(max_quarters=8)
    view = m.begin_quarter()[SUBJECT]
    text = build_briefing(view, {"notes": "(the model's own notes would appear here)", "manual": None})
    app = view["applicants"][0]
    return dict(system=SYSTEM, briefing=text, quarter=view["q"] + 1,
                applicant={k: app[k] for k in ("id", "text", "sector", "size_word", "provider", "autonomy_signal",
                                               "safety_signal", "red_flags", "ideal_limit", "default_retention")},
                tools=[dict(name=t["name"], description=t["description"]) for t in TOOLS])


def _trim(v, n=4):
    """Keep transcripts readable: long lists keep their first few items, long strings are cut."""
    if isinstance(v, list):
        out = [_trim(x, n) for x in v[:n]]
        return out + ([f"... {len(v) - n} more"] if len(v) > n else [])
    if isinstance(v, dict):
        return {k: _trim(x, n) for k, x in v.items()}
    if isinstance(v, str) and len(v) > 700:
        return v[:700] + " ..."
    return v


def _tool_output(name: str, raw: str):
    try:
        out = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw[:400] + (" ..." if len(raw) > 400 else "")    # logged outputs over 600 characters were cut
    if name == "get_applicants" and isinstance(out, dict):
        out["applicants"] = out.get("applicants", [])[:2]
        out["note"] = "applicants after the first two omitted here"
    return _trim(out, 3)


def llm_turns() -> list:
    """One real quarter per model from the current wave: every tool call, its input and the game's reply."""
    out = []
    best = {}
    for p in glob.glob(os.path.join("runs", "wave2", "*", "s*", "game.jsonl")):
        with open(os.path.join(os.path.dirname(p), "manifest.json"), encoding="utf-8") as f:
            man = json.load(f)
        model, seed = man["model"], man["seed"]
        for r in (json.loads(l) for l in open(p, encoding="utf-8")):
            names = [t["tool"] for t in r["tools"]]
            if r["q"] < 6 or "end_turn" not in names or not r.get("memo"):
                continue
            score = (len(set(names)) + 3 * ("submit_quotes" in names) + 3 * ("decide_claims" in names)
                     + 2 * ("set_reinsurance" in names) + ("set_rate_manual" in names) - 0.1 * max(0, len(names) - 14))
            if score > best.get(model, (-1,))[0]:
                best[model] = (score, seed, r)
    for model, (_, seed, r) in sorted(best.items()):
        own = r["own"]
        out.append(dict(model=model, seed=seed, quarter=r["q"] + 1, env_version=P.ENV_VERSION,
                        position=dict(cash=own["cash"], reported_equity=own["reported_equity"],
                                      audited_equity=own.get("audited_equity"), solvency_ratio=own.get("solvency_ratio"),
                                      policies_in_force=own["policies_in_force"]),
                        calls=[dict(tool=t["tool"], input=_trim(t["input"]), output=_tool_output(t["tool"], t["output"]))
                               for t in r["tools"]],
                        notes=r.get("notes"), memo=r.get("memo")))
    return out


def wealth_path(true_eq: list, div_q: list, inj_q: list, insolvent_q: int) -> list:
    """Shareholder wealth after each quarter relative to the hurdle path: (true equity + dividends - cost of
    injections, all compounded at the hurdle) / (START_EQUITY x (1 + h)^(t+1)). At quarter 40 this is R.
    After insolvency equity is zero and dividends inside the clawback window no longer count."""
    h, out = P.HURDLE, []
    for t in range(P.Q):
        dead = 0 <= insolvent_q <= t
        keep_before = insolvent_q - P.CLAWBACK_Q if dead else t + 1
        flows = sum(div_q[s] * (1 + h) ** (t - s) for s in range(min(t + 1, max(keep_before, 0))))
        flows -= sum((1 + P.DILUTION) * inj_q[s] * (1 + h) ** (t - s) for s in range(t + 1))
        eq = 0.0 if dead else max(true_eq[t], 0.0)
        out.append(round(max(eq + flows, 0.0) / (P.START_EQUITY * (1 + h) ** (t + 1)), 4))
    return out


def _per_quarter(cum_at_start: dict, total: float) -> list:
    """Per-quarter amounts from cumulative figures seen at the start of each quarter, plus the final total."""
    cum = [cum_at_start.get(t + 1, total) for t in range(P.Q)]
    cum = [min(c, total) for c in cum]
    return [round(cum[t] - (cum[t - 1] if t else 0.0), 6) for t in range(P.Q)]


def results(batch: str = "wave2") -> dict:
    """Every complete LLM game in a batch, as wealth paths, plus the reference actuary on the same seeds."""
    models = {}
    for p in sorted(glob.glob(os.path.join("runs", batch, "*", "s*", "result.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        if not r.get("complete") or r.get("env_version") != P.ENV_VERSION:
            continue
        rows = [json.loads(l) for l in open(os.path.join(os.path.dirname(p), "game.jsonl"), encoding="utf-8")]
        divs = _per_quarter({x["q"]: x["own"]["dividends_paid"] for x in rows}, r["dividends"])
        injs = _per_quarter({x["q"]: P.CAPITAL_RAISE_MAX * P.START_EQUITY - x["own"]["capital_raise_remaining"] for x in rows},
                            r["injected"])
        path = wealth_path([h["true_eq"] for h in r["history"]], divs, injs, r["insolvent_q"])
        models.setdefault(r["model"], []).append(dict(
            seed=r["seed"], R=round(r["R"], 4), insolvent=r["insolvent"], insolvent_q=r["insolvent_q"],
            usd=round(r["tokens"]["usd"], 4), minutes=round(r["wall_seconds"] / 60, 1),
            premium=round(r["premium_written"], 1), dividends=round(r["dividends"], 2), injected=round(r["injected"], 2),
            path=path))
    seeds = sorted({g["seed"] for gs in models.values() for g in gs})
    ref = []
    for s in seeds:
        lineup = {SUBJECT: bots.REGISTRY["actuary"]()}
        lineup.update(bots.make(NPCS))
        m = Market(s, lineup)
        res = m.run()["insurers"][SUBJECT]
        ins = m.ins[SUBJECT]
        ref.append(dict(seed=s, R=round(res["R"], 4), insolvent=res["insolvent"], insolvent_q=res["insolvent_q"],
                        path=wealth_path([h["true_eq"] for h in res["history"]], ins.div_q, ins.inj_q, res["insolvent_q"])))
    return dict(batch=batch, env_version=P.ENV_VERSION, models=models, reference=ref)


def main():
    import sys
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    if only:                                   # refresh some parts, keep the rest of the existing export
        txt = open(OUT, encoding="utf-8").read()
        data = json.loads(txt[txt.index("=") + 1:].rstrip().rstrip(";"))
        parts = dict(results=results, turns=llm_turns, llm=llm_excerpts, briefing=briefing, gallery=gallery, dossiers=sample_dossiers,
                     world=world_summary, lags=lag_histogram, params=params)
        for k in only:
            data[k] = parts[k]()
        _write(data)
        return
    data = dict(params=params(), world=world_summary(), dossiers=sample_dossiers(), lags=lag_histogram(),
                briefing=briefing())
    data["gallery"] = gallery()
    data["llm"] = llm_excerpts() or _existing_llm()
    data["turns"] = llm_turns() or _existing_part("turns")
    data["results"] = results() if os.path.isdir(os.path.join("runs", "wave2")) else _existing_part("results")
    _write(data)


def _existing_part(key: str) -> list:
    if not os.path.exists(OUT):
        return []
    txt = open(OUT, encoding="utf-8").read()
    try:
        return json.loads(txt[txt.index("=") + 1:].rstrip().rstrip(";")).get(key, [])
    except (ValueError, json.JSONDecodeError):
        return []


def _write(data):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Generated by python -m website.build. Do not edit by hand.\nwindow.SITE = ")
        json.dump(data, f, separators=(",", ":"), default=float)
        f.write(";\n")
    print(f"wrote {OUT} ({os.path.getsize(OUT) / 1024:.0f} KB)")


def _existing_llm() -> list:
    """Keep previously exported LLM excerpts when the local run logs are not available (e.g. on a clean clone)."""
    return _existing_part("llm")


if __name__ == "__main__":
    main()
