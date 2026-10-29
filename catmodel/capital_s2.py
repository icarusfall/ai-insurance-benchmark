"""Solvency II view: technical provisions, SCR, MCR and eligible own funds.

Simplifications, all deliberate for a toy:
- SCR is the one-year 99.5% VaR of the mutual's own losses less their mean (premium and catastrophe risk together;
  no separate reserve, market, counterparty or operational modules).
- Risk margin covers run-off only: once the year is over there is no new catastrophe exposure, just reserve risk,
  charged as the standard formula does, 3 x RESERVE_SIGMA x best estimate (Delegated Regulation Art. 115), held
  over the reserves' duration and charged at the cost-of-capital rate. RESERVE_SIGMA is the general liability
  reserve risk standard deviation in Annex II.
- MCR uses the linear formula on best estimate and premium with the general liability factors in Annex XIX
  (Art. 250), held inside the 25%-45% of SCR corridor (Directive Art. 129(3)). The absolute euro floor is ignored:
  it is a few million euros against billions here.
- Own funds: paid-in capital is Tier 1. Uncalled member contributions callable on demand are ancillary Tier 2
  (Art. 74(b), with supervisory approval). For the SCR, Tier 1 must be at least half the SCR and Tier 2 and 3
  together at most half (Art. 82(1)); the MCR is covered by basic own funds only, so ancillary items do not count.
- Sources: registry entries solvency2_premium_reserve_sigma, solvency2_mcr_linear, solvency2_own_fund_tiers.
"""
from .model import Settings
from .pricing import Stack, scr

MCR_ALPHA_BE, MCR_BETA_PREMIUM = 0.103, 0.131      # Annex XIX, segment 8: general liability
RESERVE_SIGMA = 0.11                               # Annex II, segment 5: general liability reserve risk


def solvency2(s: Settings, st: Stack, res: dict) -> dict:
    req = scr(st.net)
    runoff_scr = 3 * RESERVE_SIGMA * res["best_estimate"]
    rm = s.s2_coc * runoff_scr * res["duration"] / (1 + s.discount_rate * res["duration"])
    tp = res["best_estimate"] + rm
    linear = MCR_ALPHA_BE * res["best_estimate"] + MCR_BETA_PREMIUM * st.premium
    mcr = min(max(linear, 0.25 * req), 0.45 * req)
    tier1 = s.paid_in_capital
    tier2_ancillary = s.members * s.callable_per_member
    eligible_scr = tier1 + min(tier2_ancillary, 0.5 * req)          # Art. 82(1)(c): tier 2 at most half the SCR
    return dict(scr=req, mcr=mcr, best_estimate=res["best_estimate"], risk_margin=rm, technical_provisions=tp,
                tier1=tier1, tier2_ancillary=tier2_ancillary, eligible_own_funds_scr=eligible_scr,
                eligible_own_funds_mcr=tier1, solvency_ratio=eligible_scr / req if req else float("inf"),
                mcr_ratio=tier1 / mcr if mcr else float("inf"), tier1_covers_half_scr=tier1 >= 0.5 * req)
