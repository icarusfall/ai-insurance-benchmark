"""Bot-only market runner / calibration harness.

    python -m runner.simulate --seeds 10 --lineup actuary,reckless,cycle,predator,random
"""
import argparse
import json
import math
import os
import statistics as st

import bots
from engine.market import Market


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--lineup", default="actuary,reckless,cycle,predator,random")
    ap.add_argument("--save", default=None, help="directory to write per-seed JSON results")
    ap.add_argument("--regime", default="us", help="regulatory regime preset (us is the headline; uk is a variant)")
    args = ap.parse_args()
    from engine import params as _P
    _P.set_regime(args.regime)
    lineup = args.lineup.split(",")
    rows = {n: [] for n in lineup}
    cats = []
    for seed in range(args.start, args.start + args.seeds):
        m = Market(seed, bots.make(lineup))
        res = m.run()
        cats.append(sum(1 for e in res["events"] if e[1] == "cat"))
        for n in lineup:
            rows[n].append(res["insurers"][n])
        if args.save:
            os.makedirs(args.save, exist_ok=True)
            with open(os.path.join(args.save, f"seed{seed}.json"), "w") as f:
                json.dump(res, f)
    print(f"seeds={args.seeds} lineup={lineup} catastrophes/seed={st.mean(cats):.2f}")
    print(f"{'bot':10} {'score':>7} {'sd':>6} {'surv%':>6} {'value':>8} {'CR':>6} {'prem':>8} {'ruin_q':>7}")
    for n in lineup:
        r = rows[n]
        sc = [x["score"] for x in r]
        surv = 100 * sum(not x["insolvent"] for x in r) / len(r)
        crs = [x["combined_ratio"] for x in r if not math.isnan(x["combined_ratio"])]
        ruin = [x["insolvent_q"] for x in r if x["insolvent"]]
        print(f"{n:10} {st.mean(sc):7.2f} {st.pstdev(sc):6.2f} {surv:6.0f} {st.mean(x['value'] for x in r):8.1f} "
              f"{(st.mean(crs) if crs else float('nan')):6.2f} {st.mean(x['premium_written'] for x in r):8.1f} "
              f"{(st.mean(ruin) if ruin else float('nan')):7.1f}")


if __name__ == "__main__":
    main()
