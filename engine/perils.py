"""Catastrophe perils (v0.4): the shapes of catmodel/ scaled to the game. Shared by the world truth, the reinsurer
and the scripted actuary's prior."""
import math
from functools import lru_cache

import numpy as np

from . import loss
from . import params as P

_U = (np.arange(40) + 0.5) / 40
_SHARE2 = sum(s * s for s in P.PROVIDER_SHARES)
CONC_OUT = (1 - P.CONC_IN * _SHARE2) / (1 - _SHARE2)


def horizon(path: str, q: float) -> float:
    """AI capability (50% time horizon, hours) at quarter q on a path."""
    if path == "plateau":
        gap = math.log2(P.PLATEAU_CEILING / P.HORIZON_START)
        r = 1 / P.DOUBLING_Q["metr_2023"] / gap          # starts at the metr_2023 slope
        return P.HORIZON_START * 2 ** (gap * (1 - math.exp(-r * q)))
    return P.HORIZON_START * 2 ** (q / P.DOUBLING_Q[path])


def rate_mult(peril: str, h: float) -> float:
    p = P.PERILS[peril]
    return min(p["cap_mult"], (h / P.HORIZON_START) ** p["elasticity"])


def size_grid(peril: str) -> np.ndarray:
    """Event sizes S at 40 equally likely quantiles of a Pareto(1, alpha) truncated at cap."""
    p = P.PERILS[peril]
    a, cap = p["alpha"], p["cap"]
    return (1 - _U * (1 - cap ** -a)) ** (-1 / a)


def draw_size(peril: str, u: float) -> float:
    p = P.PERILS[peril]
    a, cap = p["alpha"], p["cap"]
    return float((1 - u * (1 - cap ** -a)) ** (-1 / a))


def hit_prob(peril: str, s: float) -> float:
    return min(P.HIT_MAX, P.PERILS[peril]["hit"] * math.sqrt(s))


def conc(peril: str, provider: int, traced) -> float:
    """Hit multiplier for a client of `provider` when the event is traced to vendor `traced` (None: every vendor)."""
    if traced is None:
        return 1.0
    return P.CONC_IN if traced == provider else CONC_OUT


def conc_mean(peril: str, provider) -> float:
    """Expected hit multiplier before the event is drawn (provider None: unknown vendor, 1 on average)."""
    if provider is None:
        return 1.0
    cm = P.PERILS[peril]["common_mode"]
    s = P.PROVIDER_SHARES[provider]
    return cm + (1 - cm) * (s * P.CONC_IN + (1 - s) * CONC_OUT)


@lru_cache(maxsize=None)
def event_layer_expectation(peril: str, size: int, limit: float, retention: float) -> float:
    """Expected covered loss on one client from one event of this peril, at concentration 1."""
    if not P.PERILS[peril]["insured"]:
        return 0.0
    tot = 0.0
    for s in size_grid(peril):
        tot += hit_prob(peril, s) * loss.cat_layer_expectation(size, limit, retention, round(math.sqrt(s), 4))
    return tot / len(_U)


def expected_quarter(provider, size: int, limit: float, retention: float, h: float) -> float:
    """Expected covered catastrophe loss on one client in a quarter at capability h (long-run rates, no gamma shock)."""
    return sum(p["rate"] * rate_mult(n, h) * conc_mean(n, provider) * event_layer_expectation(n, size, limit, retention)
               for n, p in P.PERILS.items() if p["insured"])
