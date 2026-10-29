"""Capability trajectories: each path has the shape its source describes, and the projection stops where it should."""
import math
from dataclasses import replace
from datetime import date, timedelta

import pytest

from catmodel.model import load
from catmodel.trajectory import TRAJECTORIES, horizon, load_capability, multipliers, project


@pytest.fixture
def c():
    return load_capability()


def test_every_path_starts_at_the_anchor(c):
    for t in TRAJECTORIES:
        assert horizon(c, t, c.anchor_date) == pytest.approx(c.anchor_hours)


def test_metr_trends_double_on_schedule(c):
    for t, d in (("metr_2023", c.metr_2023_doubling_days), ("metr_long_run", c.metr_long_run_doubling_days)):
        later = c.anchor_date + timedelta(days=round(d * 3))
        assert horizon(c, t, later) / c.anchor_hours == pytest.approx(8, rel=0.01)


def test_ai2027_doublings_shrink_and_blow_up(c):
    d, s = c.ai2027_doubling_days / c.ai2027_pace, c.ai2027_shrink
    one = c.anchor_date + timedelta(days=d)                 # the first doubling takes d days
    assert horizon(c, "ai2027", one) == pytest.approx(2 * c.anchor_hours, rel=0.01)
    two = c.anchor_date + timedelta(days=d * (1 + s))       # the second takes s d
    assert horizon(c, "ai2027", two) == pytest.approx(4 * c.anchor_hours, rel=0.02)
    assert math.isinf(horizon(c, "ai2027", c.anchor_date + timedelta(days=math.ceil(d / (1 - s)))))


def test_plateau_starts_on_trend_and_approaches_its_ceiling(c):
    soon = c.anchor_date + timedelta(days=10)
    assert horizon(c, "plateau", soon) == pytest.approx(horizon(c, "metr_2023", soon), rel=0.01)
    far = horizon(c, "plateau", date(2040, 1, 1))
    assert far < c.plateau_ceiling_hours and far == pytest.approx(c.plateau_ceiling_hours, rel=0.01)


def test_rate_multipliers_are_capped_and_relative_to_now(c):
    m = multipliers(c, "metr_2023", 2027)
    ratio = m["horizon"] / horizon(c, "metr_2023", c.now)
    for p, k in c.elasticity.items():
        assert m["rates"][p] == pytest.approx(min(c.cap_multiple[p], ratio ** k))
    assert multipliers(c, "metr_2023", 2032)["rates"]["bio_misuse"] == c.cap_multiple["bio_misuse"]


def test_projection_stops_at_the_horizon_and_stays_stopped(c):
    rows = project(load(), replace(c, stop_hours=300), "metr_long_run", n_years=2_000)
    stopped = [r["stopped"] for r in rows]
    assert stopped == sorted(stopped) and any(stopped) and not all(stopped)
    assert all(("premium" in r) != r["stopped"] for r in rows)
    first = next(r for r in rows if r["stopped"])
    assert first["horizon"] >= 300


def test_plateau_below_the_stop_never_stops(c):
    assert not any(r["stopped"] for r in project(load(), c, "plateau", n_years=1_000))
