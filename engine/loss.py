"""Severity model and expected layer losses (shared by the engine truth and bot priors)."""
import math
from functools import lru_cache
from statistics import NormalDist

import numpy as np

from . import params as P

_ND = NormalDist()
_ZG = np.array([_ND.inv_cdf((i + 0.5) / 200) for i in range(200)])
_TG = ((np.arange(40) + 0.5) / 40) ** (-1.0 / P.TAIL_ALPHA)


def base_severity(sector: str, size: int, z: float, sev_bias: float = 1.0) -> float:
    s = P.SECTORS[sector]
    return math.exp(math.log(s["median"]) + s["sigma"] * z) * math.sqrt(P.SIZE_MULT[size]) * sev_bias


def severity(sector: str, size: int, z: float, u_tail: float) -> float:
    x = base_severity(sector, size, z)
    if u_tail < P.TAIL_P:
        x *= P.TAIL_XM * max(u_tail / P.TAIL_P, 1e-6) ** (-1.0 / P.TAIL_ALPHA)
    return x


def layer(x: float, retention: float, limit: float) -> float:
    return min(max(x - retention, 0.0), limit)


@lru_cache(maxsize=None)
def layer_expectation(sector: str, size: int, limit: float, retention: float,
                      sev_bias: float = 1.0) -> float:
    """E[min(max(X - retention, 0), limit)] per incident."""
    s = P.SECTORS[sector]
    scale = math.sqrt(P.SIZE_MULT[size]) * sev_bias
    base = np.exp(math.log(s["median"]) + s["sigma"] * _ZG) * scale

    def lay(x):
        return np.minimum(np.maximum(x - retention, 0.0), limit)

    e_base = lay(base).mean()
    e_tail = lay(base[:, None] * P.TAIL_XM * _TG[None, :]).mean()
    return (1 - P.TAIL_P) * e_base + P.TAIL_P * e_tail


# catastrophe gross loss = CAT_SCALE_PER_SIZE * SIZE_MULT * exp(-2.65 + 0.8 z) * sev_mult, sev_mult ~ lognormal(0, 0.3)
CAT_MU = -2.65
CAT_SIGMA = math.sqrt(0.8 ** 2 + 0.3 ** 2)
CAT_HIT_MEAN = (0.012 + 0.03) / 2          # mean of the per-event hit probability (world._make_events)


@lru_cache(maxsize=None)
def cat_layer_expectation(size: int, limit: float, retention: float) -> float:
    """E[min(max(X - retention, 0), limit)] for one catastrophe hit on a client of this size."""
    base = np.exp(math.log(P.CAT_SCALE_PER_SIZE * P.SIZE_MULT[size]) + CAT_MU + CAT_SIGMA * _ZG)
    return float(np.minimum(np.maximum(base - retention, 0.0), limit).mean())


def treaty_terms(r):
    """Normalise a requested treaty the way the reinsurer writes it (attachment in 0.5 steps, whole-number limit)."""
    if not r:
        return None
    return {"attachment": max(0.5, round(float(r["attachment"]) * 2) / 2), "limit": max(1.0, round(float(r["limit"])))}


def layer_split(limit: float, reins) -> tuple:
    """(net retained, ceded) parts of a policy limit under a per-claim XoL treaty {attachment, limit} or None."""
    if not reins:
        return limit, 0.0
    ceded = min(max(limit - reins["attachment"], 0.0), reins["limit"])
    return limit - ceded, ceded


def max_gross_limit(net_cap: float, reins) -> float:
    """Largest policy limit whose net retained part stays within net_cap under the given treaty."""
    if reins and reins["attachment"] <= net_cap:
        return net_cap + reins["limit"]
    return net_cap
