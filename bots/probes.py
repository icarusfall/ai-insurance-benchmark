"""Probe bots: degenerate or single-change strategies that calibration must keep in check.

Each is a subject for benchmark mode, not an NPC. The calibration targets (see REVIEW.md) are that
the null bot scores well below the actuary, that no claims-handling shortcut beats it, and that
trivial actuary variants (margin up or down 10 points, no reinsurance) do not beat the reference either.
"""
import numpy as np

from . import actuary
from .actuary import ActuaryBot
from .base import Bot


class NullBot(Bot):
    """Writes nothing, decides nothing: the risk-free baseline."""
    name = "null"

    def act(self, view):
        return dict(quotes={}, decisions={}, ibnr=0.0, dividend=0.0)


class LiquidateBot(Bot):
    """Hands all the capital back in the first quarter and writes nothing: scores R of about 1 by construction."""
    name = "liquidate"

    def act(self, view):
        return dict(quotes={}, decisions={}, ibnr=0.0, dividend=view["own"]["reported_equity"] if view["q"] == 0 else 0.0)


class PayAllBot(ActuaryBot):
    """Actuary that leaves every claim undecided, so the engine pays it in full (the LLM harness default)."""
    name = "pay_all"

    def act(self, view):
        out = super().act(view)
        out["decisions"] = {}
        return out


class DenyAllBot(ActuaryBot):
    name = "deny_all"

    def act(self, view):
        out = super().act(view)
        out["decisions"] = {c["id"]: {"action": "deny"} for c in view["claims"]}
        return out


class ContestAllBot(ActuaryBot):
    name = "contest_all"

    def act(self, view):
        out = super().act(view)
        out["decisions"] = {c["id"]: {"action": "contest"} for c in view["claims"]}
        return out


class LowSettleBot(ActuaryBot):
    """Settles just above the acceptance line implied by murkiness (ignores precedent)."""
    name = "low_settle"

    def act(self, view):
        out = super().act(view)
        out["decisions"] = {c["id"]: {"action": "settle",
                                      "settle_pct": float(np.clip(0.9 * (0.95 - 0.7 * c["murk_obs"]) + 0.03, 0.05, 1.0))}
                            for c in view["claims"]}
        return out


class MarginUpBot(ActuaryBot):
    """Reference actuary with 10 points more margin."""
    name = "margin_up"

    def __init__(self):
        super().__init__(margin=actuary.MARGIN + 0.10)


class MarginDownBot(ActuaryBot):
    """Reference actuary with 10 points less margin."""
    name = "margin_down"

    def __init__(self):
        super().__init__(margin=actuary.MARGIN - 0.10)


class NoReinsBot(ActuaryBot):
    """Actuary without reinsurance (so its limits are cut to the net line cap)."""
    name = "no_reins"

    def treaty(self, own):
        return None


class TimidBot(ActuaryBot):
    """Actuary pricing, but quotes only a quarter of applicants."""
    name = "timid"

    def act(self, view):
        out = super().act(view)
        out["quotes"] = {k: v for k, v in out["quotes"].items() if k % 4 == 0}
        return out


PROBES = [NullBot, LiquidateBot, PayAllBot, DenyAllBot, ContestAllBot, LowSettleBot, MarginUpBot, MarginDownBot, NoReinsBot, TimidBot]
