"""Is AI-assisted bio risk insurable? Explicit tests, run on the bio peril alone, and what it would take to pass each.

    python -m catmodel.insurability          # rewrites the generated part of results/bio_insurability.md

The tests follow Berliner's insurability criteria, made quantitative where the model allows. Thresholds are ours and
are stated in each row; argue with them. Wrong-way risk needs two extra judgements (how far the mutual's assets fall,
and how much of a call members can pay, in a year with a bio catastrophe); they are set below.
"""
import os
from dataclasses import replace

import numpy as np

from .capital_s2 import solvency2
from .model import load, simulate
from .pricing import build_stack
from .reserves import reserves

PERIL = "bio_misuse"
ASSET_DRAWDOWN = 0.3       # fall in the mutual's invested capital in a bio-catastrophe year (COVID: investment losses ~ underwriting losses)
CALL_RECOVERY = 0.5        # share of a call members can actually pay in that year
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "bio_insurability.md")
START, END = "<!-- generated:start -->", "<!-- generated:end -->"


def bio_only(level="central", **changes):
    s = load(level)
    s = replace(s, perils=tuple(p for p in s.perils if p.name == PERIL), **changes)
    return s


def peril(s):
    return s.perils[0]


def evaluate(s, n_years=200_000, seed=0) -> dict:
    """The quantities the insurability tests need, for bio-only settings s."""
    p = peril(s)
    y = simulate(s, n_years, seed)
    st = build_stack(s, y)
    gross = float(st.claims.mean())
    s2 = solvency2(s, st, reserves(s, y, float(st.net.mean()) / gross if gross else 1.0))
    event = y.harm > 0
    resources = st.premium * (1 - s.expense_ratio) + s.paid_in_capital
    stressed = st.premium * (1 - s.expense_ratio) + s.paid_in_capital * (1 - ASSET_DRAWDOWN)
    call_cap = s.members * s.callable_per_member
    unpaid_plain = np.maximum(st.net - resources - call_cap, 0.0)
    unpaid_wrong_way = np.maximum(st.net - stressed - CALL_RECOVERY * call_cap, 0.0)
    unpaid_wrong_way = np.where(event, unpaid_wrong_way, unpaid_plain)
    return dict(
        el=gross, harm=float(y.harm.mean()), liable=float(y.liable.mean()),
        share_of_harm=gross / float(y.harm.mean()) if y.harm.mean() else 0.0,
        share_of_liability=gross / float(y.liable.mean()) if y.liable.mean() else 0.0,
        premium_per_member=st.premium / s.members, premium_share_revenue=st.premium / s.members / s.revenue,
        scr=s2["scr"], solvency_ratio=s2["solvency_ratio"],
        p_unpaid=float((unpaid_plain > 0).mean()), p_unpaid_wrong_way=float((unpaid_wrong_way > 0).mean()),
        var995=float(np.quantile(st.net, 0.995)), tvar995=float(st.net[st.net >= np.quantile(st.net, 0.995)].mean()),
        p_any_claim=float((st.claims > 0).mean()), mean_per_event=p.severity.mean())


def limit_for_liability_share(s, share: float) -> float:
    """Per-event limit at which the mutual would cover `share` of members' expected liability (one member, no splitting)."""
    p = peril(s)
    a = p.liable_share
    full = p.severity.mean() * a
    lo, hi = 0.0, p.severity.cap * a
    for _ in range(80):
        mid = (lo + hi) / 2
        if a * p.severity.layer(0.0, mid / a) < share * full:
            lo = mid
        else:
            hi = mid
    return hi


def criteria() -> list:
    """Rows of (criterion, test, result, verdict, what would make it pass)."""
    s = bio_only()
    p = peril(s)
    c = evaluate(s)
    opt, pess = evaluate(bio_only("optimistic")), evaluate(bio_only("pessimistic"))
    sev = p.severity
    caps = [1e4, 1e5, 1e6]
    means = [replace(sev, cap=k).mean() for k in caps]
    alpha_thin = replace(sev, alpha=1.4)
    thin_means = [replace(alpha_thin, cap=k).mean() for k in caps]
    l50 = limit_for_liability_share(s, 0.5)
    capacity = s.paid_in_capital + s.members * s.callable_per_member
    strict = evaluate(replace(s, perils=(replace(p, attribution=0.2),)))
    fmt = lambda x: f"${x:,.0f}bn" if x >= 10 else (f"${x:,.2f}bn" if x >= 1 else f"${x * 1000:,.1f}m")
    big = dict(per_event_limit=10.0, annual_aggregate=20.0, paid_in_capital=20.0, callable_per_member=10.0)
    ww = evaluate(bio_only(**big))
    rows = [
        ("1. Finite expected loss", "Tail index above 1, so the mean exists without an arbitrary cap",
         f"α = {sev.alpha:g}. Mean harm per event is {', '.join(fmt(m) for m in means)} with the cap at "
         f"$10tn, $100tn, $1,000tn: it grows with the cap. At α = 1.4: {', '.join(fmt(m) for m in thin_means)}.",
         "Fail" if sev.alpha <= 1 else "Pass",
         "Nothing an insurer controls. Either the lognormal reading of pandemic data is right (Corral), or the "
         "risk is only ever covered as a capped slice."),
        ("2. A capped slice has a finite price", "Expected annual claims on $1bn per member are finite and stable",
         f"Expected claims {fmt(c['el'])} a year; mean ground-up harm {fmt(c['harm'])} a year.",
         "Pass", "Already passes: limits turn a tail problem into a frequency problem."),
        ("3. The price can be estimated", "Expected claims vary by less than 10× across the sources' range",
         f"{fmt(opt['el'])} (optimistic) to {fmt(pess['el'])} (pessimistic): {pess['el'] / opt['el']:.0f}×.",
         "Fail" if pess["el"] / opt["el"] > 10 else "Pass",
         "Narrow the rate: better uplift studies and safeguard evidence (FRI's experts' interquartile range spans "
         "0.01% to 2%). The tail index barely matters once limits bind."),
        ("4. Compensation is meaningful", "The mutual pays at least 10% of the harm attributed to labs",
         f"It pays {c['share_of_liability']:.1%} of attributed liability and {c['share_of_harm']:.3%} of all harm. "
         f"Covering half the attributed liability needs a per-event limit of about {fmt(l50)}.",
         "Fail" if c["share_of_liability"] < 0.10 else "Pass",
         "Limits in the hundreds of billions, which only a government layer could provide (Price-Anderson's whole "
         "scheme is about $15.5bn)."),
        ("5. Premium is affordable", "Premium per member below 2% of revenue",
         f"{fmt(c['premium_per_member'])} per member, {c['premium_share_revenue']:.2%} of a ${s.revenue:g}bn revenue "
         f"(pessimistic: {pess['premium_share_revenue']:.1%}).",
         "Pass" if c["premium_share_revenue"] < 0.02 else "Fail",
         "Passes at the central case because the slice is small; fails if revenue is low and the rate high."),
        ("6. Capital is adequate", "Solvency II ratio at least 100% with paid-in capital and member calls",
         f"SCR {fmt(c['scr'])} against {fmt(s.paid_in_capital)} paid in: ratio {c['solvency_ratio']:.0%}. But a claim "
         f"happens in {c['p_any_claim']:.2%} of years, right at the 1-in-200 standard, so the 99.5% VaR is either "
         f"about zero or about the full limit depending on the rate; TVaR 99.5% is {fmt(c['tvar995'])}.",
         "Pass" if c["solvency_ratio"] >= 1 else "Fail",
         "Passes while limits stay at $1bn per member; the SCR scales with the limits, not the tail. A tail "
         "measure (TVaR, as the Swiss Solvency Test uses) avoids the knife edge."),
        ("7. Losses are not wrong-way", "The chance claims go unpaid does not rise when assets and members are hit too",
         f"With $10bn per member, $20bn paid in and $10bn callable from each member: unpaid in {ww['p_unpaid']:.3%} "
         f"of years, {ww['p_unpaid_wrong_way']:.3%} if invested capital falls {ASSET_DRAWDOWN:.0%} and members can pay "
         f"only {CALL_RECOVERY:.0%} of a call in a catastrophe year. (At $1bn per member claims cannot outrun capital.)",
         "Fail" if ww["p_unpaid_wrong_way"] > 1.5 * ww["p_unpaid"] + 1e-6 else "Pass",
         "Hold capital in assets that don't fall in a pandemic, and get callable capital from parties that "
         "aren't the members (reinsurers, cat bond investors, government)."),
        ("8. Liability is legally defined", "Attribution is set by law, not a coin toss between legal theories",
         f"Labs' expected insurable liability is {fmt(c['liable'])} a year if courts treat misuse as a superseding "
         f"cause (2% attributed) and {fmt(strict['liable'])} under a strict-liability statute (20%): "
         f"{strict['liable'] / c['liable']:.0f}×. The mutual's claims barely move ({fmt(c['el'])} against "
         f"{fmt(strict['el'])}) because the $1bn limit binds either way; the difference lands on the labs.",
         "Fail", "Legislation: either strict liability with a cap (the nuclear model) or a statutory exclusion."),
        ("9. The insured cannot trigger the loss", "Moral hazard is controllable by the insurer",
         "Not modelled. The mutual's conditions (evaluations, safeguards, testing periods) are the control; FRI's "
         "experts expect safeguards to cut AI-enabled bio risk by about two thirds.",
         "Plausible", "This is the AIUC thesis: the case for a mutual rather than a premium."),
    ]
    return rows


def grid() -> list:
    """Bio-only sensitivity: tail index × attribution × per-event limit."""
    out = []
    for alpha in (0.6, 0.7, 1.0, 1.4, 2.0):
        for att in (0.005, 0.02, 0.2):
            for limit in (1.0, 10.0, 100.0):
                base = bio_only(per_event_limit=limit, annual_aggregate=2 * limit)
                p = peril(base)
                s = replace(base, perils=(replace(p, attribution=att, severity=replace(p.severity, alpha=alpha)),))
                e = evaluate(s, 200_000, 1)
                out.append(dict(alpha=alpha, attribution=att, limit=limit, **e))
    return out


def markdown() -> str:
    lines = [START, "", "## Tests (bio peril alone, central parameters)", "",
             "| Criterion | Test | Result | Verdict | What would make it pass |", "|---|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | **{d}** | {e} |" for a, b, c, d, e in criteria()]
    lines += ["", "## Sensitivity", "",
              "Bio peril alone at the central rate (0.5% a year), five members with $10bn revenue each. The premium "
              "loads the 99.5% VaR, so where that VaR is zero the premium is just expected claims plus expenses.", "",
              "| α | Attribution | Limit per member ($bn) | Expected claims ($bn) | Share of attributed liability paid "
              "| Premium per member, % of revenue | VaR 99.5% ($bn) | TVaR 99.5% ($bn) |",
              "|---|---|---|---|---|---|---|---|"]
    for g in grid():
        lines.append(f"| {g['alpha']:g} | {g['attribution']:.1%} | {g['limit']:g} | {g['el']:.3f} | "
                     f"{g['share_of_liability']:.1%} | {g['premium_share_revenue']:.2%} | {g['var995']:.2f} | "
                     f"{g['tvar995']:.2f} |")
    lines += ["", END]
    return "\n".join(lines)


def write(path=OUT):
    body = markdown()
    if os.path.exists(path):
        text = open(path, encoding="utf-8").read()
        if START in text and END in text:
            body = text[:text.index(START)] + body + text[text.index(END) + len(END):]
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


if __name__ == "__main__":
    print("wrote", write())
