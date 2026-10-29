"""The sensitivity sweep: same random numbers in every run, so effects are exact where they should be."""
import pytest

from catmodel import sensitivity


@pytest.fixture(scope="module")
def sweep():
    old = sensitivity.N_YEARS
    sensitivity.N_YEARS = 5_000
    try:
        yield sensitivity.sweep()
    finally:
        sensitivity.N_YEARS = old


def test_revenue_scales_the_premium_share_exactly(sweep):
    r = next(r for r in sweep["rows"] if r["key"] == "revenue")
    assert r["low"]["premium_share"] * r["low_value"] == pytest.approx(r["high"]["premium_share"] * r["high_value"], rel=1e-12)
    assert r["low"]["share_paid"] == r["high"]["share_paid"] == sweep["base"]["share_paid"]


def test_every_row_has_both_ends_and_a_swing(sweep):
    assert len(sweep["rows"]) >= 15
    for r in sweep["rows"]:
        for m in sensitivity.METRICS:
            assert r["swing"][m] == pytest.approx(abs(r["high"][m] - r["low"][m]))
