"""Watch a batch while it runs (or after): cost, pace and signs of a model looping or burning tokens.

    python -m runner.watch runs/wave5
    python -m runner.watch runs/wave5 --flags-only

Per game: quarters played, spend so far, projected spend for 40 quarters, tool rounds per quarter, quarters
that hit the round limit or never ended, responses cut off at the output limit, and the longest run of
identical tool calls. Anything abnormal is flagged.
"""
import argparse
import glob
import json
import os
import time
from collections import Counter

from engine import params as P

MAX_ROUNDS = 25            # agents.llm_bot.MAX_ROUNDS


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass                      # a line being written right now
    return out


def longest_identical_run(tools: list) -> int:
    best = run = 0
    last = None
    for t in tools:
        key = (t["tool"], json.dumps(t.get("input"), sort_keys=True))
        run = run + 1 if key == last else 1
        last = key
        best = max(best, run)
    return best


def game_stats(gdir: str) -> dict:
    calls = read_jsonl(os.path.join(gdir, "calls.jsonl"))
    game = read_jsonl(os.path.join(gdir, "game.jsonl"))
    man = json.load(open(os.path.join(gdir, "manifest.json"))) if os.path.exists(os.path.join(gdir, "manifest.json")) else {}
    done = os.path.exists(os.path.join(gdir, "result.json"))
    usd = sum(c.get("usd") or 0.0 for c in calls)
    quarters = len(game)
    rounds = [len(g["tools"]) for g in game]
    per_q_calls = Counter(c["q"] for c in calls)
    loops = max((longest_identical_run(g["tools"]) for g in game), default=0)
    st = dict(model=man.get("model", os.path.basename(os.path.dirname(gdir))), seed=man.get("seed"), done=done,
              quarters=quarters, usd=usd, calls=len(calls),
              usd_per_q=usd / quarters if quarters else 0.0,
              projected=usd / quarters * P.Q if quarters else 0.0,
              unended=sum(1 for g in game if not g["ended"]),
              at_cap=sum(1 for g in game if len(g["tools"]) >= MAX_ROUNDS),
              loop_breaks=sum(1 for g in game if any(t["tool"] == "_loop_break" for t in g["tools"])),
              max_tokens=sum(1 for c in calls if c.get("stop_reason") == "max_tokens"),
              max_calls_q=max(per_q_calls.values(), default=0),
              mean_rounds=sum(rounds) / len(rounds) if rounds else 0.0,
              longest_repeat=loops,
              idle_min=(time.time() - calls[-1]["ts"]) / 60 if calls and calls[-1].get("ts") else None)
    if done:
        r = json.load(open(os.path.join(gdir, "result.json")))
        st.update(R=r.get("R"), insolvent=r.get("insolvent"), complete=r.get("complete"))
    flags = []
    if st["unended"] >= 3:
        flags.append(f"{st['unended']} unended quarters")
    if st["loop_breaks"]:
        flags.append(f"{st['loop_breaks']} loop breaks")
    if st["longest_repeat"] >= 4:
        flags.append(f"same call repeated {st['longest_repeat']}x")
    if st["max_tokens"] >= 3:
        flags.append(f"{st['max_tokens']} responses cut off at the output limit")
    if st["max_calls_q"] >= 20:
        flags.append(f"{st['max_calls_q']} calls in one quarter")
    if not done and st["idle_min"] is not None and st["idle_min"] > 15:
        flags.append(f"no call for {st['idle_min']:.0f} min")
    st["flags"] = flags
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--flags-only", action="store_true")
    a = ap.parse_args()
    games = sorted(d for d in glob.glob(os.path.join(a.batch, "*", "s*")) if os.path.isdir(d) and "_" not in os.path.basename(d))
    rows = [game_stats(d) for d in games]
    print(f"{'model':28} {'seed':>4} {'q':>3} {'$ so far':>8} {'$/40q proj':>10} {'calls':>5} {'rounds/q':>8} "
          f"{'unend':>5} {'maxtok':>6} {'repeat':>6} {'R':>5}  flags")
    total = 0.0
    for s in rows:
        total += s["usd"]
        if a.flags_only and not s["flags"]:
            continue
        R = f"{s['R']:.2f}" if s.get("R") is not None else ("run" if not s["done"] else "-")
        print(f"{s['model'][:28]:28} {str(s['seed']):>4} {s['quarters']:>3} {s['usd']:8.2f} {s['projected']:10.2f} "
              f"{s['calls']:>5} {s['mean_rounds']:8.1f} {s['unended']:>5} {s['max_tokens']:>6} {s['longest_repeat']:>6} "
              f"{R:>5}  {'; '.join(s['flags'])}")
    by = Counter()
    for s in rows:
        by[s["model"]] += s["usd"]
    print(f"\nbatch spend ${total:.2f}: " + ", ".join(f"{m} ${v:.2f}" for m, v in by.most_common()))


if __name__ == "__main__":
    main()
