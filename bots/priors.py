"""The scripted insurers' shared (slightly wrong) belief about risk.

Bots see only dossier signals, never hidden attributes. Their prior is the truth with fixed
per-sector bias and weaker risk-factor coefficients.
"""
import math

from engine import loss
from engine import perils
from engine import params as P

FREQ_BIAS = {"medical": 0.85, "finance": 1.10, "logistics": 0.90, "customer_service": 1.20,
             "legal_hr": 0.80, "infrastructure": 1.25, "defence": 0.75, "consumer": 1.05}
SEV_BIAS = 0.92
EXCL_DISCOUNT = {"upstream_excl": 0.08, "misuse_excl": 0.15}
EXPENSE_AND_MARGIN_DEFAULT = (P.EXPENSE, 0.05)


def el_annual(app: dict, limit: float, retention: float, upstream_excl: bool = False,
              misuse_excl: bool = False) -> float:
    s = P.SECTORS[app["sector"]]
    mods = math.exp(0.7 * P.B_AUTONOMY * (app["autonomy_signal"] - 0.5)
                    + 0.7 * P.B_SAFETY * (app["safety_signal"] - 0.5)
                    + 0.15 * len(app["red_flags"]))
    freq = s["freq"] * FREQ_BIAS[app["sector"]] * math.sqrt(P.SIZE_MULT[app["size_band"]]) * mods
    layer = loss.layer_expectation(app["sector"], app["size_band"], round(limit, 2), round(retention, 3), SEV_BIAS)
    el = freq * layer
    if upstream_excl:
        el *= 1 - EXCL_DISCOUNT["upstream_excl"]
    if misuse_excl:
        el *= 1 - EXCL_DISCOUNT["misuse_excl"]
    return el


def cat_el_annual(app: dict, limit: float, retention: float, horizon: float) -> float:
    """Expected catastrophe loss over a year at the published capability, from the textbook peril model (v0.4).
    An undisclosed vendor counts as an average one."""
    prov = P.PROVIDER_NAMES.index(app["provider"]) if app.get("provider") in P.PROVIDER_NAMES else None
    return 4 * perils.expected_quarter(prov, app["size_band"], round(limit, 2), round(retention, 3), horizon)


def quote_limit(app: dict, own: dict, treaty) -> float:
    """The client's ideal limit, cut down to what the single-risk rule allows under the given treaty."""
    return min(app["ideal_limit"], loss.max_gross_limit(own["max_net_line"], treaty))


def quote_dict(app: dict, premium: float, limit: float = None) -> dict:
    return dict(premium=premium, limit=app["ideal_limit"] if limit is None else limit, retention=app["default_retention"],
                cat_carveout=False, upstream_excl=False, misuse_excl=False)
