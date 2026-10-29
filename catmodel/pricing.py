"""The layer stack above the mutual's claims, the premium, and catastrophe bond pricing.

Stack, bottom up: the mutual's claims are first reduced by any reinsurance or cat bond layer, then by a government
share above an attachment (TRIA-style, free at the point of cover). What is left is met from premium (net of
expenses), then paid-in capital, then calls on members up to their callable amount. Anything beyond that is unpaid:
it falls back on the victims.
"""
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from .model import Settings, Years

_N = NormalDist()

# Lane's equation EER = gamma PFL^a CEL^b: spread, probability of first loss and expected loss given a loss, all decimals
# of par. LANE_2000 is his fit to 16 tranches from 1999 (p. 273). LANE is our re-fit to 58 natural catastrophe and 9
# cyber tranches from 2023-26 (python -m catmodel.catbond_fit): the same slopes for both, cyber priced at `cyber` times.
LANE_2000 = dict(gamma=0.55, a=0.495, b=0.574, cyber=1.0)
LANE = dict(gamma=0.490, a=0.591, b=0.017, cyber=2.14)


def lane_spread(pfl: float, cel: float, coef: dict = LANE, cyber: bool = False) -> float:
    if pfl <= 0 or cel <= 0:
        return 0.0
    return coef["gamma"] * (coef["cyber"] if cyber else 1.0) * pfl ** coef["a"] * cel ** coef["b"]


def layer(x, attach: float, limit: float):
    return np.minimum(np.maximum(x - attach, 0.0), limit)


@dataclass
class Stack:
    claims: np.ndarray
    reinsured: np.ndarray
    government: np.ndarray
    net: np.ndarray               # the mutual's own share
    premium: float                # technical premium, whole mutual
    reinsurance_cost: float
    calls: np.ndarray             # assessments on members actually made
    unpaid: np.ndarray            # claims nobody pays


def var(x, p: float) -> float:
    return float(np.quantile(x, p))


def tvar(x, p: float) -> float:
    q = var(x, p)
    tail = x[x >= q]
    return float(tail.mean()) if len(tail) else q


def scr(net: np.ndarray) -> float:
    """One-year 99.5% VaR of the mutual's own losses, less their expectation (Solvency II style)."""
    return max(var(net, 0.995) - float(net.mean()), 0.0)


def build_stack(s: Settings, y: Years) -> Stack:
    c = y.claims
    r = layer(c, s.reinsurance_attach, s.reinsurance_limit) if s.reinsurance_limit > 0 else np.zeros_like(c)
    g = s.government_share * np.maximum(c - r - s.government_attach, 0.0) if s.government_share > 0 else np.zeros_like(c)
    net = c - r - g
    ri_cost = s.catbond_multiple * float(r.mean())          # priced like a cat bond: a multiple of expected loss
    premium = (float(net.mean()) + ri_cost + s.cost_of_capital * scr(net)) / (1 - s.expense_ratio)
    resources = premium * (1 - s.expense_ratio) + s.paid_in_capital
    gap = np.maximum(net - resources, 0.0)
    calls = np.minimum(gap, s.members * s.callable_per_member)
    return Stack(claims=c, reinsured=r, government=g, net=net, premium=premium, reinsurance_cost=ri_cost,
                 calls=calls, unpaid=gap - calls)


def catbond(x: np.ndarray, attach: float, exhaust: float, multiple: float, wang_lambda: float) -> dict:
    """Metrics for a bond paying the layer [attach, exhaust] of annual losses x (an indemnity trigger)."""
    limit = exhaust - attach
    pa, pe = float((x > attach).mean()), float((x > exhaust).mean())
    el = float(layer(x, attach, limit).mean()) / limit
    cel = el / pa if pa > 0 else 0.0
    lane, lane_natcat = lane_spread(pa, cel, cyber=True), lane_spread(pa, cel)
    grid = np.linspace(attach, exhaust, 401)
    xs = np.sort(x)
    sf = 1 - np.searchsorted(xs, grid, side="right") / len(xs)
    distorted = np.array([_N.cdf(_N.inv_cdf(u) + wang_lambda) if 0 < u < 1 else float(u) for u in sf])
    wang = float(np.trapezoid(distorted, grid)) / limit
    return dict(attach=attach, exhaust=exhaust, prob_attach=pa, prob_exhaust=pe, expected_loss=el,
                spread_multiple=multiple * el, spread_lane=lane, spread_lane_natcat=lane_natcat, spread_wang=wang)
