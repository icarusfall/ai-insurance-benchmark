"""The site's JavaScript model agrees with the Python model it was ported from.

Closed forms and everything computed from a given set of simulated years must match to rounding; the JavaScript
simulation uses its own random numbers, so its averages must match Python's statistically.
"""
import json
import os
import shutil
import subprocess

import pytest
import yaml

from catmodel.capital_s2 import solvency2
from catmodel.capital_us import us
from catmodel.dist import TruncatedPareto
from catmodel.model import DEFAULTS, LEVELS, load, simulate
from catmodel.pricing import build_stack, catbond
from catmodel.reserves import reserves
from catmodel import trajectory as tr

HARNESS = os.path.join(os.path.dirname(__file__), "..", "mutual_site", "tests", "parity.js")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def js(req: dict):
    out = subprocess.run(["node", HARNESS], input=json.dumps(req), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def js_settings(s) -> dict:
    d = {k: v for k, v in s.__dict__.items() if k != "perils"}
    d["perils"] = [dict(name=p.name, rate=p.rate, xm=p.severity.xm, alpha=p.severity.alpha, cap=p.severity.cap,
                        attribution=p.attribution, insurable=p.insurable, common_mode=p.common_mode,
                        rate_cv=p.rate_cv, payout_lag_years=p.payout_lag_years) for p in s.perils]
    return d


def close(a, b, rel=1e-9, abs_=1e-12):
    if isinstance(b, str) or isinstance(a, str):
        return a == b or (a == "inf" and b == float("inf"))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    return a == pytest.approx(b, rel=rel, abs=abs_)


def test_closed_forms_match():
    cases = [dict(xm=1.0, alpha=a, cap=1e4, xs=[0.5, 1, 3, 100, 9999, 2e4], ps=[0.0, 0.3, 0.9, 0.999],
                  layers=[[0, 1], [0, 50], [2, 10], [0, 1e4], [500, 1e5]]) for a in (0.6, 1.0, 1.7)]
    got = js(dict(op="closed", cases=cases))
    for c, g in zip(cases, got):
        d = TruncatedPareto(c["xm"], c["alpha"], c["cap"])
        assert g["sf"] == pytest.approx([float(d.sf(x)) for x in c["xs"]], rel=1e-12)
        assert g["layer"] == pytest.approx([d.layer(r, l) for r, l in c["layers"]], rel=1e-12)
        assert g["quantile"] == pytest.approx([float(d.quantile(p)) for p in c["ps"]], rel=1e-12)
        assert g["mean"] == pytest.approx(d.mean(), rel=1e-12)


@pytest.mark.parametrize("level", LEVELS)
def test_defaults_load_the_same(level):
    with open(DEFAULTS, encoding="utf-8") as f:
        defaults = yaml.safe_load(f)
    got = js(dict(op="load", defaults=defaults, level=level))
    want = js_settings(load(level))
    for k, v in want.items():
        if k == "perils":
            for gp, wp in zip(got["perils"], v):
                for kk, vv in wp.items():
                    assert gp[kk] == vv, (level, wp["name"], kk)
        else:
            assert got[k] == v, (level, k)


@pytest.mark.parametrize("level,changes", [("central", {}), ("pessimistic", {}),
                                           ("central", dict(reinsurance_attach=1.0, reinsurance_limit=2.0,
                                                            government_attach=3.0, government_share=0.8))])
def test_everything_downstream_of_the_years_matches(level, changes):
    from dataclasses import replace
    s = replace(load(level), **changes)
    y = simulate(s, 20_000, seed=5)
    st = build_stack(s, y)
    gross = float(st.claims.mean())
    res = reserves(s, y, float(st.net.mean()) / gross)
    want = dict(premium=st.premium, s2=solvency2(s, st, res), us=us(s, st, res), reserves=res,
                p_calls=float((st.calls > 0).mean()), p_unpaid=float((st.unpaid > 0).mean()),
                bond=catbond(st.claims, 1.0, 3.0, s.catbond_multiple, s.wang_lambda))
    got = js(dict(op="evaluate", settings=js_settings(s), bond=[1.0, 3.0],
                  years=dict(harm=y.harm.tolist(), liable=y.liable.tolist(), claims=y.claims.tolist(),
                             by_peril={k: v.tolist() for k, v in y.by_peril.items()})))
    assert close(got["premium"], want["premium"])
    for part in ("s2", "us", "reserves"):
        for k, v in want[part].items():
            assert close(got[part][k], v), (part, k, got[part][k], v)
    for k in ("p_calls", "p_unpaid"):
        assert close(got[k], want[k])
    for k, v in want["bond"].items():
        assert close(got["bond"][k], v, rel=1e-5, abs_=1e-7), (k, got["bond"][k], v)   # normal approximations
    assert got["expected_claim"] == pytest.approx([p.expected_claim(s.per_event_limit) for p in s.perils], rel=1e-12)


def test_simulation_matches_statistically():
    s = load("pessimistic")
    py = simulate(s, 300_000, seed=11)
    got = js(dict(op="simulate", settings=js_settings(s), n_years=300_000, seed=7))
    assert got["claims"] == pytest.approx(float(py.claims.mean()), rel=0.06)
    for k, v in py.by_peril.items():
        assert got["by_peril"][k] == pytest.approx(float(v.mean()), rel=0.1), k


@pytest.mark.parametrize("level", LEVELS)
def test_trajectories_match(level):
    with open(DEFAULTS, encoding="utf-8") as f:
        defaults = yaml.safe_load(f)
    c = tr.load_capability(level)
    dates = ["2026-04-07", "2026-10-29", "2027-07-01", "2028-03-15", "2029-07-01", "2035-07-01"]
    got = js(dict(op="trajectory", defaults=defaults, level=level, dates=dates))
    for t in tr.TRAJECTORIES:
        want = [tr.horizon(c, t, __import__("datetime").date.fromisoformat(d)) for d in dates]
        for g, w in zip(got["paths"][t]["horizons"], want):
            assert close(g, w, rel=1e-9), (t, g, w)
        for g, year in zip(got["paths"][t]["years"], range(c.first_year, c.last_year + 1)):
            w = tr.multipliers(c, t, year)
            assert g["stopped"] == w["stopped"] and close(g["revenue"], w["revenue"]), (t, year)
            for p, v in w["rates"].items():
                assert close(g["rates"][p], v), (t, year, p)
