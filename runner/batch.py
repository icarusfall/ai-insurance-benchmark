"""Run many (model, seed) games in parallel with resume. Benchmark mode: subject vs frozen NPCs.

    python -m runner.batch --models claude-haiku-5-5,gpt-5.6-luna --seeds 5 --workers 6 --out runs/wave1
"""
import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import bots
from agents.env import load_env
from agents.factory import make_adapter
from agents.llm_bot import LLMBot
from agents.pricing import Budget, BudgetExceeded, load_models
from agents.runlog import RunLog
from engine import params as P
from engine.market import Market
from runner.benchmark_mode import NPCS, SUBJECT, play


def safe(model: str) -> str:
    return model.replace("/", "_")


def reference(out: str, seed: int) -> dict:
    """Actuary-bot in the subject's seat on this seed (cached)."""
    path = os.path.join(out, "_reference", f"s{seed}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    r = play(seed, bots.REGISTRY["actuary"]())
    r = {k: r[k] for k in ("score", "value", "insolvent", "insolvent_q", "combined_ratio")}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(r, f)
    return r


def run_job(model: str, seed: int, out: str, models: dict, per_game_cap: float, total: Budget) -> dict:
    root = os.path.join(out, safe(model))
    path = os.path.join(root, f"s{seed}", "result.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    log = RunLog(root, f"s{seed}", dict(model=model, seed=seed, mode="benchmark", env_version=P.ENV_VERSION,
                                        npcs=NPCS, prices=models[model]))
    budget = Budget(per_game_cap, parent=total)
    bot = LLMBot(SUBJECT, make_adapter(model, models[model]), model, models, budget, log)
    lineup = {SUBJECT: bot}
    lineup.update(bots.make(NPCS))
    m = Market(seed, lineup)
    err, t0 = None, time.time()
    try:
        m.run()
    except BudgetExceeded as e:
        err = f"budget: {e}"
    except Exception as e:                       # keep the batch alive; record the failure
        err = f"{type(e).__name__}: {str(e)[:300]}"
    r = m.result()["insurers"][SUBJECT]
    res = dict(model=model, seed=seed, complete=err is None and len(r["history"]) == P.Q and bot.errors <= 4 and bot.unended <= 4, error=err,
               quarters=len(r["history"]), score=r["score"], value=r["value"], insolvent=r["insolvent"],
               insolvent_q=r["insolvent_q"], combined_ratio=r["combined_ratio"], premium_written=r["premium_written"],
               injected=r["injected"], dividends=r["dividends"], tokens=bot.totals, adapter_errors=bot.errors,
               refusals=bot.refusals, unended_quarters=bot.unended, wall_seconds=time.time() - t0,
               history=r["history"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(res, f, default=float)
    return res


def preflight(names: list, models: dict) -> bool:
    """One quarter per model, in parallel. Catches bad model ids / unsupported parameters before real spend."""
    def one(n):
        try:
            bot = LLMBot(SUBJECT, make_adapter(n, models[n]), n, models, Budget(0.25), None)
            lineup = {SUBJECT: bot}
            lineup.update(bots.make(NPCS))
            Market(0, lineup).run(1)
            ok = bot.errors == 0 and bot.unended == 0 and bot.totals["calls"] >= 2
            return n, ok, "" if ok else f"errors={bot.errors} unended={bot.unended} calls={bot.totals['calls']}", bot.totals["usd"]
        except Exception as e:
            return n, False, f"{type(e).__name__}: {str(e)[:220]}", 0.0
    with ThreadPoolExecutor(len(names)) as ex:
        res = list(ex.map(one, names))
    good = True
    for n, ok, why, usd in res:
        print(f"  preflight {n:32} {'ok' if ok else 'FAIL ' + why}  (${usd:.4f})", flush=True)
        good &= ok
    return good


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--per-game-cap", type=float, default=1.5)
    ap.add_argument("--total-cap", type=float, default=15.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-preflight", action="store_true")
    a = ap.parse_args()
    models = load_models()
    names = a.models.split(",")
    for n in names:
        if n not in models:
            raise SystemExit(f"{n} not in models.yaml")
    if not a.skip_preflight and not preflight(names, models):
        raise SystemExit("preflight failed; fix the models above (or pass --skip-preflight)")
    seeds = list(range(a.start, a.start + a.seeds))
    for s in seeds:
        reference(a.out, s)
    total = Budget(a.total_cap)
    jobs = [(n, s) for s in seeds for n in names]
    print(f"{len(jobs)} games, {a.workers} workers, per-game cap ${a.per_game_cap}, total cap ${a.total_cap}", flush=True)
    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_job, n, s, a.out, models, a.per_game_cap, total): (n, s) for n, s in jobs}
        for f in as_completed(futs):
            n, s = futs[f]
            try:
                r = f.result()
                msg = (f"score {r['score']:+.2f} value {r['value']:.1f} {'RUIN ' if r['insolvent'] else ''}"
                       f"cost ${r['tokens']['usd']:.3f} {r['wall_seconds'] / 60:.1f}min "
                       f"{'' if r['complete'] else 'INCOMPLETE ' + str(r['error'])}")
            except Exception as e:
                msg = f"FAILED {type(e).__name__}: {str(e)[:200]}"
            with lock:
                done += 1
                print(f"[{done}/{len(jobs)}] {n} seed {s}: {msg} | total ${total.spent:.2f}", flush=True)


if __name__ == "__main__":
    main()
