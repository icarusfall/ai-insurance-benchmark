"""Actuary-bot: expected loss + margin, learns a credibility multiplier per sector, books IBNR."""
import math
from collections import defaultdict

import numpy as np

from engine import params as P

from . import priors
from .base import Bot


class ActuaryBot(Bot):
    name = "actuary"

    def __init__(self, margin: float = 0.10, cat_load: float = 0.25, cred_k: float = 6.0, maturity: int = 8):
        self.margin, self.cat_load, self.cred_k, self.maturity = margin, cat_load, cred_k, maturity

    def reset(self, seed, seat):
        super().reset(seed, seat)
        self.expo = defaultdict(lambda: defaultdict(float))   # occ_q -> sector -> raw model EL
        self.inc = defaultdict(lambda: defaultdict(float))    # occ_q -> sector -> reported covered loss
        self.quoted = {}                                       # client -> (sector, raw_el)

    # ---- learning
    def mult(self, sector: str, q: int) -> float:
        hi = q - self.maturity
        e = sum(self.expo[t][sector] for t in range(0, hi + 1))
        i = sum(self.inc[t][sector] for t in range(0, hi + 1))
        return float(np.clip((self.cred_k + i) / (self.cred_k + e), 0.6, 2.0))

    def overall_mult(self, q: int) -> float:
        hi = q - self.maturity
        e = sum(sum(self.expo[t].values()) for t in range(0, hi + 1))
        i = sum(sum(self.inc[t].values()) for t in range(0, hi + 1))
        return float(np.clip((self.cred_k + i) / (self.cred_k + e), 0.6, 2.0))

    def on_bound(self, client, q, info):
        rec = self.quoted.get(client)
        if rec:
            sector, raw = rec
            for t in range(q, q + P.POLICY_TERM):
                self.expo[t][sector] += raw / P.POLICY_TERM

    # ---- pricing
    def price(self, app, q, retreat=1.0):
        raw = priors.el_annual(app, app["ideal_limit"], app["default_retention"])
        self.quoted[app["id"]] = (app["sector"], raw)
        gross = raw * self.mult(app["sector"], q) * (1 + self.cat_load)
        return gross / (1 - P.EXPENSE - self.margin) * retreat

    def act(self, view):
        q = view["q"]
        own = view["own"]
        quotes = {}
        if not own["restricted"]:
            retreat = 1.3 if own["rating_score"] < 0.35 else 1.0
            # capacity discipline: don't write more premium than capital supports
            cap = max(own["reported_equity"], 0.0) / (2 * P.K_REG)
            running = own["npw4"]
            live = sum(1 for v in view["public"]["insurers"].values() if not v["insolvent"])
            win_guess = 1.0 / max(1, live)
            for app in sorted(view["applicants"], key=lambda a: not a["renewal"]):
                prem = self.price(app, q, retreat)
                if running > cap:
                    prem *= 1.6
                else:
                    running += prem * win_guess
                quotes[app["id"]] = priors.quote_dict(app, prem)
        decisions = {}
        for cl in view["claims"]:
            self.inc[cl["occ_q"]][cl["sector"]] += cl["covered"]
            if cl["murk_obs"] < 0.3:
                decisions[cl["id"]] = {"action": "pay"}
            else:
                decisions[cl["id"]] = {"action": "settle", "settle_pct": float(np.clip(1 - 0.8 * cl["murk_obs"], 0.3, 0.95))}
        att = round(max(0.5, 0.12 * max(own["reported_equity"], 3.0)) * 2) / 2
        return dict(quotes=quotes, decisions=decisions, ibnr=self.ibnr(q), dividend=0.0,
                    reinsurance={"attachment": att, "limit": 10 * att})

    def ibnr(self, q):
        m = self.overall_mult(q)
        tot = 0.0
        for t in range(max(0, q - 7), q + 1):
            ult = sum(self.expo[t].values()) * m
            rep = sum(self.inc[t].values())
            tot += max(ult - rep, 0.0)
        return tot
