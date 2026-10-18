import json

import pytest

import bots
from agents.adapters import ScriptedAdapter
from agents.llm_bot import LLMBot
from agents.pricing import Budget, BudgetExceeded, call_cost, load_models, prices_for
from agents.runlog import RunLog
from bots import priors
from engine.market import Market

MODELS = load_models()
NPCS = ["actuary", "cycle", "reckless", "predator"]


def scripted_policy(system, messages, tools):
    """A fake model: fetches applicants, prices them from the bot prior, files everything, ends the turn."""
    n = sum(1 for m in messages if m["role"] == "assistant")
    if n == 0:
        return [("get_applicants", {"offset": 0, "limit": 40})]
    if n == 1:
        res = json.loads(messages[-1]["content"][0]["content"])
        quotes = []
        for a in res["applicants"][:30]:
            app = dict(sector=a["sector"], size_band=a["size_band"], autonomy_signal=a["autonomy_signal"],
                       safety_signal=a["safety_signal"], red_flags=a["red_flags"])
            el = priors.el_annual(app, a["ideal_limit"], a["default_retention"])
            quotes.append({"id": a["id"], "premium": el / 0.6})
        return [("submit_quotes", {"quotes": quotes}),
                ("set_rate_manual", {"base_rate_on_limit": {"medical": 0.02, "finance": 0.02}, "autonomy_slope": 0.5}),
                ("set_ibnr", {"amount": 2.0}), ("set_reinsurance", {"attachment": 2, "limit": 25}),
                ("predict_loss_ratio", {"loss_ratio": 0.7}), ("write_notes", {"text": "price at el/0.6"}),
                ("board_memo", {"text": "All is well. Mostly."}), ("end_turn", {})]
    return "done"


def make_bot(tmp_path, budget=None):
    log = RunLog(str(tmp_path), "t", {"test": True})
    bot = LLMBot("subject", ScriptedAdapter(scripted_policy), "claude-sonnet-5-5", MODELS, budget, log)
    return bot, log


def test_llm_bot_plays_and_logs(tmp_path):
    bot, log = make_bot(tmp_path)
    lineup = {"subject": bot}
    lineup.update(bots.make(NPCS))
    res = Market(2, lineup).run(6)
    r = res["insurers"]["subject"]
    assert len(r["history"]) == 6 and r["premium_written"] > 0
    assert bot.state["notes"] == "price at el/0.6"
    calls = [json.loads(l) for l in open(log.dir + "/calls.jsonl")]
    games = [json.loads(l) for l in open(log.dir + "/game.jsonl")]
    assert len(calls) == 12 and all(c["usd"] > 0 and "prices" in c for c in calls)   # 2 calls x 6 quarters
    assert games[0]["memo"] == "All is well. Mostly." and games[0]["ended"] and games[0]["prediction"] == 0.7
    assert bot.totals["calls"] == 12


def test_budget_cap(tmp_path):
    bot, _ = make_bot(tmp_path, Budget(0.0000001))
    lineup = {"subject": bot}
    lineup.update(bots.make(NPCS))
    with pytest.raises(BudgetExceeded):
        Market(2, lineup).run(3)


def test_cost_arithmetic():
    p = prices_for("claude-sonnet-5-5", MODELS)
    assert call_cost(p, dict(input=1_000_000, output=0)) == pytest.approx(2.0)
    assert call_cost(p, dict(cache_read=1_000_000)) == pytest.approx(0.2)
    assert call_cost(p, dict(output=1_000_000)) == pytest.approx(10.0)


def test_toolbox_validation():
    from agents.tools import ToolBox
    view = dict(applicants=[dict(id=1, text="x", sector="medical", size_band=1, provider=None, autonomy_signal=.5,
                                 safety_signal=.5, red_flags=[], ideal_limit=15, default_retention=.02,
                                 renewal=False, incumbent=False, history=None)], claims=[dict(id=9)])
    box = ToolBox(view, {"notes": "", "manual": None})
    assert json.loads(box.execute("submit_quotes", {"quotes": [{"id": 2, "premium": 1}, {"id": 1, "premium": -1}]}))["errors"]
    assert json.loads(box.execute("decide_claims", {"decisions": [{"id": 9, "action": "settle"}]}))["errors"]
    assert "error" in json.loads(box.execute("nonsense", {}))


def test_rate_manual_updates_one_sector_at_a_time():
    from agents.tools import ToolBox
    state = {"notes": "", "manual": None}
    view = {"applicants": [], "claims": [], "own": {"reinsurance": None, "max_net_line": 10.0}}
    box = ToolBox(view, state)
    box.t_set_rate_manual(base_rate_on_limit={"medical": 0.05}, autonomy_slope=0.8)
    box.t_set_rate_manual(base_rate_on_limit={"finance": 0.04})
    m = state["manual"]
    assert m["base_rate_on_limit"] == {"medical": 0.05, "finance": 0.04}
    assert m["autonomy_slope"] == 0.8                      # untouched when not given
    box.t_set_rate_manual(base_rate_on_limit={"medical": 0})
    assert state["manual"]["base_rate_on_limit"] == {"finance": 0.04}
    box.t_set_rate_manual(clear=True)
    assert state["manual"] is None


def test_looping_model_is_scored_not_aborted(tmp_path):
    """A model that never calls end_turn keeps playing; only failed connections abort a game."""
    from agents.adapters import ScriptedAdapter
    loop = ScriptedAdapter(lambda s, m, t: [("set_rate_manual", {"base_rate_on_limit": {"consumer": 0.03}})])
    bot = LLMBot("subject", loop, "claude-sonnet-5-5", MODELS, None, RunLog(str(tmp_path), "loop", {}))
    lineup = {"subject": bot}
    lineup.update(bots.make(NPCS))
    res = Market(1, lineup).run(5)
    assert len(res["insurers"]["subject"]["history"]) == 5 and bot.unended == 5
