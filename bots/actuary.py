"""Actuary-bot: expected loss + margin, learns a credibility multiplier per sector, books IBNR."""
import math
from collections import defaultdict

import numpy as np

from engine import params as P

from . import priors
from .base import Bot


MARGIN = 0.35   # the reference's profit margin; set by the calibration sweep (see CALIBRATION.md; v0.1: 0.10)


class ActuaryBot(Bot):
    name = "actuary"

    def __init__(self, margin: float = None, cat_load: float = 0.5, cred_k: float = 6.0, maturity: int = 8,
                 div_buffer: float = 10.0):
        self.margin = MARGIN if margin is None else margin
        self.cat_load, self.cred_k, self.maturity = cat_load, cred_k, maturity
        self.div_buffer = div_buffer

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
    def price(self, app, q, retreat=1.0, limit=None, horizon=P.HORIZON_START):
        lim = app["ideal_limit"] if limit is None else limit
        raw = priors.el_annual(app, lim, app["default_retention"])
        self.quoted[app["id"]] = (app["sector"], raw)
        cat = priors.cat_el_annual(app, lim, app["default_retention"], horizon)   # v0.4: priced explicitly, loaded
        gross = raw * self.mult(app["sector"], q) + cat * (1 + self.cat_load)
        return gross / (1 - P.EXPENSE - self.margin) * retreat

    def act(self, view):
        q = view["q"]
        own = view["own"]
        quotes = {}
        treaty = self.treaty(own)
        if not own["restricted"]:
            retreat = 1.3 if own["rating_score"] < 0.35 else 1.0
            # capacity discipline: don't write more premium than capital supports
            cap = max(own["reported_equity"], 0.0) / (2 * P.K_REG)
            running = own["npw4"]
            live = sum(1 for v in view["public"]["insurers"].values() if not v["insolvent"])
            win_guess = 1.0 / max(1, live)
            for app in sorted(view["applicants"], key=lambda a: not a["renewal"]):
                lim = priors.quote_limit(app, own, treaty)
                if lim <= 0:
                    continue
                prem = self.price(app, q, retreat, lim, view["public"]["horizon_hours"])
                if running > cap:
                    prem *= 1.6
                else:
                    running += prem * win_guess
                quotes[app["id"]] = priors.quote_dict(app, prem, lim)
        decisions = {}
        for cl in view["claims"]:
            self.inc[cl["occ_q"]][cl["sector"]] += cl["covered"]
            if cl["murk_obs"] < 0.3:
                decisions[cl["id"]] = {"action": "pay"}
            else:
                decisions[cl["id"]] = {"action": "settle", "settle_pct": float(np.clip(1 - 0.8 * cl["murk_obs"], 0.3, 0.95))}
        raise_amt = 0.0
        ratio = own.get("solvency_ratio")
        if own["restricted"] or own["rating_score"] < 0.3 or (ratio is not None and ratio < 1.1 * P.LADDER["restricted"]):
            target = 1.4 * P.LADDER["no_dividends"] * own["required_capital"]      # back above the dividend line
            raise_amt = float(np.clip(target - own["audited_equity"], 0.0, 0.5 * P.START_EQUITY))
        dividend = 0.0
        if q % 4 == 3 and not own["restricted"]:
            dividend = max(0.0, own["reported_equity"] - (2 * P.K_REG * own["npw4"] + self.div_buffer))
        return dict(quotes=quotes, decisions=decisions, ibnr=self.ibnr(q), dividend=dividend,
                    reinsurance=treaty, raise_capital=raise_amt)

    def treaty(self, own):
        """Buy exactly what the single-risk rule needs: attach at the net line cap, cover up to the largest limit."""
        att = max(0.5, math.floor(own["max_net_line"] * 2) / 2)
        top = P.IDEAL_LIMIT_PER_SIZE * P.SIZE_MULT[-1]
        return {"attachment": att, "limit": max(1.0, top - att)} if att < top else None

    def ibnr(self, q):
        m = self.overall_mult(q)
        tot = 0.0
        for t in range(max(0, q - 7), q + 1):
            ult = sum(self.expo[t].values()) * m
            rep = sum(self.inc[t].values())
            tot += max(ult - rep, 0.0)
        return tot
