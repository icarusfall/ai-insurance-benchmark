import math

import bots
from engine import params as P
from engine.market import Market
from engine.world import World

LINEUP = ["actuary", "reckless", "cycle", "predator", "random"]


def run(seed, lineup=LINEUP):
    return Market(seed, bots.make(lineup)).run()


def test_deterministic():
    a, b = run(3), run(3)
    for n in LINEUP:
        assert a["insurers"][n]["value"] == b["insurers"][n]["value"]
        assert a["insurers"][n]["insolvent_q"] == b["insurers"][n]["insolvent_q"]


def test_exogenous_world_independent_of_insurers():
    """Common random numbers: events and incidents never depend on who plays."""
    w1, w2 = World(5), World(5)
    assert [(e.q, e.kind) for e in w1.events] == [(e.q, e.kind) for e in w2.events]
    for c1, c2 in zip(w1.clients[:50], w2.clients[:50]):
        for q in range(P.Q):
            assert w1.incidents(c1, q) == w2.incidents(c2, q)
    # and the market's event list is the same whatever the lineup
    ev_a = run(5, ["actuary", "random"])["events"]
    ev_b = run(5, ["reckless", "cycle", "predator"])["events"]
    assert ev_a == ev_b


def test_results_sane():
    r = run(1)
    for n, x in r["insurers"].items():
        assert not math.isnan(x["score"])
        assert x["value"] >= 0
        assert len(x["history"]) == P.Q
