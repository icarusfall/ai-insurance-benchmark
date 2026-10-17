"""Hidden world truth: providers, events, clients and their pre-drawn incident variates.

Everything here is a pure function of the seed. Incidents for a (client, quarter) are
computed from pre-drawn uniforms, so they are identical whichever insurer holds the policy.
"""
import math
from dataclasses import dataclass, field

import numpy as np

from . import loss
from . import params as P
from .rng import stream

SLOTS = 4  # 0-2: base/flaw incidents, 3: catastrophe


@dataclass
class Provider:
    id: int
    name: str
    flaw_rate: float
    quality: float
    litigiousness: float


@dataclass
class Event:
    q: int
    kind: str
    headline: str
    data: dict = field(default_factory=dict)


@dataclass
class Client:
    id: int
    name: str
    arrival_q: int
    sector: str
    size: int
    provider: int
    autonomy: float
    safety: float
    corner: bool
    unk: float
    ps: float
    cov_pref: float
    rating_w: float
    rep_w: float
    perceived: float
    autonomy_obs: float
    safety_obs: float
    provider_stated: bool
    red_flags: list
    text: str
    ideal_limit: float
    default_retention: float
    z_sev: np.ndarray = None
    u_tail: np.ndarray = None
    u_cnt: np.ndarray = None
    u_lag: np.ndarray = None
    u_murk: np.ndarray = None
    z_murkobs: np.ndarray = None
    u_misuse: np.ndarray = None
    u_cat: np.ndarray = None
    z_cat: np.ndarray = None
    u_court: np.ndarray = None
    u_sue: np.ndarray = None


def poisson_inv(u: float, lam: float, cap: int = 3) -> int:
    p = math.exp(-lam)
    c = p
    k = 0
    while u > c and k < cap:
        k += 1
        p *= lam / k
        c += p
    return k


class World:
    def __init__(self, seed: int):
        self.seed = seed
        self.providers = self._make_providers()
        self.events = self._make_events()
        self._precompute_exogenous()
        self.clients = self._make_clients()

    # ---------------------------------------------------------------- providers
    def _make_providers(self):
        rng = stream(self.seed, "providers")
        out = []
        for i, name in enumerate(P.PROVIDER_NAMES):
            out.append(Provider(i, name, flaw_rate=float(rng.uniform(0.01, 0.04)),
                                quality=float(math.exp(rng.normal(0, 0.15))),
                                litigiousness=float(rng.uniform(0, 1))))
        return out

    # ------------------------------------------------------------------- events
    def _make_events(self):
        rng = stream(self.seed, "events")
        ev = []
        mandate_done = safe_done = False
        for q in range(4, P.Q):
            if rng.random() < P.CAT_RATE:
                what = rng.choice(["an engineered pathogen traced to AI-assisted design tooling",
                                   "a cascade of autonomous trading agents that erased a Tuesday",
                                   "a synthetic-impersonation incident disrupting a national election",
                                   "an autonomous logistics fleet that interpreted 'priority' liberally"])
                ev.append(Event(q, "cat", f"CATASTROPHE: correlated morbidity occurrence attributed to {what}",
                                dict(hit_prob=float(rng.uniform(0.012, 0.03)),
                                     sev_mult=float(math.exp(rng.normal(0, 0.3))))))
            for p in self.providers:
                if rng.random() < p.flaw_rate:
                    ev.append(Event(q, "flaw", f"{p.name} ships update; customers' agents discover creative "
                                               f"interpretations of their instructions",
                                    dict(provider=p.id, duration=2, mult=float(rng.uniform(3, 6)))))
            if rng.random() < P.RULING_RATE:
                s = str(rng.choice(P.SECTOR_NAMES))
                d = float(rng.uniform(0.08, 0.2)) * (1 if rng.random() < 0.6 else -1)
                who = "deployers strictly liable" if d > 0 else "vendors primarily liable"
                ev.append(Event(q, "ruling", f"Court holds {who} for autonomous {s.replace('_', ' ')} agents",
                                dict(sector=s, delta=d)))
            if not mandate_done and 8 <= q <= 30 and rng.random() < P.MANDATE_RATE:
                mandate_done = True
                ev.append(Event(q, "mandate", "Regulator mandates AI liability cover; demand expected to double",
                                dict(duration=8)))
            if not safe_done and 8 <= q <= 30 and rng.random() < P.SAFE_HARBOUR_RATE:
                safe_done = True
                ev.append(Event(q, "safe_harbour", "Legislature passes AI safe-harbour provisions; claims expected to ease",
                                dict(mult=0.8)))
            if rng.random() < P.FALSE_ALARM_RATE:
                ev.append(Event(q, "false_alarm", "Report warns of imminent AI incident; nothing imminently occurs", {}))
        return ev

    def _precompute_exogenous(self):
        S = len(P.SECTOR_NAMES)
        rng = stream(self.seed, "drift")
        self.drift = np.exp(np.cumsum(rng.normal(0, P.DRIFT_SIGMA, size=(P.Q, S)), axis=0))
        self.prec_shift = np.zeros((P.Q, S))
        self.flawmult = np.ones((P.Q, len(self.providers)))
        self.safe = np.ones(P.Q)
        self.cat_hit = np.zeros(P.Q)
        self.cat_sev = np.ones(P.Q)
        self.arrival_mult = np.ones(P.Q)
        self.outside_pen = np.zeros(P.Q)
        for e in self.events:
            if e.kind == "cat":
                self.cat_hit[e.q] = e.data["hit_prob"]
                self.cat_sev[e.q] = e.data["sev_mult"]
            elif e.kind == "flaw":
                for t in range(e.q, min(P.Q, e.q + e.data["duration"])):
                    self.flawmult[t, e.data["provider"]] = max(self.flawmult[t, e.data["provider"]], e.data["mult"])
            elif e.kind == "ruling":
                self.prec_shift[e.q:, P.SECTOR_IDX[e.data["sector"]]] += e.data["delta"]
            elif e.kind == "mandate":
                self.arrival_mult[e.q:e.q + e.data["duration"]] = 2.0
                self.outside_pen[e.q:] = 3.0
            elif e.kind == "safe_harbour":
                self.safe[e.q:] *= e.data["mult"]

    # ------------------------------------------------------------------ clients
    def _make_clients(self):
        rng = stream(self.seed, "clients")
        sw = np.array([P.SECTORS[s]["weight"] for s in P.SECTOR_NAMES])
        sw = sw / sw.sum()
        arrivals = []
        for i in range(P.INITIAL_CLIENTS):
            arrivals.append(int(rng.integers(0, 4)))
        for q in range(4, P.Q):
            lam = P.ARRIVALS_PER_Q * (1 + P.ARRIVAL_GROWTH * q) * self.arrival_mult[q]
            arrivals += [q] * int(rng.poisson(lam))
        clients = []
        for cid, aq in enumerate(arrivals):
            sector = P.SECTOR_NAMES[int(rng.choice(len(sw), p=sw))]
            size = int(rng.choice(5, p=P.SIZE_WEIGHTS))
            prov = int(rng.choice(6, p=P.PROVIDER_SHARES))
            autonomy = float(rng.beta(2, 2))
            safety = float(np.clip(rng.beta(2, 2) + 0.05 * size, 0, 1))
            corner = bool(rng.random() < 0.12)
            unk = float(math.exp(rng.normal(0, 0.3)))
            ps = float(np.clip(rng.normal(4, 1), 1.5, 7))
            cov_pref = float(np.clip(rng.normal(2, 0.5), 0.5, 4))
            rating_w = float(np.clip(rng.normal(1.5, 0.5), 0, 3))
            rep_w = float(np.clip(rng.normal(1.0, 0.4), 0, 2))
            perceived = float(math.exp(rng.normal(0, 0.3)))
            a_obs = float(np.clip(autonomy + rng.normal(0, 0.2), 0, 1))
            s_obs = float(np.clip(safety + rng.normal(0, 0.25), 0, 1))
            stated = bool(rng.random() < 0.85)
            flags = []
            if corner and rng.random() < 0.5:
                flags.append(str(rng.choice(["recent regulatory inquiry (closed, 'no findings')",
                                             "safety team reportedly reduced in last reorganisation",
                                             "founder describes testing as 'a mindset'"])))
            elif (not corner) and rng.random() < 0.1:
                flags.append("recently hired a Head of Responsible AI (function unclear)")
            ideal = P.IDEAL_LIMIT_PER_SIZE * P.SIZE_MULT[size]
            ret = round(P.RETENTION_PER_SIZE * P.SIZE_MULT[size], 3)
            name = f"{rng.choice(['Nimbus', 'Quokka', 'Verity', 'Lumen', 'Orchid', 'Basalt', 'Tandem', 'Kestrel'])} " \
                   f"{rng.choice(['Health', 'Capital', 'Freight', 'Support', 'Legal', 'Grid', 'Shield', 'Apps'])} #{cid}"
            c = Client(cid, name, aq, sector, size, prov, autonomy, safety, corner, unk, ps, cov_pref, rating_w,
                       rep_w, perceived, a_obs, s_obs, stated, flags, "", ideal, ret)
            c.text = self._dossier_text(c)
            ir = stream(self.seed, f"incidents:{cid}")
            c.z_sev = ir.standard_normal((P.Q, SLOTS))
            c.u_tail = ir.random((P.Q, SLOTS))
            c.u_cnt = ir.random((P.Q, 2))
            c.u_lag = ir.random((P.Q, SLOTS))
            c.u_murk = ir.random((P.Q, SLOTS))
            c.z_murkobs = ir.standard_normal((P.Q, SLOTS))
            c.u_misuse = ir.random((P.Q, SLOTS))
            c.u_cat = ir.random(P.Q)
            c.z_cat = ir.standard_normal(P.Q)
            c.u_court = ir.random((P.Q, SLOTS))
            c.u_sue = ir.random((P.Q, SLOTS))
            clients.append(c)
        return clients

    def _dossier_text(self, c: Client) -> str:
        aut = "fully autonomous" if c.autonomy_obs > 0.7 else "mostly autonomous" if c.autonomy_obs > 0.4 else "human-supervised"
        saf = ("a well-resourced safety function" if c.safety_obs > 0.65
               else "a modest safety function" if c.safety_obs > 0.35 else "no discernible safety function")
        prov = self.providers[c.provider].name if c.provider_stated else "an undisclosed foundation-model vendor"
        flags = (" Notes: " + "; ".join(c.red_flags) + ".") if c.red_flags else ""
        return (f"{c.name}: a {P.SIZE_WORDS[c.size]} {c.sector.replace('_', ' ')} firm deploying {aut} agents "
                f"built on {prov}. It reports {saf}.{flags}")

    # --------------------------------------------------------------- truth rates
    def mods(self, c: Client) -> float:
        return (math.exp(P.B_AUTONOMY * (c.autonomy - 0.5) + P.B_SAFETY * (c.safety - 0.5)
                         + P.B_CORNER * c.corner) * c.unk * self.providers[c.provider].quality)

    def prec_mult(self, q: int, sector: str) -> float:
        return math.exp(1.5 * self.prec_shift[q, P.SECTOR_IDX[sector]])

    def lam_base(self, c: Client, q: int) -> float:
        s = P.SECTORS[c.sector]
        return (s["freq"] / 4 * math.sqrt(P.SIZE_MULT[c.size]) * self.mods(c)
                * self.drift[q, P.SECTOR_IDX[c.sector]] * self.prec_mult(q, c.sector) * self.safe[q])

    def lam_flaw(self, c: Client, q: int) -> float:
        return self.lam_base(c, q) * (self.flawmult[q, c.provider] - 1.0)

    def cat_prob(self, c: Client, q: int) -> float:
        return float(self.cat_hit[q])

    def liability_p(self, q: int, sector: str, murk: float) -> float:
        return float(np.clip(0.95 - 0.7 * murk + self.prec_shift[q, P.SECTOR_IDX[sector]], 0.05, 0.99))

    def expected_quarter_loss(self, c: Client, q: int, limit: float, retention: float) -> float:
        """Oracle expected covered loss next quarter (ignores catastrophes)."""
        lam = self.lam_base(c, q) + self.lam_flaw(c, q)
        return lam * loss.layer_expectation(c.sector, c.size, round(limit, 2), round(retention, 3))

    def expected_quarter_ceded(self, c: Client, q: int, limit: float, retention: float,
                               attach: float, rlimit: float) -> float:
        """Oracle expected quarterly loss to a per-claim XoL layer [attach, attach+rlimit] over the policy."""
        if limit <= attach:
            return 0.0
        lam = self.lam_base(c, q) + self.lam_flaw(c, q)
        return lam * loss.layer_expectation(c.sector, c.size, round(min(rlimit, limit - attach), 0),
                                            round(retention + attach, 2))

    # ----------------------------------------------------------------- incidents
    def incidents(self, c: Client, q: int):
        """Gross incidents for client c in quarter q. Independent of insurer."""
        out = []
        nb = poisson_inv(float(c.u_cnt[q, 0]), self.lam_base(c, q))
        nf = poisson_inv(float(c.u_cnt[q, 1]), self.lam_flaw(c, q))
        slot = 0
        for comp, n in (("base", nb), ("flaw", nf)):
            for _ in range(n):
                if slot >= 3:
                    break
                gross = loss.severity(c.sector, c.size, float(c.z_sev[q, slot]), float(c.u_tail[q, slot]))
                out.append(self._inc(c, q, slot, comp, gross))
                slot += 1
        if c.u_cat[q] < self.cat_prob(c, q):
            gross = c.ideal_limit * math.exp(-2.65 + 0.8 * float(c.z_cat[q])) * float(self.cat_sev[q])
            out.append(self._inc(c, q, 3, "cat", gross))
        return out

    def _inc(self, c, q, slot, comp, gross):
        u_lag = float(c.u_lag[q, slot])
        lag = 1 + int(u_lag ** 1.6 * 8) if comp == "base" else 1 + int(u_lag * 4)
        murk = 0.5 + 0.5 * float(c.u_murk[q, slot]) if comp == "cat" else float(c.u_murk[q, slot]) ** 1.5
        murk_obs = float(np.clip(murk + 0.15 * c.z_murkobs[q, slot], 0, 1))
        return dict(slot=slot, comp=comp, gross=gross, lag=min(lag, 8), murk=murk, murk_obs=murk_obs,
                    misuse=bool(c.u_misuse[q, slot] < P.MISUSE_SHARE),
                    u_court=float(c.u_court[q, slot]), u_sue=float(c.u_sue[q, slot]))
