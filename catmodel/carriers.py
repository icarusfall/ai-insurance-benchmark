"""Who carries the risk: the same simulated losses, carried by a mutual, captives, a diversified insurer, the mutual
with reinsurance above it, or the mutual with a government backstop.

    python -m catmodel.carriers

Each carrier in defaults.yaml `carriers` changes a few settings from the central mutual. Every run uses the same
simulated years, so the differences are the structure's, not simulation noise.
"""
from dataclasses import replace

import yaml

from .model import DEFAULTS, load
from .report import run
from .sensitivity import N_YEARS, SEED


def _defaults(path: str = DEFAULTS) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def compare(path: str = DEFAULTS) -> list:
    base = load(path=path)
    out = []
    for c in _defaults(path)["carriers"]:
        s = replace(base, **c["changes"])
        r = run(s, N_YEARS, seed=SEED)
        st, y = r["stack"], r["years"]
        claims = float(st.claims.mean())
        per_lab = st.premium / s.members
        out.append(dict(key=c["key"], premium_per_lab=per_lab, premium_share=per_lab / s.revenue,
                        share_paid=claims / float(y.harm.mean()), scr=r["s2"]["scr"],
                        solvency_ratio=r["s2"]["solvency_ratio"], capital_per_lab=s.paid_in_capital / s.members,
                        carried=dict(own=float(st.net.mean()) / claims, reinsurer=float(st.reinsured.mean()) / claims,
                                     government=float(st.government.mean()) / claims),
                        p_unpaid=float((st.unpaid > 0).mean())))
    return out


def summary(path: str = DEFAULTS) -> dict:
    """What the site shows that it does not recompute itself."""
    return dict(carriers=compare(path))


def main():
    labels = {c["key"]: c["label"] for c in _defaults()["carriers"]}
    for r in compare():
        c = r["carried"]
        print(f"{labels[r['key']][:42]:42} premium per lab ${r['premium_per_lab'] * 1000:4.0f}m ({r['premium_share']:.2%} of revenue), "
              f"SCR {r['scr']:.2f}, Solvency II {r['solvency_ratio']:.0%}; expected claims kept {c['own']:.0%}, "
              f"reinsurer {c['reinsurer']:.0%}, government {c['government']:.0%}")


if __name__ == "__main__":
    main()
