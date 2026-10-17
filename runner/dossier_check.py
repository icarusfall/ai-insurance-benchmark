"""How much of the true (log) expected loss can be recovered from what a dossier reveals?"""
import math

import numpy as np

from engine import loss, params as P
from engine.world import World


def design(c, W, hidden):
    sec = [1.0 if c.sector == s else 0.0 for s in P.SECTOR_NAMES]
    prov = [1.0 if (c.provider == i and (hidden or c.provider_stated)) else 0.0 for i in range(6)]
    x = sec + prov + [c.size, len(c.red_flags)]
    if hidden:
        x += [c.autonomy, c.safety, float(c.corner), math.log(c.unk)]
    else:
        x += [c.autonomy_obs, c.safety_obs]
    return x


def r2(X, y):
    X = np.array(X); y = np.array(y)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    return 1 - res.var() / y.var()


def main():
    ys, Xd, Xh = [], [], []
    for seed in range(5):
        W = World(seed)
        for c in W.clients:
            lam = W.lam_base(c, 0)
            el = 4 * lam * loss.layer_expectation(c.sector, c.size, round(c.ideal_limit, 2), round(c.default_retention, 3))
            ys.append(math.log(el))
            Xd.append(design(c, W, False)); Xh.append(design(c, W, True))
    print(f"n={len(ys)} clients")
    print(f"R^2 of log expected loss from dossier fields only : {r2(Xd, ys):.2f}")
    print(f"R^2 if hidden attributes were visible (ceiling)   : {r2(Xh, ys):.2f}")

if __name__ == "__main__":
    main()
