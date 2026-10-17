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
