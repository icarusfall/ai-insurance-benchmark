"""US view: statutory reserves, an RBC-style ratio and a rating-agency VaR test.

Simplifications, all deliberate for a toy:
- RBC = sqrt(premium charge^2 + reserve charge^2 + catastrophe charge^2), where the catastrophe charge follows NAIC's
  Rcat idea (the 1-in-100 net catastrophe loss). Premium and reserve factors are placeholders until NAIC factors are
  sourced. Authorized control level (ACL) is half of RBC.
- Total adjusted capital is paid-in capital only: uncalled assessments are not admitted surplus.
- Action levels as in the benchmark's v0.3 ladder: 200% company action, 150% regulatory action, 100% authorized
  control, 70% mandatory control.
- The rating view asks how much capital covers a 99.6% one-year loss after premium.
"""
import math

from .model import Settings
from .pricing import Stack, var

LEVELS = [(2.0, "no action"), (1.5, "company action"), (1.0, "regulatory action"), (0.7, "authorized control")]


def action_level(ratio: float) -> str:
    for threshold, name in LEVELS:
        if ratio >= threshold:
            return name
    return "mandatory control"


def us(s: Settings, st: Stack, res: dict) -> dict:
    r_prem = s.us_premium_factor * st.premium
    r_res = s.us_reserve_factor * res["statutory"]
    r_cat = var(st.net, 0.99)
    rbc = math.sqrt(r_prem ** 2 + r_res ** 2 + r_cat ** 2)
    acl = 0.5 * rbc
    tac = s.paid_in_capital
    ratio = tac / acl if acl else float("inf")
    need_996 = max(var(st.net, 0.996) - st.premium * (1 - s.expense_ratio), 0.0)
    return dict(statutory_reserves=res["statutory"], r_premium=r_prem, r_reserve=r_res, r_cat=r_cat, rbc=rbc, acl=acl,
                total_adjusted_capital=tac, rbc_ratio=ratio, action_level=action_level(ratio),
                capital_for_996=need_996, rating_cover=tac / need_996 if need_996 else float("inf"))
