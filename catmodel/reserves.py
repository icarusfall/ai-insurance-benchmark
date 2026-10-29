"""Expected outstanding claims at year end, from each peril's payment lag.

Claims arise evenly through the year and are paid at an exponential rate with mean lag D years, so the expected
unpaid fraction at year end is D(1 - e^(-1/D)), and the present value of a claim's payments is 1/(1 + rD)
(continuous discounting at rate r). Both are toy simplifications of a payment pattern.
"""
import math

import numpy as np

from .model import Settings, Years


def unpaid_fraction(lag: float) -> float:
    return lag * (1 - math.exp(-1 / lag)) if lag > 0 else 0.0


def reserves(s: Settings, y: Years, net_share: float = 1.0) -> dict:
    """Expected year-end reserves, undiscounted (US statutory) and discounted (Solvency II best estimate).

    net_share scales gross claims to the mutual's retained share after reinsurance and government layers.
    """
    undisc = disc = lag_weighted = total = 0.0
    for p in s.perils:
        el = float(np.mean(y.by_peril[p.name])) * net_share
        u = unpaid_fraction(p.payout_lag_years)
        undisc += el * u
        disc += el * u / (1 + s.discount_rate * p.payout_lag_years)
        lag_weighted += el * u * p.payout_lag_years
        total += el * u
    return dict(statutory=undisc, best_estimate=disc, duration=lag_weighted / total if total else 0.0)
