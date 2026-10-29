"""The toy catastrophe model: closed forms agree with simulation, and the stack and capital rules behave."""
import math
from dataclasses import replace

import numpy as np
import pytest

from catmodel.dist import TruncatedPareto
from catmodel.model import Peril, Settings, load, simulate
from catmodel.pricing import catbond, lane_spread
from catmodel.report import run


@pytest.mark.parametrize("alpha", [0.6, 1.0, 1.7])
def test_layer_matches_monte_carlo(alpha):
    d = TruncatedPareto(10.0, alpha, 1e4)
    x = d.sample(np.random.default_rng(1), 400_000)
    for r, l in [(0, 5), (0, 50), (20, 100), (0, 1e4)]:
        mc = np.minimum(np.maximum(x - r, 0), l).mean()
        assert d.layer(r, l) == pytest.approx(mc, rel=0.03), (alpha, r, l)


def test_survival_and_quantile_are_inverse():
    d = TruncatedPareto(1.0, 0.7, 1e5)
    assert d.sf(0.5) == 1.0 and d.sf(1e5) == 0.0
    for p in [0.1, 0.5, 0.99, 0.9999]:
        assert 1 - d.sf(d.quantile(p)) == pytest.approx(p)
    assert d.quantile(0.0) == pytest.approx(1.0) and d.quantile(1.0) == pytest.approx(1e5)


def test_simulated_claims_match_closed_form_when_only_event_limits_bind():
    p = Peril("x", rate=0.3, severity=TruncatedPareto(1.0, 1.2, 1e3), attribution=0.5, insurable=0.8)
    s = Settings(perils=(p,), members=4, per_event_limit=2.0, annual_aggregate=1e9)
    y = simulate(s, 400_000, seed=3)
    assert y.claims.mean() == pytest.approx(p.expected_claim(2.0), rel=0.03)


def test_common_mode_spreads_liability_across_member_limits():
    p = Peril("x", rate=1.0, severity=TruncatedPareto(100.0, 3.0, 1e3), attribution=1.0, insurable=1.0)
    solo = simulate(Settings(perils=(p,), members=5, per_event_limit=1.0, annual_aggregate=1e9), 50_000, 0)
    joint = simulate(Settings(perils=(replace(p, common_mode=1.0),), members=5, per_event_limit=1.0,
                              annual_aggregate=1e9), 50_000, 0)
    assert joint.claims.mean() == pytest.approx(5 * solo.claims.mean(), rel=0.05)


def test_stack_pays_in_order_and_leaves_unpaid_only_beyond_calls():
    s = load()
    r = run(s, 50_000, seed=2)
    st = r["stack"]
    resources = st.premium * (1 - s.expense_ratio) + s.paid_in_capital
    assert np.all(st.calls <= s.members * s.callable_per_member + 1e-12)
    assert np.all((st.unpaid > 0) <= (st.net > resources + s.members * s.callable_per_member - 1e-9))
    assert np.allclose(st.net + st.reinsured + st.government, st.claims)


def test_ancillary_own_funds_capped_at_half_scr_and_excluded_from_mcr():
    s = load()
    r = run(s, 50_000, seed=2)
    s2 = r["s2"]
    assert s2["eligible_own_funds_scr"] <= s2["tier1"] + 0.5 * s2["scr"] + 1e-12
    assert s2["eligible_own_funds_mcr"] == s2["tier1"]
    assert 0.25 * s2["scr"] - 1e-12 <= s2["mcr"] <= 0.45 * s2["scr"] + 1e-12


# Lane (2000) Table 2: the sixteen 1999 tranches his equation was fitted to, as (EER, PFL, CEL) in decimals of par.
LANE_1999 = [(.0364, .0115, .3652), (.0552, .0525, .5410), (.0393, .0084, .7500), (.0324, .0058, .8621),
             (.0272, .0064, .6563), (.0381, .0060, .7500), (.0327, .0076, .5789), (.0652, .1210, .3678),
             (.0452, .0156, .1923), (.0282, .0017, 1.0000), (.0485, .0078, .8077), (.0381, .0100, .7500),
             (.0263, .0019, .5789), (.0352, .0029, .7931), (.1095, .0547, .5923), (.0383, .0113, .6460)]


def test_lane_spread_reproduces_the_paper_fit():
    log_resid = [math.log(lane_spread(pfl, cel) / eer) for eer, pfl, cel in LANE_1999]
    assert abs(sum(log_resid) / len(log_resid)) < 0.05      # a log-linear fit with intercept: residuals average ~0
    assert max(abs(r) for r in log_resid) < 0.6             # single deals scatter (adjusted R² 0.84)


def test_catbond_metrics_are_ordered():
    x = TruncatedPareto(0.1, 1.1, 100).sample(np.random.default_rng(0), 200_000)
    b = catbond(x, 1.0, 3.0, multiple=3.0, wang_lambda=0.0)
    assert b["prob_attach"] >= b["expected_loss"] >= b["prob_exhaust"]
    assert b["spread_wang"] == pytest.approx(b["expected_loss"], rel=0.02)     # lambda 0 prices at expected loss
    assert catbond(x, 1.0, 3.0, 3.0, 0.5)["spread_wang"] > b["spread_wang"]


def test_defaults_load_at_every_level():
    for level in ("optimistic", "central", "pessimistic"):
        s = load(level)
        assert len(s.perils) == 3 and s.members == 5


def test_bio_insurability_report_keeps_hand_written_text(tmp_path, monkeypatch):
    from catmodel import insurability as ins
    s = ins.bio_only()
    assert ins.limit_for_liability_share(s, 0.25) < ins.limit_for_liability_share(s, 0.5)
    path = tmp_path / "bio.md"
    path.write_text(f"# notes\n{ins.START}\nold\n{ins.END}\ntail\n", encoding="utf-8")
    ins.markdown = lambda: f"{ins.START}\nnew\n{ins.END}"
    ins.write(str(path))
    assert path.read_text(encoding="utf-8") == f"# notes\n{ins.START}\nnew\n{ins.END}\ntail\n"
