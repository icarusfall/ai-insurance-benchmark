"""Solvency II view: technical provisions, SCR, MCR and eligible own funds.

Simplifications, all deliberate for a toy:
- SCR is the one-year 99.5% VaR of the mutual's own losses less their mean (premium and catastrophe risk together;
  no separate reserve, market, counterparty or operational modules).
- Risk margin covers run-off only: once the year is over there is no new catastrophe exposure, just reserve risk,
  approximated as 3 x RESERVE_SIGMA x best estimate (roughly a 99.5% lognormal shock), held over the reserves'
  duration and charged at the cost-of-capital rate. RESERVE_SIGMA is the standard formula's general liability
  reserve volatility from memory, still to verify.
- MCR uses a linear formula on best estimate and premium, held inside the 25%-45% of SCR corridor. The liability
  factors below are from memory and still to verify.
- Own funds: paid-in capital is Tier 1. Uncalled member assessments are ancillary Tier 2 (with supervisory
  approval). For the SCR, Tier 1 must be at least half the SCR and Tier 2 and 3 together at most half; ancillary
  own funds do not count towards the MCR.
"""
from .model import Settings
from .pricing import Stack, scr

MCR_ALPHA_BE, MCR_BETA_PREMIUM = 0.103, 0.131      # general liability factors (verify)
RESERVE_SIGMA = 0.11                               # general liability reserve risk volatility (verify)


def solvency2(s: Settings, st: Stack, res: dict) -> dict:
    req = scr(st.net)
    runoff_scr = 3 * RESERVE_SIGMA * res["best_estimate"]
    rm = s.s2_coc * runoff_scr * res["duration"] / (1 + s.discount_rate * res["duration"])
    tp = res["best_estimate"] + rm
    linear = MCR_ALPHA_BE * res["best_estimate"] + MCR_BETA_PREMIUM * st.premium
    mcr = min(max(linear, 0.25 * req), 0.45 * req)
    tier1 = s.paid_in_capital
    tier2_ancillary = s.members * s.callable_per_member
    eligible_scr = tier1 + min(tier2_ancillary, 0.5 * req, tier1)   # tier 2 capped at half the SCR, and by tier 1
    return dict(scr=req, mcr=mcr, best_estimate=res["best_estimate"], risk_margin=rm, technical_provisions=tp,
                tier1=tier1, tier2_ancillary=tier2_ancillary, eligible_own_funds_scr=eligible_scr,
                eligible_own_funds_mcr=tier1, solvency_ratio=eligible_scr / req if req else float("inf"),
                mcr_ratio=tier1 / mcr if mcr else float("inf"), tier1_covers_half_scr=tier1 >= 0.5 * req)
