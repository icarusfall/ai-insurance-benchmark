"""Summarise a batch directory: paired score vs the actuary-in-seat reference, survival, cost, reliability.

    python -m runner.report runs/wave1
"""
import glob
import json
import os
import sys

import numpy as np


def load(out):
    ref = {}
    for p in glob.glob(os.path.join(out, "_reference", "s*.json")):
        with open(p) as f:
            ref[int(os.path.basename(p)[1:-5])] = json.load(f)
    rows = {}
    for p in glob.glob(os.path.join(out, "*", "s*", "result.json")):
        with open(p) as f:
            r = json.load(f)
        rows.setdefault(r["model"], []).append(r)
    return ref, rows


def main(out):
    ref, rows = load(out)
    print(f"{'model':30} {'n':>3} {'dScore':>7} {'95% CI':>14} {'surv':>5} {'ref':>5} {'medR':>5} {'refR':>5} "
          f"{'beat':>5} {'$/game':>7} "
          f"{'tok in/out k':>13} {'min/game':>8} {'err/refus/unend':>15}")
    for model, rs in sorted(rows.items()):
        ok = [r for r in rs if r["complete"]]
        if not ok:
            print(f"{model:30} no complete games ({len(rs)} attempted; first error: {rs[0].get('error')})")
            continue
        d = np.array([r["score"] - ref[r["seed"]]["score"] for r in ok])
        b = np.random.default_rng(0).choice(d, size=(2000, len(d))).mean(axis=1) if len(d) > 1 else d
        t = {k: np.mean([r["tokens"][k] for r in ok]) for k in ("input", "output", "cache_read", "usd")}
        extra = f"  (+{len(rs) - len(ok)} incomplete)" if len(rs) > len(ok) else ""
        print(f"{model:30} {len(ok):3d} {d.mean():+7.2f} [{np.percentile(b, 2.5):+5.2f},{np.percentile(b, 97.5):+5.2f}] "
              f"{100 * np.mean([not r['insolvent'] for r in ok]):4.0f}% "
              f"{100 * np.mean([not ref[r['seed']]['insolvent'] for r in ok]):4.0f}% "
              f"{np.median([r['R'] for r in ok]):5.2f} {np.median([ref[r['seed']]['R'] for r in ok]):5.2f} "
              f"{100 * np.mean([r['value'] > ref[r['seed']]['value'] for r in ok]):4.0f}% "
              f"{t['usd']:7.3f} {(t['input'] + t['cache_read']) / 1000:6.0f}/{t['output'] / 1000:<6.0f} "
              f"{np.mean([r['wall_seconds'] for r in ok]) / 60:8.1f} "
              f"{sum(r['adapter_errors'] for r in ok)}/{sum(r['refusals'] for r in ok)}/{sum(r['unended_quarters'] for r in ok)}{extra}")


if __name__ == "__main__":
    main(sys.argv[1])
