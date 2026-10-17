"""Calibration probes: every probe bot (bots/probes.py) as a benchmark-mode subject, paired against actuary-in-seat.

    python -m runner.probe --seeds 20
    python -m runner.probe --seeds 10 --probes null,deny_all

Run after every recalibration. The reference runs once per seed and is shared by all probes.
"""
import argparse
import time

import numpy as np

import bots
from runner.benchmark_mode import play, summarise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--probes", default=",".join(bots.PROBE_NAMES))
    a = ap.parse_args()
    seeds = range(a.start, a.start + a.seeds)
    refs = {s: play(s, bots.REGISTRY["actuary"]()) for s in seeds}
    ref_v = [refs[s]["value"] for s in seeds]
    print(f"seeds={a.seeds}  reference actuary: mean V {np.mean(ref_v):.1f}, median V {np.median(ref_v):.1f}, "
          f"survival {np.mean([not refs[s]['insolvent'] for s in seeds]):.0%}")
    print(f"{'probe':12} {'delta':>7} {'95% CI':>17} {'surv':>5} {'mean V':>7} {'med V':>7} {'P(beat ref)':>11}")
    for name in a.probes.split(","):
        t = time.time()
        rows = []
        for s in seeds:
            sub = play(s, bots.REGISTRY[name]())
            rows.append(dict(seed=s, subject=sub, reference=refs[s], delta=sub["score"] - refs[s]["score"]))
        r = summarise(rows)
        v = [x["subject"]["value"] for x in rows]
        beat = np.mean([x["subject"]["value"] > x["reference"]["value"] for x in rows])
        print(f"{name:12} {r['mean_delta']:+7.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}] {r['survival']:5.0%} "
              f"{np.mean(v):7.1f} {np.median(v):7.1f} {beat:11.0%}   ({time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
