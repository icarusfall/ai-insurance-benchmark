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


def test_view_flags_are_plain_python():
    """Logs are written with json default=str, so a numpy bool would become the truthy string "False"."""
    m = Market(2, bots.make(LINEUP))
    for _ in range(6):
        views = m.begin_quarter()
        for v in views.values():
            assert type(v["own"]["restricted"]) is bool
        m.resolve({n: m.ins[n].bot.act(v) for n, v in views.items()})


def test_null_bot_earns_only_interest():
    r = run(0, ["null", "actuary"])["insurers"]["null"]
    assert not r["insolvent"]
    assert abs(r["value"] - P.START_EQUITY * (1 + P.INVEST_RATE) ** P.Q) < 1e-6


def test_null_bot_scores_below_hurdle():
    r = run(0, ["null", "actuary"])["insurers"]["null"]
    assert abs(r["R"] - ((1 + P.INVEST_RATE) / (1 + P.HURDLE)) ** P.Q) < 1e-9


def test_single_risk_rule_voids_oversized_net_lines():
    from bots.base import Bot

    class Greedy(Bot):
        def act(self, view):
            return dict(quotes={a["id"]: dict(premium=0.001, limit=a["ideal_limit"], retention=0.0)
                                for a in view["applicants"]}, decisions={}, ibnr=0.0, dividend=0.0)

    m = Market(1, {"greedy": Greedy()})
    m.run(max_quarters=1)
    cap = P.NET_LINE_MAX * P.START_EQUITY
    lims = [p.limit for p in m.policies.values()]
    assert lims and max(lims) <= cap


def test_dividends_clawed_back_near_insolvency():
    m = Market(1, bots.make(["actuary"]))
    ins = m.ins["actuary"]
    ins.insolvent, ins.insolvent_q = True, 20
    ins.div_q[5], ins.div_q[15] = 10.0, 10.0          # 15 is inside the 8-quarter window, 5 is not
    assert abs(m.value("actuary") - 10.0 * (1 + P.HURDLE) ** (P.Q - 1 - 5)) < 1e-9


def test_briefing_solvency_ratio_matches_restriction():
    """A restricted insurer must never be shown a solvency ratio of 1 or more."""
    for seed in range(4):
        m = Market(seed, bots.make(["reckless", "cycle", "actuary"]))
        for _ in range(P.Q):
            views = m.begin_quarter()
            for v in views.values():
                sr = v["own"]["solvency_ratio"]
                if v["own"]["restricted"]:
                    assert sr is not None and sr < 1
            m.resolve({n: m.ins[n].bot.act(v) for n, v in views.items()})


def test_dossier_articles():
    w = World(7)
    assert not any(" a enormous" in c.text for c in w.clients)
    assert any(" an enormous" in c.text for c in w.clients)
