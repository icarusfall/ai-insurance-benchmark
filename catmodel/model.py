"""Perils, settings and the simulation of many years of claims against the mutual.

Each year, each peril produces a Poisson number of events (its rate scaled by a gamma shock shared by the year, so
bad years cluster). An event's ground-up harm comes from the peril's severity; the lab's liability is that harm times
the attribution and insurable shares. Most events are caused by one member; a common-mode event is caused by every
member's models together and the liability is split between them, so their per-member limits stack.
"""
import os
from dataclasses import dataclass, field, replace

import numpy as np
import yaml

from .dist import TruncatedPareto

DEFAULTS = os.path.join(os.path.dirname(__file__), "defaults.yaml")


@dataclass(frozen=True)
class Peril:
    name: str
    rate: float
    severity: TruncatedPareto
    attribution: float
    insurable: float
    common_mode: float = 0.0
    rate_cv: float = 0.0
    payout_lag_years: float = 1.0

    @property
    def liable_share(self) -> float:
        return self.attribution * self.insurable

    def expected_claim(self, per_event_limit: float) -> float:
        """Expected claims per year if limits apply per event and nothing else binds (no aggregates, no splitting)."""
        s = self.liable_share
        return self.rate * s * self.severity.layer(0.0, per_event_limit / s) if s > 0 else 0.0


@dataclass(frozen=True)
class Settings:
    perils: tuple
    members: int = 5
    revenue: float = 10.0
    per_event_limit: float = 1.0
    annual_aggregate: float = 2.0
    paid_in_capital: float = 5.0
    callable_per_member: float = 1.0
    reinsurance_attach: float = 0.0
    reinsurance_limit: float = 0.0
    government_attach: float = 0.0
    government_share: float = 0.0
    expense_ratio: float = 0.10
    cost_of_capital: float = 0.10
    catbond_multiple: float = 10.0
    wang_lambda: float = 0.5
    s2_coc: float = 0.0475
    discount_rate: float = 0.04
    us_premium_factor: float = 0.3
    us_reserve_factor: float = 0.3

    def with_peril(self, name: str, **changes) -> "Settings":
        return replace(self, perils=tuple(replace(p, **changes) if p.name == name else p for p in self.perils))


LEVELS = ("optimistic", "central", "pessimistic")


def _pick(spec, level: str):
    """A parameter's value at a level. Pessimistic means the high end unless the spec says `worse: low`
    (a larger tail index or a larger revenue makes things better, not worse)."""
    if not isinstance(spec, dict):
        return spec
    if level == "central":
        return spec["central"]
    bad = spec.get("worse", "high")
    end = bad if level == "pessimistic" else ("low" if bad == "high" else "high")
    return spec.get(end, spec["central"])


def load(level: str = "central", path: str = DEFAULTS) -> Settings:
    """Settings from the defaults file, every ranged parameter at the optimistic, central or pessimistic end."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}")
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    perils = []
    for name, p in d["perils"].items():
        g = lambda k, default=None: _pick(p[k], level) if k in p else default
        perils.append(Peril(name=name, rate=g("rate"), severity=TruncatedPareto(g("xm"), g("alpha"), g("cap")),
                            attribution=g("attribution"), insurable=g("insurable"), common_mode=g("common_mode", 0.0),
                            rate_cv=g("rate_cv", 0.0), payout_lag_years=g("payout_lag_years", 1.0)))
    flat = {}
    for section in ("structure", "pricing", "capital"):
        flat.update({k: _pick(v, level) for k, v in d[section].items()})
    return Settings(perils=tuple(perils), members=int(_pick(d["members"]["count"], level)),
                    revenue=_pick(d["members"]["revenue"], level), **flat)


@dataclass
class Years:
    """Simulated years. Arrays have one entry per year; by_peril holds each peril's claims to the mutual."""
    harm: np.ndarray              # ground-up harm in the world
    liable: np.ndarray            # insurable liability of members, before any limit
    claims: np.ndarray            # what the mutual owes members after per-event limits and annual aggregates
    by_peril: dict = field(default_factory=dict)
    n: int = 0


def simulate(s: Settings, n_years: int = 200_000, seed: int = 0) -> Years:
    rng = np.random.default_rng(seed)
    m, L, A = s.members, s.per_event_limit, s.annual_aggregate
    harm, liable = np.zeros(n_years), np.zeros(n_years)
    per_member = np.zeros(n_years * m)        # each member's limited claims, year-major
    by_peril_raw = {}
    for p in s.perils:
        shock = rng.gamma(1 / p.rate_cv ** 2, p.rate_cv ** 2, n_years) if p.rate_cv > 0 else np.ones(n_years)
        counts = rng.poisson(p.rate * shock)
        year = np.repeat(np.arange(n_years), counts)
        x = p.severity.sample(rng, len(year))
        lia = x * p.liable_share
        np.add.at(harm, year, x)
        np.add.at(liable, year, lia)
        joint = rng.random(len(year)) < p.common_mode
        pc = np.zeros(n_years * m)
        solo_member = rng.integers(0, m, len(year))
        sel = ~joint
        np.add.at(pc, year[sel] * m + solo_member[sel], np.minimum(lia[sel], L))
        if joint.any():                          # liability split evenly; each share meets that member's limit
            share = np.minimum(lia[joint] / m, L)
            for j in range(m):
                np.add.at(pc, year[joint] * m + j, share)
        by_peril_raw[p.name] = pc
        per_member += pc
    capped = np.minimum(per_member, A)
    # allocate each member's annual aggregate cut back to perils pro rata
    scale = np.divide(capped, per_member, out=np.ones_like(per_member), where=per_member > 0)
    claims = capped.reshape(n_years, m).sum(axis=1)
    by_peril = {k: (v * scale).reshape(n_years, m).sum(axis=1) for k, v in by_peril_raw.items()}
    return Years(harm=harm, liable=liable, claims=claims, by_peril=by_peril, n=n_years)
