"""The market lens: mappings invert cleanly, and the preset is what the snapshot implies."""
import math
from datetime import date

import pytest

from catmodel import markets
from catmodel.model import load
from catmodel.trajectory import load_capability


def test_growth_years_equals_years_when_nothing_grows():
    c = load_capability()
    flat = c.__class__(**{**c.__dict__, "elasticity": {k: 0.0 for k in c.elasticity}})
    assert markets.growth_years(flat, "metr_2023", "agent_runaway", date(2027, 1, 1), date(2029, 1, 1)) ==         pytest.approx(731 / 365.25, rel=1e-6)


def test_rate_mapping_inverts():
    """A rate implied from a market, run forward on the same path, gives back the market's probability."""
    snap, s, c = markets.load_snapshot(), load(), load_capability()
    r = markets.implied(snap, s, c)
    for row, q in ((row, next(q for q in snap["questions"] if q["id"] == row["id"])) for row in r["rows"] if row["kind"] == "rate"):
        p = next(p for p in s.perils if p.name == row["peril"])
        exposure = markets.growth_years(c, c.trajectory, p.name, date.fromisoformat(snap["taken"]), date.fromisoformat(q["closes"]))
        at_threshold = row["implied_rate"] * (p.severity.xm / q["mapping"]["threshold_bn"]) ** p.severity.alpha
        prob = 1 - math.exp(-at_threshold * exposure / q["mapping"]["share"])
        assert prob == pytest.approx(q["probability"], rel=1e-9)


def test_median_date_interpolates():
    pts = [{"date": "2027-01-01", "p": 0.2}, {"date": "2029-01-01", "p": 0.8}]
    assert markets.median_date(pts) == date(2028, 1, 1)
    assert markets.median_date([{"date": "2027-01-01", "p": 0.4}]) is None


def test_preset_applies_every_override():
    r = markets.implied()
    s, c = markets.apply_preset(load(), load_capability(), r["preset"])
    for key, v in r["preset"].items():
        if key.startswith("capability."):
            assert getattr(c, key.split(".", 1)[1]) == v
        elif "." in key:
            peril, field = key.split(".")
            assert getattr(next(p for p in s.perils if p.name == peril), field) == v
        else:
            assert getattr(s, key) == v
    assert 0 < r["hazard"] < 0.5 and r["agi_median"]
