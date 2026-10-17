"""Benchmark mode: one subject against frozen NPCs, scored against a reference bot in the same seat.

    python -m runner.benchmark_mode --subject random --seeds 20
"""
import argparse
import math

import numpy as np

import bots
from engine.market import Market

NPCS = ["actuary", "cycle", "reckless", "predator"]
SUBJECT = "subject"


def play(seed: int, subject_bot) -> dict:
    """Subject sits in seat 0; NPC line-up is fixed. Returns the subject's result dict."""
    lineup = {SUBJECT: subject_bot}
    lineup.update(bots.make(NPCS))
    res = Market(seed, lineup).run()
    return res["insurers"][SUBJECT]


def paired(seed: int, make_subject) -> dict:
    ref = play(seed, bots.REGISTRY["actuary"]())
    sub = play(seed, make_subject())
    return dict(seed=seed, subject=sub, reference=ref, delta=sub["score"] - ref["score"])


def summarise(rows) -> dict:
    d = np.array([r["delta"] for r in rows])
    raw = np.array([r["subject"]["score"] for r in rows])
    n = len(d)
    boots = np.random.default_rng(0).choice(d, size=(2000, n)).mean(axis=1)
    return dict(n=n, mean_delta=float(d.mean()), ci=(float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))),
                sd_raw=float(raw.std()), sd_delta=float(d.std()),
                survival=float(np.mean([not r["subject"]["insolvent"] for r in rows])),
                ref_survival=float(np.mean([not r["reference"]["insolvent"] for r in rows])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="random", choices=list(bots.REGISTRY))
    ap.add_argument("--seeds", type=int, default=20)
    a = ap.parse_args()
    rows = [paired(s, bots.REGISTRY[a.subject]) for s in range(a.seeds)]
    r = summarise(rows)
    print(f"subject={a.subject} seeds={r['n']}")
    print(f"  mean paired delta vs actuary-in-seat: {r['mean_delta']:+.2f}  95% CI [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]")
    print(f"  sd of raw score {r['sd_raw']:.2f} -> sd of paired delta {r['sd_delta']:.2f}")
    print(f"  survival: subject {100*r['survival']:.0f}%  reference {100*r['ref_survival']:.0f}%")


if __name__ == "__main__":
    main()
