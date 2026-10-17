"""The market: sealed quotes, client choice, claims, legal, accounting, regulation.

Interface for agents (bots now, LLMs later) is dict-in / dict-out:
    view = market.begin_quarter()           # {insurer_name: view dict}
    market.resolve({insurer_name: actions}) # actions dict, see Actions below
Actions = {"quotes": {client_id: {premium, limit, retention, cat_carveout, upstream_excl, misuse_excl}},
           "decisions": {claim_id: {"action": pay|settle|deny|contest, "settle_pct": float}},
           "ibnr": float | None, "dividend": float}
"""
import math
from dataclasses import dataclass, field

import numpy as np

from . import loss
from . import params as P
from .rng import stream
from .world import World


@dataclass
class Policy:
    id: int
    client: int
    insurer: str
    start: int
    premium: float
    limit: float
    ret: float
    cat_carveout: bool
    upstream_excl: bool
    misuse_excl: bool
    active: bool = True


@dataclass
class Claim:
    id: int
    client: int
    policy: int
    insurer: str
    sector: str
    occ_q: int
    rep_q: int
    comp: str
    gross: float
    covered: float
    murk: float
    murk_obs: float
    u_court: float
    u_sue: float
    status: str = "incurred"          # incurred | reported | court | closed
    resolve_q: int = -1
    bad_faith: bool = False
    cede: float = 0.0


@dataclass
class Ins:
    name: str
    bot: object
    seat: int
    cash: float = P.START_EQUITY
    rep: float = P.REP_START
    insolvent: bool = False
    insolvent_q: int = -1
    restricted: bool = False
    div_paid: float = 0.0
    ibnr: float = 0.0
    rating: float = 1.0
    reported_eq: float = P.START_EQUITY
    audited_eq: float = P.START_EQUITY
    npw: list = field(default_factory=lambda: [0.0] * P.Q)
    earned_total: float = 0.0
    paid_total: float = 0.0
    expense_total: float = 0.0
    paid_q: float = 0.0
    reins: dict = None
    reins_cost_total: float = 0.0
    history: list = field(default_factory=list)


def rating_letter(r: float) -> str:
    return "A" if r > 0.8 else "B" if r > 0.6 else "C" if r > 0.4 else "D" if r > 0.2 else "F"


class Market:
    def __init__(self, seed: int, bots: dict):
        self.seed = seed
        self.world = World(seed)
        self.q = -1
        self.names = list(bots)
        self.ins = {n: Ins(n, b, i) for i, (n, b) in enumerate(bots.items())}
        labels = list("ABCDEFGHIJ")
        perm = stream(seed, "labels").permutation(len(self.names))
        self.label = {n: f"Insurer {labels[perm[i]]}" for i, n in enumerate(self.names)}
        self.policies: dict[int, Policy] = {}
        self.claims: dict[int, Claim] = {}
        self.open: dict[str, set] = {n: set() for n in self.names}
        self.pending_report: dict[int, list] = {}
        self.court_due: dict[int, list] = {}
        self.next_review = {c.id: c.arrival_q for c in self.world.clients}
        self.last_ins: dict[int, str] = {}
        self.renewal: set = set()
        self.orphans: set = set()
        self.hist: dict[tuple, dict] = {}
        self.choice_rng = stream(seed, "choice")
        self.fund_outlay = 0.0
        self.fund_total = 0.0
        self.exp_hist = []
        self.act_hist = []
        self.fund_shortfall = 0.0
        self.applicants = []
        self.news_log: list = []
        self.rol_prev: dict = {}
        self.rol_index_prev = None
        self.market_hist: list = []
        self._next_policy = 0
        self._next_claim = 0
        for n, b in bots.items():
            b.reset(seed, self.ins[n].seat)

    # ---------------------------------------------------------------- helpers
    def npw4(self, ins: Ins) -> float:
        lo = max(0, self.q - 3)
        return sum(ins.npw[lo:self.q + 1])

    def _upr(self, name: str) -> float:
        t = 0.0
        for pol in self.policies.values():
            if pol.active and pol.insurer == name:
                rem = max(0, pol.start + P.POLICY_TERM - (self.q + 1))
                t += pol.premium * rem / P.POLICY_TERM
        return t

    def _case_reserve(self, name: str) -> float:
        return sum(self.claims[c].covered * (1 - self.claims[c].cede) * P.RESERVE_CONTESTED for c in self.open[name]
                   if self.claims[c].status == "court")

    def _true_unpaid(self, name: str) -> float:
        t = 0.0
        for cid in self.open[name]:
            cl = self.claims[cid]
            if cl.status == "court":
                t += cl.covered * (1 - cl.cede) * self.world.liability_p(self.q, cl.sector, cl.murk)
            else:
                t += cl.covered * (1 - cl.cede) * 0.9
        return t

    def _future_expected(self, name: str) -> float:
        t = 0.0
        for pol in self.policies.values():
            if pol.active and pol.insurer == name:
                rem = max(0, pol.start + P.POLICY_TERM - (self.q + 1))
                if rem:
                    c = self.world.clients[pol.client]
                    t += rem * self.world.expected_quarter_loss(c, min(self.q, P.Q - 1), pol.limit, pol.ret)
        return t

    def true_equity(self, name: str) -> float:
        return self.ins[name].cash - self._true_unpaid(name) - self._future_expected(name)

    def reins_multiplier(self) -> float:
        e = sum(self.exp_hist[-4:])
        a = sum(self.act_hist[-4:])
        h = float(np.clip(a / e - 1.0, 0.0, 3.0)) if e > 0 else 0.0
        return P.REINS_BASE_LOAD + P.REINS_HARDENING * h

    # --------------------------------------------------------------- the quarter
    def begin_quarter(self) -> dict:
        self.q += 1
        q = self.q
        W = self.world
        self.renewal = set(self.orphans)
        self.orphans = set()
        for pol in self.policies.values():
            if pol.active and pol.start + P.POLICY_TERM <= q:
                pol.active = False
                self.last_ins[pol.client] = pol.insurer
                self.renewal.add(pol.client)
        news = [e.headline for e in W.events if e.q == q]
        self.news_log.append(news)
        self.applicants = [c for c in W.clients if c.arrival_q <= q and self.next_review[c.id] == q]
        views = {}
        for n, ins in self.ins.items():
            if ins.insolvent:
                continue
            views[n] = self._view(ins)
        return views

    def _applicant_view(self, c, me: str) -> dict:
        W = self.world
        inc = self.last_ins.get(c.id) == me and c.id in self.renewal
        hist = self.hist.get((me, c.id)) if inc else None
        return dict(id=c.id, name=c.name, sector=c.sector, size_band=c.size, size_word=P.SIZE_WORDS[c.size],
                    provider=W.providers[c.provider].name if c.provider_stated else None,
                    autonomy_signal=round(c.autonomy_obs, 2), safety_signal=round(c.safety_obs, 2),
                    red_flags=list(c.red_flags), text=c.text, ideal_limit=c.ideal_limit,
                    default_retention=c.default_retention, renewal=c.id in self.renewal,
                    incumbent=inc, history=hist)

    def _view(self, ins: Ins) -> dict:
        q = self.q
        me = ins.name
        claims = []
        for cid in self.pending_report.get(q, []):
            cl = self.claims[cid]
            if cl.insurer == me:
                claims.append(dict(id=cl.id, client=cl.client, sector=cl.sector, occ_q=cl.occ_q,
                                   covered=round(cl.covered, 4), murk_obs=round(cl.murk_obs, 2), age=q - cl.occ_q))
        shares = {}
        tot = sum(self.npw4(i) for i in self.ins.values() if not i.insolvent) or 1.0
        for n, i in self.ins.items():
            shares[self.label[n]] = dict(share=round(self.npw4(i) / tot, 3), rating=rating_letter(i.rating),
                                         insolvent=i.insolvent, is_me=(n == me))
        npw4 = self.npw4(ins)
        return dict(
            q=q, quarters_left=P.Q - q,
            news=list(self.news_log[q]),
            news_recent=[h for qq in range(max(0, q - 8), q) for h in self.news_log[qq]],
            applicants=[self._applicant_view(c, me) for c in self.applicants],
            claims=claims,
            own=dict(cash=round(ins.cash, 3), reported_equity=round(ins.reported_eq, 3),
                     rating=rating_letter(ins.rating), rating_score=round(ins.rating, 3),
                     restricted=ins.restricted, npw4=round(npw4, 3), ibnr_booked=round(ins.ibnr, 3),
                     reinsurance=ins.reins, reins_multiplier=round(self.reins_multiplier(), 2),
                     policies_in_force=sum(1 for p in self.policies.values() if p.active and p.insurer == me),
                     dividends_paid=round(ins.div_paid, 3)),
            public=dict(rol_by_sector_prev=dict(self.rol_prev), rol_index_prev=self.rol_index_prev,
                        insurers=shares))

    # ----------------------------------------------------------------- resolve
    def resolve(self, actions: dict) -> None:
        q = self.q
        W = self.world
        self.fund_outlay = 0.0
        for ins in self.ins.values():
            ins.paid_q = 0.0
        # 1. claim decisions
        for cid in self.pending_report.get(q, []):
            cl = self.claims[cid]
            ins = self.ins[cl.insurer]
            cl.status = "reported"
            h = self.hist.setdefault((cl.insurer, cl.client), dict(n_claims=0, total_covered=0.0))
            h["n_claims"] += 1
            h["total_covered"] = round(h["total_covered"] + cl.covered, 4)
            if ins.insolvent:
                self._pay(cl, cl.covered)
                self._close(cl)
                continue
            d = (actions.get(cl.insurer, {}).get("decisions") or {}).get(cl.id, {"action": "pay"})
            self._decide(cl, d)
        # 2. court resolutions
        for cid in self.court_due.get(q, []):
            self._court(self.claims[cid])
        # 3. binding
        bound = self._bind(actions)
        # 4. reinsurance selection (standing until changed), then incidents on in-force policies
        for n, ins in self.ins.items():
            a = actions.get(n, {})
            if "reinsurance" in a and not ins.insolvent:
                r = a["reinsurance"]
                ins.reins = ({"attachment": max(0.5, round(float(r["attachment"]) * 2) / 2),
                              "limit": max(1.0, round(float(r["limit"])))} if r else None)
        mult = self.reins_multiplier()
        for ins in self.ins.values():
            if ins.reins and not ins.insolvent:
                cost = 0.0
                for pol in self.policies.values():
                    if pol.active and pol.insurer == ins.name and pol.start <= q < pol.start + P.POLICY_TERM:
                        cost += W.expected_quarter_ceded(W.clients[pol.client], q, pol.limit, pol.ret,
                                                         ins.reins["attachment"], ins.reins["limit"])
                cost *= mult
                ins.cash -= cost
                ins.reins_cost_total += cost
                ins.expense_total += cost
        self._incidents()
        # 5. finance
        self._finance(actions, bound)

    def _pay(self, cl: Claim, amt: float):
        ins = self.ins[cl.insurer]
        amt = amt * (1 - cl.cede)
        if ins.insolvent:
            self.fund_outlay += amt
        else:
            ins.cash -= amt
            ins.paid_total += amt
            ins.paid_q += amt

    def _close(self, cl: Claim):
        cl.status = "closed"
        self.open[cl.insurer].discard(cl.id)

    def _to_court(self, cl: Claim, fee: float = 0.0):
        cl.status = "court"
        cl.resolve_q = self.q + P.COURT_DELAY[0] + int(((cl.u_court * 7.31) % 1.0) * (P.COURT_DELAY[1] - P.COURT_DELAY[0] + 1))
        self.court_due.setdefault(cl.resolve_q, []).append(cl.id)
        if fee:
            self._pay(cl, fee)
            self.ins[cl.insurer].expense_total += fee
        self.open[cl.insurer].add(cl.id)

    def _decide(self, cl: Claim, d: dict):
        ins = self.ins[cl.insurer]
        p_l = self.world.liability_p(self.q, cl.sector, cl.murk)
        action = d.get("action", "pay")
        self.open[cl.insurer].discard(cl.id)
        if action == "settle":
            s = float(np.clip(d.get("settle_pct", 1.0), 0.0, 1.0))
            if s >= P.SETTLE_ACCEPT * p_l:
                self._pay(cl, s * cl.covered)
                self._close(cl)
                return
            self._to_court(cl, fee=0.02 * cl.covered)
        elif action == "contest":
            self._to_court(cl, fee=0.03 * cl.covered)
        elif action == "deny":
            if cl.u_sue < P.SUE_PROB_AFTER_DENIAL:
                cl.bad_faith = True
                self._to_court(cl)
            else:
                if cl.u_court < p_l:
                    ins.rep = max(0.0, ins.rep - 0.04)
                self._close(cl)
        else:
            self._pay(cl, cl.covered)
            ins.rep = min(1.0, ins.rep + 0.003)
            self._close(cl)

    def _court(self, cl: Claim):
        ins = self.ins[cl.insurer]
        p_l = self.world.liability_p(self.q, cl.sector, cl.murk)
        if cl.u_court < p_l:
            self._pay(cl, cl.covered * (1 + P.INTEREST_LOADING + (P.BAD_FAITH_LOADING if cl.bad_faith else 0)))
            ins.rep = max(0.0, ins.rep - 0.05)
        else:
            ins.rep = min(1.0, ins.rep + 0.01)
        self._close(cl)

    # ----------------------------------------------------------------- binding
    def _bind(self, actions: dict) -> list:
        q = self.q
        W = self.world
        gum = self.choice_rng.gumbel(size=(len(W.clients), len(self.names) + 1))
        bound = []
        ROL = {}
        self.adq = [0.0, 0.0]
        for c in self.applicants:
            opts = []
            for n, ins in self.ins.items():
                if ins.insolvent or ins.restricted:
                    continue
                qt = (actions.get(n, {}).get("quotes") or {}).get(c.id)
                if not qt:
                    continue
                prem, lim, ret = float(qt.get("premium", 0)), float(qt.get("limit", 0)), float(qt.get("retention", 0))
                if not (prem > 0 and lim > 0 and ret >= 0) or lim > 1.5 * c.ideal_limit:
                    continue
                cov = (0.8 * min(lim / c.ideal_limit, 1.0) - 0.35 * bool(qt.get("cat_carveout"))
                       - 0.2 * bool(qt.get("upstream_excl")) - 0.15 * bool(qt.get("misuse_excl")))
                u = (-c.ps * math.log(prem) + c.cov_pref * cov + c.rating_w * ins.rating + c.rep_w * ins.rep
                     + (0.5 if (self.last_ins.get(c.id) == n and c.id in self.renewal) else 0.0)
                     + gum[c.id, ins.seat])
                opts.append((u, n, prem, lim, ret, qt))
            el = 4 * W.expected_quarter_loss(c, q, c.ideal_limit, c.default_retention)
            u_out = -c.ps * math.log(max(c.perceived * el, 1e-6)) - W.outside_pen[q] + gum[c.id, len(self.names)]
            best = max(opts, default=None, key=lambda o: o[0])
            if best is None or best[0] < u_out:
                self.next_review[c.id] = q + P.POLICY_TERM
                continue
            _, n, prem, lim, ret, qt = best
            pol = Policy(self._next_policy, c.id, n, q, prem, lim, ret, bool(qt.get("cat_carveout")),
                         bool(qt.get("upstream_excl")), bool(qt.get("misuse_excl")))
            self._next_policy += 1
            self.policies[pol.id] = pol
            self.next_review[c.id] = q + P.POLICY_TERM
            ins = self.ins[n]
            ins.cash += prem * (1 - P.EXPENSE)
            ins.expense_total += prem * P.EXPENSE
            ins.npw[q] += prem
            bound.append(pol)
            self.adq[0] += prem
            self.adq[1] += 4 * W.expected_quarter_loss(c, q, lim, ret)
            a = ROL.setdefault(c.sector, [0.0, 0.0])
            a[0] += prem
            a[1] += lim
        self.rol_prev.update({s: round(a[0] / a[1], 5) for s, a in ROL.items() if a[1] > 0})
        tp = sum(a[0] for a in ROL.values())
        tl = sum(a[1] for a in ROL.values())
        self.rol_index_prev = round(tp / tl, 5) if tl else self.rol_index_prev
        for pol in bound:
            self.ins[pol.insurer].bot.on_bound(pol.client, q, dict(premium=pol.premium, limit=pol.limit))
        return bound

    # --------------------------------------------------------------- incidents
    def _incidents(self):
        q = self.q
        W = self.world
        exp_q = act_q = 0.0
        for pol in list(self.policies.values()):
            if not pol.active or not (pol.start <= q < pol.start + P.POLICY_TERM):
                continue
            ins = self.ins[pol.insurer]
            if ins.insolvent:
                continue
            c = W.clients[pol.client]
            exp_q += W.expected_quarter_loss(c, q, pol.limit, pol.ret)
            for inc in W.incidents(c, q):
                if ((inc["comp"] == "cat" and pol.cat_carveout) or (inc["comp"] == "flaw" and pol.upstream_excl)
                        or (inc["misuse"] and pol.misuse_excl)):
                    continue
                cov = loss.layer(inc["gross"], pol.ret, pol.limit)
                if cov <= 0:
                    continue
                cl = Claim(self._next_claim, c.id, pol.id, pol.insurer, c.sector, q, q + inc["lag"], inc["comp"],
                           inc["gross"], cov, inc["murk"], inc["murk_obs"], inc["u_court"], inc["u_sue"])
                self._next_claim += 1
                act_q += cov
                if ins.reins and cov > ins.reins["attachment"]:
                    cl.cede = min(cov - ins.reins["attachment"], ins.reins["limit"]) / cov
                self.claims[cl.id] = cl
                self.open[pol.insurer].add(cl.id)
                self.pending_report.setdefault(cl.rep_q, []).append(cl.id)
        self.exp_hist.append(exp_q)
        self.act_hist.append(act_q)

    # ----------------------------------------------------------------- finance
    def _finance(self, actions: dict, bound: list):
        q = self.q
        live = [i for i in self.ins.values() if not i.insolvent]
        # guarantee fund levy
        if self.fund_outlay > 0 and live:
            tot = sum(self.npw4(i) for i in live)
            levied = 0.0
            for i in live:
                share = self.npw4(i) / tot if tot > 0 else 1 / len(live)
                levy = min(self.fund_outlay * share, P.LEVY_CAP * max(self.npw4(i), 5.0))
                i.cash -= levy
                levied += levy
            self.fund_total += levied
            self.fund_shortfall += self.fund_outlay - levied
        newly = []
        for ins in live:
            earned = sum(p.premium / P.POLICY_TERM for p in self.policies.values()
                         if p.active and p.insurer == ins.name and p.start <= q < p.start + P.POLICY_TERM)
            ins.earned_total += earned
            if ins.cash > 0:
                ins.cash += ins.cash * P.INVEST_RATE
            act = actions.get(ins.name, {})
            if act.get("ibnr") is not None:
                ins.ibnr = max(0.0, float(act["ibnr"]))
            upr = self._upr(ins.name) * (1 - P.EXPENSE)   # net of deferred acquisition cost
            booked = self._case_reserve(ins.name) + ins.ibnr
            ins.reported_eq = ins.cash - upr - booked
            npw4 = self.npw4(ins)
            div = float(act.get("dividend") or 0.0)
            if div > 0:
                allow = max(0.0, min(div, ins.reported_eq - 2 * P.K_REG * npw4, ins.cash))
                ins.cash -= allow
                ins.div_paid += allow
                ins.reported_eq -= allow
            true_unpaid = self._true_unpaid(ins.name)
            audited_res = max(booked, P.AUDIT_FLOOR * true_unpaid)
            ins.audited_eq = ins.cash - upr - audited_res
            ins.restricted = ins.audited_eq < P.K_REG * npw4
            ins.rating = float(np.clip(ins.audited_eq / max(npw4, 8.0) / P.RATING_FULL, 0.0, 1.0))
            if ins.audited_eq < 0:
                newly.append(ins)
        for ins in newly:
            ins.insolvent = True
            ins.insolvent_q = q
            for p in self.policies.values():
                if p.active and p.insurer == ins.name:
                    p.active = False
                    self.next_review[p.client] = q + 1
                    self.last_ins[p.client] = ins.name
                    self.orphans.add(p.client)
        for ins in self.ins.values():
            ins.history.append(dict(q=q, cash=ins.cash, reported_eq=ins.reported_eq, audited_eq=ins.audited_eq,
                                    true_eq=self.true_equity(ins.name) if not ins.insolvent else 0.0,
                                    npw=ins.npw[q], paid=ins.paid_q, rating=ins.rating, rep=ins.rep,
                                    insolvent=ins.insolvent, ibnr=ins.ibnr,
                                    in_force=sum(1 for p in self.policies.values() if p.active and p.insurer == ins.name)))
        self.market_hist.append(dict(q=q, rol=self.rol_index_prev, rol_by_sector=dict(self.rol_prev),
                                     fund_outlay=self.fund_outlay, news=list(self.news_log[q]),
                                     n_applicants=len(self.applicants),
                                     adequacy=(self.adq[0] / self.adq[1] if self.adq[1] > 0 else None),
                                     n_bound=len(bound)))
        # tell each bot what it can learn at quarter end
        for ins in self.ins.values():
            if not ins.insolvent:
                ins.bot.on_quarter_end(q)

    # --------------------------------------------------------------------- run
    def run(self) -> dict:
        for _ in range(P.Q):
            views = self.begin_quarter()
            actions = {n: self.ins[n].bot.act(v) for n, v in views.items()}
            self.resolve(actions)
        return self.result()

    def result(self) -> dict:
        out = {}
        for n, ins in self.ins.items():
            te = 0.0 if ins.insolvent else max(self.true_equity(n), 0.0)
            v = te + (0.0 if ins.insolvent else ins.div_paid)
            out[n] = dict(insolvent=ins.insolvent, insolvent_q=ins.insolvent_q, true_equity=te,
                          dividends=ins.div_paid, value=v,
                          score=math.log(max(v, 1.0) / P.START_EQUITY),
                          combined_ratio=((ins.paid_total + ins.expense_total) / ins.earned_total
                                          if ins.earned_total > 0 else float("nan")),
                          premium_written=sum(ins.npw), reins_cost=ins.reins_cost_total, history=ins.history)
        return dict(seed=self.seed, env_version=P.ENV_VERSION, insurers=out, market=self.market_hist,
                    events=[(e.q, e.kind, e.headline) for e in self.world.events], fund_total=self.fund_total, fund_shortfall=self.fund_shortfall)
