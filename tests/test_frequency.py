"""Three ways to count: the actuarial estimate is a Jeffreys-Poisson posterior, the causal one a product of links."""
import math

import pytest

from catmodel import frequency
from catmodel.model import load


def test_gamma_quantiles_match_known_values():
    assert frequency.gamma_quantile(0.95, 1.0) == pytest.approx(-math.log(0.05), rel=1e-9)   # exponential
    assert frequency.gamma_quantile(0.95, 0.5) == pytest.approx(3.841459 / 2, rel=1e-6)      # chi-squared(1) / 2


def test_actuarial_is_the_posterior_mean_with_a_bracketing_interval():
    d = frequency._defaults()
    for p in d["perils"]:
        a = frequency.actuarial(d, p)
        assert a["rate"] == pytest.approx((a["events"] + 0.5) / a["years"])
        assert a["low"] < a["rate"] < a["high"]


def test_causal_rate_is_the_product_of_its_links():
    d = frequency._defaults()
    for p, links in d["frequency"]["causal"].items():
        c = frequency.chain(d, p)
        assert c[-1]["running"] == pytest.approx(math.prod(l["central"] for l in links))
        assert frequency.chain(d, p, overrides={links[0]["key"]: 0})[-1]["running"] == 0


def test_expert_method_leaves_settings_unchanged_and_others_replace_rates():
    s = load()
    assert frequency.with_method(s, "expert") == s
    r = frequency.rates(method="causal")
    assert [p.rate for p in frequency.with_method(s, "causal").perils] == [r[p.name] for p in s.perils]
