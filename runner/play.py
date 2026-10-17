"""Play one LLM subject in benchmark mode (frozen NPC rivals).

    python -m runner.play --model claude-sonnet-5-5 --seed 0 --quarters 8 --max-cost 2
"""
import argparse
import json
import time

import bots
from agents.adapters import AnthropicAdapter
from agents.llm_bot import LLMBot
from agents.pricing import Budget, BudgetExceeded, load_models
from agents.runlog import RunLog
from engine import params as P
from engine.market import Market
from runner.benchmark_mode import NPCS, SUBJECT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quarters", type=int, default=P.Q)
    ap.add_argument("--max-cost", type=float, default=5.0, help="hard USD cap for this run")
    ap.add_argument("--runs-dir", default="runs")
    a = ap.parse_args()
    import os
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise SystemExit("No Anthropic credentials found. Set ANTHROPIC_API_KEY in the environment "
                         "(never in the repo) and run again.")
    models = load_models()
    if a.model not in models:
        raise SystemExit(f"{a.model} not in models.yaml")
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{a.model}-s{a.seed}"
    log = RunLog(a.runs_dir, run_id, dict(model=a.model, seed=a.seed, quarters=a.quarters, mode="benchmark",
                                          env_version=P.ENV_VERSION, npcs=NPCS, prices=models[a.model]))
    budget = Budget(a.max_cost)
    bot = LLMBot(SUBJECT, AnthropicAdapter(a.model, models[a.model]), a.model, models, budget, log)
    lineup = {SUBJECT: bot}
    lineup.update(bots.make(NPCS))
    m = Market(a.seed, lineup)
    try:
        res = m.run(a.quarters)
    except BudgetExceeded as e:
        print("STOPPED:", e)
        res = m.result()
    r = res["insurers"][SUBJECT]
    summary = dict(run_id=run_id, quarters_played=len(r["history"]), score=r["score"], value=r["value"],
                   insolvent=r["insolvent"], tokens=bot.totals)
    log.game(summary=summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
