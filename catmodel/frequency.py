"""How often each peril's events happen, estimated three ways.

    python -m catmodel.frequency                      # all three methods side by side
    python -m catmodel.frequency --level pessimistic

- expert: each peril's `rate` in defaults.yaml, set from expert forecasts and parallels with other industries.
- actuarial: only the observed record. n AI-attributable events at the peril's threshold in T years of exposure give a
  Poisson rate. With a Jeffreys prior the posterior is Gamma(n + 1/2, T): mean (n + 1/2) / T. With no events in a few
  years that mean is high and its interval wide. History this short cannot tell 1-in-10 from 1-in-1,000, which is the
  case for a causal model.
- causal: the AIUC essay's catastrophe-model approach. The rate is a chain of links, a count per year times
  conditional probabilities, each with its own range and sources: rate = count x p1 x p2 x ...

Severity, attribution and everything downstream are the same under all three; only the rates change.
"""
import argparse
import math
from dataclasses import replace
from datetime import date

import yaml

from .model import DEFAULTS, _pick, load

METHODS = ("expert", "actuarial", "causal")


def _defaults(path: str = DEFAULTS) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _now(d: dict) -> date:
    return date.fromisoformat(str(d["capability"]["now"]["central"]))


def actuarial(d: dict, peril: str) -> dict:
    a = d["frequency"]["actuarial"][peril]
    years = (_now(d) - date.fromisoformat(str(a["since"]))).days / 365.25
    shape = a["events"] + 0.5
    return dict(events=a["events"], years=years, rate=shape / years,
                low=gamma_quantile(0.05, shape) / years, high=gamma_quantile(0.95, shape) / years)


def chain(d: dict, peril: str, level: str = "central", overrides: dict | None = None) -> list:
    """Each link's value at a level (or overridden), and the running product down the chain."""
    out, running = [], 1.0
    for link in d["frequency"]["causal"][peril]:
        v = (overrides or {}).get(link["key"], _pick(link, level))
        running *= v
        out.append(dict(key=link["key"], label=link["label"], value=v, running=running))
    return out


def rates(level: str = "central", method: str = "expert", path: str = DEFAULTS) -> dict:
    d = _defaults(path)
    out = {}
    for peril, spec in d["perils"].items():
        if method == "expert":
            out[peril] = _pick(spec["rate"], level)
        elif method == "actuarial":
            out[peril] = actuarial(d, peril)["rate"]
        elif method == "causal":
            out[peril] = chain(d, peril, level)[-1]["running"]
        else:
            raise ValueError(f"method must be one of {METHODS}")
    return out


def with_method(s, method: str, level: str = "central", path: str = DEFAULTS):
    """Settings with every peril's rate replaced by the chosen method's."""
    r = rates(level, method, path)
    return replace(s, perils=tuple(replace(p, rate=r[p.name]) for p in s.perils))


def summary(level: str = "central", path: str = DEFAULTS) -> dict:
    """Everything the site shows that it does not recompute itself: the actuarial intervals."""
    d = _defaults(path)
    return {p: dict(actuarial=actuarial(d, p)) for p in d["perils"]}


# ---- the regularised lower incomplete gamma function and its inverse (no scipy in this repo)
def _gamma_p(a: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x < a + 1:                                   # series
        term = total = 1.0 / a
        n = a
        for _ in range(500):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    b, c, dd = x + 1 - a, 1e300, 1 / (x + 1 - a)    # continued fraction (Lentz)
    h = dd
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        dd = an * dd + b
        dd = 1 / (dd if abs(dd) > 1e-300 else 1e-300)
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        h *= dd * c
        if abs(dd * c - 1) < 1e-15:
            break
    return 1 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gamma_quantile(p: float, shape: float) -> float:
    """x with P(Gamma(shape, 1) <= x) = p, by bisection."""
    lo, hi = 0.0, max(10.0, shape * 10)
    for _ in range(200):
        mid = (lo + hi) / 2
        if _gamma_p(shape, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="central")
    a = ap.parse_args()
    d = _defaults()
    by = {m: rates(a.level, m) for m in METHODS}
    print(f"Events a year at each peril's threshold ({a.level})")
    print(f"  {'peril':16} {'expert':>10} {'actuarial':>10} {'(90% interval)':>22} {'causal':>10}")
    for p in d["perils"]:
        act = actuarial(d, p)
        print(f"  {p:16} {by['expert'][p]:10.4f} {act['rate']:10.4f}   ({act['low']:.4f} to {act['high']:.3f}) {by['causal'][p]:10.4f}"
              f"   [{act['events']} events in {act['years']:.1f} years]")
    for p in d["perils"]:
        print(f"\n  {p} chain:")
        for link in chain(d, p, a.level):
            print(f"    {link['label'][:64]:64} {link['value']:>8g}  -> {link['running']:.4g}")


if __name__ == "__main__":
    main()
