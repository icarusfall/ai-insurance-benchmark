"""LLMBot: a Bot whose act() runs a tool-use loop against a model adapter, within a budget."""
import time

from bots.base import Bot

from .http import AdapterError
from . import prompt as pr
from .pricing import Budget, call_cost, prices_for
from .tools import TOOLS, ToolBox

MAX_ROUNDS = 25


class LLMBot(Bot):
    def __init__(self, name: str, adapter, model: str, models_cfg: dict = None, budget: Budget = None,
                 runlog=None, max_tokens: int = 16000):
        self.name = name
        self.adapter = adapter
        self.model = model
        self.prices = prices_for(model, models_cfg) if models_cfg is not None or model else None
        self.budget = budget
        self.runlog = runlog
        self.max_tokens = max_tokens
        self.state = {"notes": "", "manual": None}
        self.totals = dict(input=0, output=0, cache_read=0, cache_write=0, calls=0, usd=0.0)
        self.errors = 0
        self.refusals = 0
        self.unended = 0
        self.bad_streak = 0

    def reset(self, seed, seat):
        super().reset(seed, seat)
        self.state = {"notes": "", "manual": None}

    # ------------------------------------------------------------------ one quarter
    def act(self, view: dict) -> dict:
        q = view["q"]
        box = ToolBox(view, self.state)
        messages = [{"role": "user", "content": pr.build_briefing(view, self.state)}]
        nudged = False
        tool_log, refusal = [], False
        for rnd in range(MAX_ROUNDS):
            try:
                turn = self.adapter.complete(pr.SYSTEM, messages, TOOLS, self.max_tokens)
            except AdapterError as e:            # transient provider failure after retries: play on with what we have
                if not e.retryable:
                    raise
                self.errors += 1
                tool_log.append(dict(tool="_adapter_error", input={}, output=str(e)[:300]))
                break
            self._account(q, rnd, turn, len(turn.tool_calls))
            messages.append({"role": "assistant", "content": turn.raw})
            if turn.stop_reason == "refusal":
                refusal = True
                self.refusals += 1
                break
            if not turn.tool_calls:
                if box.done or nudged:
                    break
                nudged = True
                messages.append({"role": "user", "content": "You have not called end_turn. Finish the quarter's "
                                                            "decisions with the tools, then call end_turn."})
                continue
            results = []
            for cid, name, inp in turn.tool_calls:
                out = box.execute(name, inp)
                tool_log.append(dict(tool=name, input=inp, output=out if len(out) < 600 else out[:600] + "..."))
                results.append({"type": "tool_result", "tool_use_id": cid, "content": out})
            messages.append({"role": "user", "content": results})
            if box.done:
                break
        if not box.done:
            self.unended += 1
        self.bad_streak = self.bad_streak + 1 if (not box.done and not box.quotes) else 0
        if self.bad_streak >= 3:
            raise AdapterError("three consecutive quarters without a completed turn; aborting", retryable=False)
        actions = box.actions()
        if self.runlog:
            self.runlog.game(q=q, bot=self.name, refusal=refusal, ended=box.done, rounds=len(tool_log),
                             memo=box.memo, prediction=box.prediction, notes=self.state.get("notes"),
                             manual=self.state.get("manual"), tools=tool_log,
                             quotes=len(actions["quotes"]), decisions=len(actions["decisions"]),
                             ibnr=actions["ibnr"], dividend=actions["dividend"],
                             raise_capital=actions.get("raise_capital"), reinsurance=actions.get("reinsurance"),
                             own=view["own"])
        return actions

    # ------------------------------------------------------------------- accounting
    def _account(self, q, rnd, turn, ntools):
        usd = turn.cost if turn.cost is not None else (call_cost(self.prices, turn.usage) if self.prices else 0.0)
        for k in ("input", "output", "cache_read", "cache_write"):
            self.totals[k] += turn.usage.get(k, 0)
        self.totals["calls"] += 1
        self.totals["usd"] += usd
        if self.runlog:
            self.runlog.call(bot=self.name, model=self.model, seed=self.seed, q=q, round=rnd, usage=turn.usage,
                             usd=usd, latency=turn.latency, tool_calls=ntools, stop_reason=turn.stop_reason,
                             request_id=turn.request_id, prices=self.prices, ts=time.time())
        if self.budget:
            self.budget.add(usd)
