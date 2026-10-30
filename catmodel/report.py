"""Run the toy model and print a one-page report.

    python -m catmodel.report                         # central defaults
    python -m catmodel.report --level pessimistic     # every ranged parameter at its bad end
    python -m catmodel.report --set bio_misuse.alpha=1.4 --set paid_in_capital=10 --bond 2,4
"""
import argparse

import numpy as np

from .capital_s2 import solvency2
from .capital_us import us
from .model import load, simulate
from .pricing import build_stack, catbond, tvar, var
from .reserves import reserves


def run(s, n_years=200_000, seed=0, bond=None):
    y = simulate(s, n_years, seed)
    st = build_stack(s, y)
    gross = float(st.claims.mean())
    res = reserves(s, y, float(st.net.mean()) / gross if gross else 1.0)
    out = dict(settings=s, years=y, stack=st, s2=solvency2(s, st, res), us=us(s, st, res))
    if bond:
        out["bond"] = catbond(st.claims, bond[0], bond[1], s.catbond_multiple, s.wang_lambda)
    return out


def _apply(s, assignments):
    from dataclasses import replace
    for a in assignments:
        key, val = a.split("=")
        if "." in key:
            peril, field = key.split(".")
            if field in ("xm", "alpha", "cap"):
                p = next(p for p in s.perils if p.name == peril)
                sev = replace(p.severity, **{field: float(val)})
                s = s.with_peril(peril, severity=sev)
            else:
                s = s.with_peril(peril, **{field: float(val)})
        else:
            s = replace(s, **{key: type(getattr(s, key))(float(val))})
    return s


def show(r):
    s, y, st, s2, u = r["settings"], r["years"], r["stack"], r["s2"], r["us"]
    m = s.members
    print(f"{y.n:,} simulated years, {m} members, ${s.per_event_limit:g}bn per event and ${s.annual_aggregate:g}bn a year each")
    print("\nExpected per year ($bn)       harm in world   member liability   mutual pays")
    for p in s.perils:
        harm = p.severity.mean() * p.rate
        print(f"  {p.name:26} {harm:15.3f} {harm * p.liable_share:18.4f} {float(y.by_peril[p.name].mean()):13.4f}")
    print(f"  {'all':26} {float(y.harm.mean()):15.3f} {float(y.liable.mean()):18.4f} {float(st.claims.mean()):13.4f}")
    print(f"  share of expected harm the mutual pays: {float(st.claims.mean()) / max(float(y.harm.mean()), 1e-12):.2%}")
    print("\nMutual's annual claims ($bn)   mean    VaR 99%  VaR 99.5%  VaR 99.6%  TVaR 99.5%  max")
    for name, x in (("gross", st.claims), ("net of layers", st.net)):
        print(f"  {name:28} {x.mean():6.3f} {var(x, .99):9.3f} {var(x, .995):10.3f} {var(x, .996):10.3f} {tvar(x, .995):11.3f} {x.max():6.2f}")
    print(f"\nPremium: ${st.premium:.3f}bn for the mutual, ${st.premium / m * 1000:,.0f}m per member "
          f"({st.premium / m / s.revenue:.2%} of a ${s.revenue:g}bn revenue)")
    print(f"  = (expected net loss {st.net.mean():.3f} + reinsurance {st.reinsurance_cost:.3f} "
          f"+ {s.cost_of_capital:.0%} x SCR {s2['scr']:.3f}) / (1 - {s.expense_ratio:.0%} expenses)")
    print(f"Calls on members in {float((st.calls > 0).mean()):.2%} of years; claims left unpaid in {float((st.unpaid > 0).mean()):.3%} "
          f"(mean unpaid when it happens ${float(st.unpaid[st.unpaid > 0].mean()) if (st.unpaid > 0).any() else 0:.2f}bn)")
    print(f"\nSolvency II: SCR {s2['scr']:.3f}  MCR {s2['mcr']:.3f}  best estimate {s2['best_estimate']:.3f}  "
          f"risk margin {s2['risk_margin']:.4f}")
    print(f"  own funds: tier 1 {s2['tier1']:.2f} + ancillary tier 2 {s2['tier2_ancillary']:.2f} -> eligible {s2['eligible_own_funds_scr']:.2f}; "
          f"SCR ratio {s2['solvency_ratio']:.0%}, MCR ratio {s2['mcr_ratio']:.0%}")
    print(f"US ({s.us_line}): RBC {u['rbc']:.3f} (premium {u['r_premium']:.3f}, reserve {u['r_reserve']:.3f}), ACL {u['acl']:.3f}; "
          f"RBC ratio {u['rbc_ratio']:.0%} ({u['action_level']}) as written")
    print(f"  with the 1-in-100 AI loss {u['r_cat']:.3f} charged like Rcat: ACL {u['acl_with_cat']:.3f}; "
          f"RBC ratio {u['rbc_ratio_with_cat']:.0%} ({u['action_level_with_cat']})")
    print(f"  statutory reserves {u['statutory_reserves']:.3f}; capital for a 99.6% year {u['capital_for_996']:.3f} "
          f"(covered {u['rating_cover']:.1f}x)")
    if "bond" in r:
        b = r["bond"]
        print(f"\nCat bond on the mutual's claims, ${b['attach']:g}-{b['exhaust']:g}bn: attach {b['prob_attach']:.2%}, "
              f"exhaust {b['prob_exhaust']:.2%}, expected loss {b['expected_loss']:.2%}")
        print(f"  spread: {b['spread_multiple']:.2%} ({s.catbond_multiple:g}x EL), Lane {b['spread_lane']:.2%}, "
              f"Wang (lambda {s.wang_lambda:g}) {b['spread_wang']:.2%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="central", choices=["optimistic", "central", "pessimistic"])
    ap.add_argument("--years", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--set", action="append", default=[], help="override: name=value or peril.field=value")
    ap.add_argument("--bond", help="cat bond layer on the mutual's annual claims: attach,exhaust in $bn")
    a = ap.parse_args()
    s = _apply(load(a.level), a.set)
    bond = tuple(float(v) for v in a.bond.split(",")) if a.bond else None
    show(run(s, a.years, a.seed, bond))


if __name__ == "__main__":
    np.set_printoptions(suppress=True)
    main()
