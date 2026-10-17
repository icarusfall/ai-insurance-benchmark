"""Reckless, cycle-follower, predator and random bots."""
import math

import numpy as np

from engine import params as P

from . import priors
from .actuary import ActuaryBot
from .base import Bot
from engine.rng import stream


class RecklessBot(Bot):
    """Undercuts last quarter's market rate by 10%, never books IBNR, pays out profits."""
    name = "reckless"

    def reset(self, seed, seat):
        super().reset(seed, seat)
        self.last_eq = P.START_EQUITY

    def act(self, view):
        q = view["q"]
        pub = view["public"]
        quotes = {}
        if not view["own"]["restricted"]:
            for app in view["applicants"]:
                rol = pub["rol_by_sector_prev"].get(app["sector"])
                if rol:
                    prem = 0.9 * rol * app["ideal_limit"]
                else:
                    prem = 0.9 * priors.el_annual(app, app["ideal_limit"], app["default_retention"]) / 0.75
                quotes[app["id"]] = priors.quote_dict(app, prem)
        decisions = {cl["id"]: {"action": "deny" if cl["murk_obs"] > 0.25 else "pay"} for cl in view["claims"]}
        div = 0.0
        if q % 4 == 3:
            div = max(0.0, 0.5 * (view["own"]["reported_equity"] - self.last_eq))
            self.last_eq = view["own"]["reported_equity"]
        return dict(quotes=quotes, decisions=decisions, ibnr=0.0, dividend=div)


class CycleBot(Bot):
    """Prices at last quarter's market rate on line for the sector."""
    name = "cycle"

    def act(self, view):
        pub = view["public"]
        quotes = {}
        if not view["own"]["restricted"]:
            for app in view["applicants"]:
                rol = pub["rol_by_sector_prev"].get(app["sector"])
                prem = (rol * app["ideal_limit"] if rol
                        else 1.3 * priors.el_annual(app, app["ideal_limit"], app["default_retention"]))
                quotes[app["id"]] = priors.quote_dict(app, prem)
        decisions = {cl["id"]: {"action": "pay"} for cl in view["claims"]}
        return dict(quotes=quotes, decisions=decisions, ibnr=0.15 * view["own"]["npw4"], dividend=0.0)


class PredatorBot(ActuaryBot):
    """Actuary pricing, but undercuts hard while healthy and a rival is weak."""
    name = "predator"

    def act(self, view):
        rivals = [v for v in view["public"]["insurers"].values() if not v["is_me"] and not v["insolvent"]]
        weak = any(v["rating"] in ("D", "F") for v in rivals)
        healthy = view["own"]["rating_score"] > 0.8
        out = super().act(view)
        if weak and healthy:
            for qt in out["quotes"].values():
                qt["premium"] *= 0.85
        return out


class RandomBot(Bot):
    name = "random"

    def reset(self, seed, seat):
        super().reset(seed, seat)
        self.rng = stream(seed, f"bot:random:{seat}")

    def act(self, view):
        quotes = {}
        if not view["own"]["restricted"]:
            for app in view["applicants"]:
                el = priors.el_annual(app, app["ideal_limit"], app["default_retention"])
                quotes[app["id"]] = priors.quote_dict(app, el / 0.75 * math.exp(self.rng.normal(0, 0.4)))
        acts = ["pay", "settle", "deny", "contest"]
        decisions = {cl["id"]: {"action": acts[int(self.rng.integers(4))], "settle_pct": 0.7} for cl in view["claims"]}
        return dict(quotes=quotes, decisions=decisions, ibnr=float(self.rng.uniform(0, 0.3)) * view["own"]["npw4"],
                    dividend=0.0)
