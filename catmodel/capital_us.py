"""US view: statutory reserves, the NAIC P&C risk-based capital ratio and a rating-agency VaR test.

The RBC formula follows the NAIC's 2024 P&C instructions (sources/structures.yaml `naic_pc_rbc_*`):
- Reserve risk R4 = reserves x max(0, (1 + RBC%) x investment-income factor - 1); premium risk R5 = premium x max(0,
  loss & LAE ratio x investment-income factor + expense ratio - 1), with the industry factors for the line the mutual
  files under (`us_line`). A new company has no history, so its own experience adjustment is 1. A monoline writer's
  concentration factors are 1.
- Rcat charges only earthquake and hurricane (wildfire and convective storm are informational). An AI catastrophe has
  no charge as the formula is written; `with_cat` adds the 1-in-100 net loss as if regulators treated it like Rcat.
- RBC = 1.03 x sqrt(R4^2 + R5^2 + Rcat^2), the 3% being basic operational risk. Asset (R0-R2) and credit (R3) risk are
  left out. Authorized control level (ACL) is half of RBC.
- Total adjusted capital is paid-in capital only: uncalled assessments are not admitted surplus (some RRG domiciles
  admit letters of credit, which the model does not).
- Action levels on TAC / ACL: below 200% company action, 150% regulatory action, 100% authorized control, 70%
  mandatory control. The trend test (200-300% with a combined ratio above 120%) is left out.
- The rating view asks how much capital covers a 99.6% one-year loss after premium.
"""
import math

from .model import Settings
from .pricing import Stack, var

LEVELS = [(2.0, "no action"), (1.5, "company action"), (1.0, "regulatory action"), (0.7, "authorized control")]
# NAIC 2024 industry factors (PR017 lines 4 and 8, PR018 lines 4 and 7): reserve RBC %, its investment-income factor,
# loss & LAE ratio, its investment-income factor.
LINES = dict(other_liability=(0.514, 0.858, 1.003, 0.827), products_liability=(1.014, 0.843, 1.229, 0.788),
             reinsurance_liability=(0.626, 0.816, 1.253, 0.794))
OPERATIONAL = 0.03


def action_level(ratio: float) -> str:
    for threshold, name in LEVELS:
        if ratio >= threshold:
            return name
    return "mandatory control"


def factors(line: str, expense_ratio: float) -> tuple:
    """Charges per unit of reserves and of premium."""
    rbc_pct, inv_res, lr, inv_prem = LINES[line]
    return max((1 + rbc_pct) * inv_res - 1, 0.0), max(lr * inv_prem + expense_ratio - 1, 0.0)


def us(s: Settings, st: Stack, res: dict) -> dict:
    f_res, f_prem = factors(s.us_line, s.expense_ratio)
    r_prem = f_prem * st.premium
    r_res = f_res * res["statutory"]
    r_cat = var(st.net, 0.99)
    tac = s.paid_in_capital

    def view(cat):
        rbc = (1 + OPERATIONAL) * math.sqrt(r_prem ** 2 + r_res ** 2 + cat ** 2)
        ratio = tac / (0.5 * rbc) if rbc else float("inf")
        return rbc, ratio

    rbc, ratio = view(0.0)
    rbc_cat, ratio_cat = view(r_cat)
    need_996 = max(var(st.net, 0.996) - st.premium * (1 - s.expense_ratio), 0.0)
    return dict(statutory_reserves=res["statutory"], reserve_factor=f_res, premium_factor=f_prem, r_premium=r_prem,
                r_reserve=r_res, r_cat=r_cat, rbc=rbc, acl=0.5 * rbc, total_adjusted_capital=tac, rbc_ratio=ratio,
                action_level=action_level(ratio), rbc_with_cat=rbc_cat, acl_with_cat=0.5 * rbc_cat,
                rbc_ratio_with_cat=ratio_cat, action_level_with_cat=action_level(ratio_cat),
                capital_for_996=need_996, rating_cover=tac / need_996 if need_996 else float("inf"))
