"""US capital: the NAIC factors in the model are the ones in the registry, and the formula sees no AI catastrophe."""
import pytest

from catmodel import capital_us
from mutual_site.build import registry


def _entry(id_):
    return next(e for e in registry() if e["id"] == id_)


def test_line_factors_are_the_registry_values():
    values = _entry("naic_pc_rbc_underwriting_factors_2024")["values"]
    for line, (rbc_pct, inv_res, lr, inv_prem) in capital_us.LINES.items():
        v = values[line]
        assert (rbc_pct, inv_res, lr, inv_prem) == (v["reserve_rbc_pct"], v["reserve_inv"], v["loss_ratio"], v["premium_inv"])


def test_formula_constants_are_the_registry_values():
    v = _entry("naic_pc_rbc_formula")["values"]
    assert capital_us.OPERATIONAL == v["operational_add_on"]
    assert [t for t, _ in capital_us.LEVELS] == [v["company_action"], v["regulatory_action"], v["authorized_control"], v["mandatory_control"]]


def test_charges_per_dollar():
    assert capital_us.factors("other_liability", 0.10) == pytest.approx((1.514 * 0.858 - 1, 0.0))
    assert capital_us.factors("products_liability", 0.10) == pytest.approx((2.014 * 0.843 - 1, 1.229 * 0.788 - 0.9))


def test_adding_the_ai_tail_only_lowers_the_ratio():
    from catmodel.model import load
    from catmodel.report import run
    u = run(load(), n_years=20_000)["us"]
    assert u["rbc_ratio_with_cat"] < u["rbc_ratio"] and u["acl_with_cat"] > u["acl"]
