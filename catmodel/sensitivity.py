"""Which levers move the answer: swing each parameter to its low and high end, everything else central.

    python -m catmodel.sensitivity

Ranged parameters swing to the low and high ends in defaults.yaml. The cover and capital levers have no range, so they
are halved and doubled. Every run uses the same random numbers, so the differences are the parameter's effect, not
simulation noise. One year, no capability growth.
"""
from dataclasses import replace

import yaml

from .model import DEFAULTS, load
from .report import run

N_YEARS, SEED = 60_000, 3
PERIL_FIELDS = {"rate": "how often", "alpha": "tail index", "attribution": "share pinned on the lab",
                "insurable": "share insurable", "common_mode": "all members to blame"}
SHORT = {"bio_misuse": "Bio", "cyber_misuse": "Cyber", "agent_runaway": "Agents"}
SETTINGS = {"revenue": "Members' revenue", "cost_of_capital": "Return required on capital",
            "catbond_multiple": "Reinsurance price"}
SCALED = {"per_event_limit": "Cover per member per event", "annual_aggregate": "Cover per member per year",
          "paid_in_capital": "Paid-in capital", "callable_per_member": "Callable from each member"}
METRICS = ("premium_share", "share_paid", "solvency_ratio")


def metrics(s) -> dict:
    r = run(s, N_YEARS, seed=SEED)
    st, y = r["stack"], r["years"]
    return dict(premium_share=st.premium / s.members / s.revenue, share_paid=float(st.claims.mean()) / float(y.harm.mean()),
                solvency_ratio=r["s2"]["solvency_ratio"])


def _peril(s, name, field, v):
    p = next(p for p in s.perils if p.name == name)
    if field == "alpha":
        return s.with_peril(name, severity=replace(p.severity, alpha=v))
    return s.with_peril(name, **{field: v})


def sweep(path: str = DEFAULTS) -> dict:
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    base = load(path=path)
    rows = []
    for name, spec in d["perils"].items():
        for field, label in PERIL_FIELDS.items():
            v = spec.get(field)
            if isinstance(v, dict) and "low" in v and "high" in v:
                rows.append(dict(key=f"{name}.{field}", label=f"{SHORT.get(name, spec['label'])}: {label}", low_value=v["low"], high_value=v["high"],
                                 low=metrics(_peril(base, name, field, v["low"])), high=metrics(_peril(base, name, field, v["high"]))))
    specs = {**d["pricing"], **d["structure"], "revenue": d["members"]["revenue"]}
    for key, label in SETTINGS.items():
        v = specs[key]
        if isinstance(v, dict) and "low" in v:
            rows.append(dict(key=key, label=label, low_value=v["low"], high_value=v["high"],
                             low=metrics(replace(base, **{key: v["low"]})), high=metrics(replace(base, **{key: v["high"]}))))
    for key, label in SCALED.items():
        lo, hi = getattr(base, key) / 2, getattr(base, key) * 2
        change = lambda x: {key: x, **({"annual_aggregate": max(base.annual_aggregate, x)} if key == "per_event_limit" else {}),
                            **({"per_event_limit": min(base.per_event_limit, x)} if key == "annual_aggregate" else {})}
        rows.append(dict(key=key, label=f"{label} (halved, doubled)", low_value=lo, high_value=hi,
                         low=metrics(replace(base, **change(lo))), high=metrics(replace(base, **change(hi)))))
    b = metrics(base)
    for r in rows:
        r["swing"] = {m: abs(r["high"][m] - r["low"][m]) for m in METRICS}
    return dict(base=b, rows=rows, n_years=N_YEARS)


def main():
    out = sweep()
    b = out["base"]
    print(f"central: premium {b['premium_share']:.3%} of revenue, pays {b['share_paid']:.3%} of harm, SII {b['solvency_ratio']:.0%}")
    for r in sorted(out["rows"], key=lambda r: -r["swing"]["premium_share"]):
        lo, hi = r["low"], r["high"]
        print(f"  {r['label'][:62]:62} {lo['premium_share']:7.3%} .. {hi['premium_share']:7.3%}   "
              f"{lo['share_paid']:6.3%} .. {hi['share_paid']:6.3%}   {lo['solvency_ratio']:5.0%} .. {hi['solvency_ratio']:5.0%}")


if __name__ == "__main__":
    main()
