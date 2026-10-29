"""Re-fit Lane's (2000) pricing equation and the Wang transform to recent catastrophe bonds.

    python -m catmodel.catbond_fit

Data: catmodel/sources/catbond_prices.csv (Artemis deal pages). Lane is fitted the way he fitted it, by least squares on
ln EER = ln γ + a ln PFL + b ln CEL, everything in decimals of par, here with one extra term: a cyber dummy, so cyber
bonds share the natural catastrophe slopes but carry their own multiplicative loading.

Wang: the deal pages give only the attachment probability and expected loss of each tranche, not its loss curve. Inside the
layer we assume the exceedance probability falls log-linearly from PFL at attachment to PFE at exhaustion, with PFE set
so the layer's expected loss matches (then CEL = (r - 1) / ln r, r = PFE / PFL). λ is the shift that makes the
Wang-distorted expected loss equal the spread. The assumption only shapes the curve between two points that are known.
"""
import csv
import math
import os
from statistics import NormalDist, median

import numpy as np

DATA = os.path.join(os.path.dirname(__file__), "sources", "catbond_prices.csv")
_N = NormalDist()


def load(path: str = DATA) -> list:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    for r in rows:
        r["pfl"], r["el"], r["spread"] = (float(r[k]) / 100 for k in ("pfl_pct", "el_pct", "spread_pct"))
        r["cel"] = r["el"] / r["pfl"]
    return rows


def fit_lane(rows: list) -> dict:
    """Least squares on logs. Returns γ, a, b, the cyber loading exp(c), standard errors and R²."""
    y = np.log([r["spread"] for r in rows])
    cyber = np.array([r["peril"] == "cyber" for r in rows], dtype=float)
    cols = [np.ones(len(rows)), np.log([r["pfl"] for r in rows]), np.log([r["cel"] for r in rows])]
    if cyber.any() and not cyber.all():
        cols.append(cyber)
    X = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    s2 = float(resid @ resid) / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    r2 = 1 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    out = dict(n=n, gamma=math.exp(beta[0]), a=float(beta[1]), b=float(beta[2]), se_ln_gamma=float(se[0]),
               se_a=float(se[1]), se_b=float(se[2]), r2=r2, adj_r2=1 - (1 - r2) * (n - 1) / (n - k),
               cyber_loading=1.0, se_cyber=0.0)
    if k == 4:
        out.update(cyber_loading=math.exp(beta[3]), se_cyber=float(se[3]))
    return out


def layer_ratio(cel: float) -> float:
    """r = PFE / PFL such that a log-linear exceedance curve across the layer has the given CEL."""
    if cel >= 1 - 1e-9:
        return 1.0
    lo, hi = 1e-12, 1 - 1e-12                     # (r - 1) / ln r rises from 0 to 1 as r goes from 0 to 1
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if (mid - 1) / math.log(mid) < cel:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def wang_price(pfl: float, cel: float, lam: float, steps: int = 200) -> float:
    """Wang-distorted expected loss of the layer, as a fraction of its limit."""
    r = layer_ratio(cel)
    xs = (np.arange(steps) + 0.5) / steps
    return float(np.mean([_N.cdf(_N.inv_cdf(pfl * r ** x) + lam) for x in xs]))


def fit_wang(pfl: float, cel: float, spread: float) -> float:
    lo, hi = 0.0, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if wang_price(pfl, cel, mid) < spread:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def summary(rows: list | None = None) -> dict:
    rows = rows if rows is not None else load()
    for r in rows:
        r["wang_lambda"] = fit_wang(r["pfl"], r["cel"], r["spread"])
    by = {p: [r for r in rows if r["peril"] == p] for p in ("natcat", "cyber")}
    lam = {p: dict(median=median(r["wang_lambda"] for r in rs), low=min(r["wang_lambda"] for r in rs),
                   high=max(r["wang_lambda"] for r in rs), n=len(rs)) for p, rs in by.items()}
    mult = {p: median(r["spread"] / r["el"] for r in rs) for p, rs in by.items()}
    return dict(lane_pooled=fit_lane(rows), lane_natcat=fit_lane(by["natcat"]), wang=lam, median_multiple=mult, rows=rows)


def main():
    s = summary()
    for k in ("lane_natcat", "lane_pooled"):
        f = s[k]
        print(f"{k}: n={f['n']}  EER = {f['gamma']:.3f} PFL^{f['a']:.3f} CEL^{f['b']:.3f}"
              f"  (se a {f['se_a']:.3f}, b {f['se_b']:.3f})  cyber x{f['cyber_loading']:.2f} (se of log {f['se_cyber']:.2f})"
              f"  adj R2 {f['adj_r2']:.2f}")
    for p, w in s["wang"].items():
        print(f"wang lambda, {p}: median {w['median']:.3f}, range {w['low']:.3f}-{w['high']:.3f}, n={w['n']};"
              f" median multiple of EL {s['median_multiple'][p]:.2f}")


if __name__ == "__main__":
    main()
