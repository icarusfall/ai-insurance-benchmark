"""Calibration diagnostics: does an underwriting cycle emerge? How much does the seed matter?"""
import argparse
import statistics as st

import numpy as np

import bots
from engine import params as P
from engine.market import Market


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--lineup", default="actuary,reckless,cycle,predator,random")
    a = ap.parse_args()
    lineup = a.lineup.split(",")
    adq = np.full((a.seeds, P.Q), np.nan)
    live = np.zeros((a.seeds, P.Q))
    cat_q = []
    scores = {n: [] for n in lineup}
    for s in range(a.seeds):
        res = Market(s, bots.make(lineup)).run()
        for q, m in enumerate(res["market"]):
            if m["adequacy"] is not None:
                adq[s, q] = m["adequacy"]
            live[s, q] = sum(1 for n in lineup if not res["insurers"][n]["history"][q]["insolvent"])
        cat_q += [(s, e[0]) for e in res["events"] if e[1] == "cat"]
        for n in lineup:
            scores[n].append(res["insurers"][n]["score"])
    print("rate adequacy (premium / oracle expected loss; break-even ~1.25), mean by year:")
    for y in range(10):
        print(f"  year {y+1}: {np.nanmean(adq[:, 4*y:4*y+4]):.2f}   live insurers: {live[:, 4*y:4*y+4].mean():.2f}")
    pre, post = [], []
    for s, q in cat_q:
        if q >= 4 and q + 6 < P.Q:
            pre.append(np.nanmean(adq[s, q-4:q]))
            post.append(np.nanmean(adq[s, q+1:q+5]))
    if pre:
        print(f"around catastrophes (n={len(pre)}): adequacy before {np.mean(pre):.2f} -> after {np.mean(post):.2f}")
    # between-seed vs within-seed variance of each bot's score
    mat = np.array([scores[n] for n in lineup])            # bots x seeds
    seed_effect = mat.mean(axis=0)
    print(f"score variance: total {mat.var():.2f}; explained by seed {np.var(seed_effect):.2f} "
          f"({100*np.var(seed_effect)/mat.var():.0f}%)")
    ref = mat[lineup.index("actuary")]
    for n in lineup:
        d = mat[lineup.index(n)] - ref
        print(f"  {n:9} raw sd {mat[lineup.index(n)].std():.2f}  paired-vs-actuary sd {d.std():.2f}")

if __name__ == "__main__":
    main()
