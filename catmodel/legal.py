"""Who pays: a peril's attribution built up from the law, and what changing the law would do to the premium.

    python -m catmodel.legal

attribution = liable x recoverable x (joint + (1 - joint) x fault_share). A claim must survive duty and causation;
only part of the loss can be claimed at all (the economic loss rule); and of that the lab pays everything where
liability is joint and several (the attacker never pays), or only its own share of fault where it is several.
The chains live in defaults.yaml `legal.attribution`; each peril's `attribution` there is the chain at each level.
"""
import yaml

from .model import DEFAULTS, LEVELS, _pick, load
from . import sensitivity


def _defaults(path: str = DEFAULTS) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def chain(d: dict, peril: str, level: str = "central", overrides: dict | None = None) -> dict:
    """Each link's value at a level (or overridden), and the attribution they give."""
    links = {l["key"]: (overrides or {}).get(l["key"], _pick(l, level)) for l in d["legal"]["attribution"][peril]}
    pays = links["joint"] + (1 - links["joint"]) * links["fault_share"]
    return dict(links=links, pays=pays, attribution=links["liable"] * links["recoverable"] * pays)


def attributions(level: str = "central", path: str = DEFAULTS) -> dict:
    d = _defaults(path)
    return {p: chain(d, p, level)["attribution"] for p in d["legal"]["attribution"]}


def scenarios(path: str = DEFAULTS) -> list:
    """Each scenario's attribution and what it does to the premium, everything else at the central settings."""
    d, base = _defaults(path), load(path=path)
    out = []
    for sc in d["legal"]["scenarios"]:
        s, att = base, {}
        for peril in d["legal"]["attribution"]:
            att[peril] = chain(d, peril, "central", sc["changes"].get(peril))["attribution"]
            s = s.with_peril(peril, attribution=att[peril])
        out.append(dict(key=sc["key"], label=sc["label"], attribution=att, **sensitivity.metrics(s)))
    return out


def summary(path: str = DEFAULTS) -> dict:
    """What the site shows that it does not recompute itself."""
    return dict(scenarios=scenarios(path))


def main():
    d = _defaults()
    for peril in d["legal"]["attribution"]:
        print(peril)
        for level in LEVELS:
            c = chain(d, peril, level)
            links = "  ".join(f"{k} {v:.0%}" for k, v in c["links"].items())
            print(f"  {level:12} {links}  -> pays {c['pays']:.0%} of the claimable loss, attribution {c['attribution']:.2%}"
                  f" (defaults.yaml: {_pick(d['perils'][peril]['attribution'], level):.2%})")
    print("\nscenarios (central otherwise)")
    for r in scenarios():
        att = ", ".join(f"{k} {v:.2%}" for k, v in r["attribution"].items())
        print(f"  {r['label'][:40]:40} {att:24} premium {r['premium_share']:.3%} of revenue, pays {r['share_paid']:.3%} of harm,"
              f" SII {r['solvency_ratio']:.0%}")


if __name__ == "__main__":
    main()
