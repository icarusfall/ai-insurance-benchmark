"""v0.4 catastrophes: the peril process keeps its promises (vendor concentration averages out, the closed-form
expectation the reinsurer and actuary use matches the world, misuse catastrophes are less often the client's fault)."""
import math

import numpy as np

from engine import params as P
from engine import loss, perils
from engine.world import World


def test_version():
    assert P.ENV_VERSION.startswith("0.4")


def test_concentration_averages_to_one():
    for name in P.PERILS:
        assert math.isclose(sum(s * perils.conc_mean(name, i) for i, s in enumerate(P.PROVIDER_SHARES)), 1.0)
    # a one-vendor event: the traced vendor's clients are hit far more often than the rest
    assert perils.conc("cyber_misuse", 0, 0) / perils.conc("cyber_misuse", 1, 0) > 10


def test_capability_paths():
    for path in P.CAPABILITY_PATHS:
        h = [perils.horizon(path, q) for q in range(P.Q)]
        assert h[0] == P.HORIZON_START and all(b >= a for a, b in zip(h, h[1:]))
    assert perils.horizon("plateau", 1000) <= P.PLATEAU_CEILING + 1e-6
    for name, p in P.PERILS.items():
        assert perils.rate_mult(name, P.HORIZON_START) == 1.0 and perils.rate_mult(name, 1e12) == p["cap_mult"]


def test_size_grid_is_truncated_pareto():
    for name, p in P.PERILS.items():
        g = perils.size_grid(name)
        assert g.min() >= 1 and g.max() <= p["cap"]
        assert math.isclose(perils.draw_size(name, 0.0), 1.0) and math.isclose(perils.draw_size(name, 1.0), p["cap"])


def test_closed_form_matches_world():
    """The closed-form expected catastrophe loss (used by the reinsurer and the actuary) agrees with the events the
    world draws. Checked at event level (hit chance x mean loss per hit), since client-level sums are too fat-tailed."""
    per_hit = loss.cat_layer_expectation(0, 1e9, 0.0)
    real = ana = 0.0
    for seed in range(200):
        w = World(seed)
        real += sum(e.data["hit"] * e.data["sev"] * per_hit for e in w.events if e.kind == "cat")
        ana += sum(perils.expected_quarter(None, 0, 1e9, 0.0, w.horizon[q]) for q in range(4, P.Q))
    assert 0.8 < real / ana < 1.25


def test_misuse_catastrophes_are_murkier_and_shared():
    w = World(1)
    found = set()
    for c in w.clients:
        for q in range(P.Q):
            for inc in w.incidents(c, q):
                if inc["comp"] == "cat":
                    p = P.PERILS[inc["peril"]]
                    assert inc["misuse"] == p["misuse"] and inc["attribution"] == p["attribution"]
                    assert (inc["murk"] >= 0.5) == p["misuse"] or not p["misuse"]
                    found.add(inc["peril"])
    assert w.liability_p(5, "finance", 0.6, 0.6) < w.liability_p(5, "finance", 0.6)
    assert not any(e.data.get("peril") == "bio_misuse" for e in w.events if e.kind == "cat")


def test_capability_reports_are_annual():
    w = World(2)
    qs = [e.q for e in w.events if e.kind == "capability"]
    assert qs == list(range(4, P.Q, 4))
