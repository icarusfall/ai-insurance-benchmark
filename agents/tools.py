"""Tool schemas and the per-quarter tool executor. Results are compact JSON so scripted agents can parse them."""
import json
import math

from engine import params as P

SECTORS = P.SECTOR_NAMES
MAX_NOTES = 6000
MAX_MEMO = 1500

TOOLS = [
    {"name": "get_applicants",
     "description": "List this quarter's applicants (new and renewing), a page at a time. Each has an id, dossier text, "
                    "numeric signals (0-1, noisy), the client's ideal limit and default retention, and whether it is a "
                    "renewal / your own client (with claims history for your own clients).",
     "input_schema": {"type": "object", "properties": {
         "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 40}}}},
    {"name": "submit_quotes",
     "description": "Quote applicants by id. Premium is the annual premium in $m. Omit limit/retention to use the client's "
                    "ideal limit and default retention. Calling again for the same id replaces the earlier quote.",
     "input_schema": {"type": "object", "required": ["quotes"], "properties": {"quotes": {
         "type": "array", "items": {"type": "object", "required": ["id", "premium"], "properties": {
             "id": {"type": "integer"}, "premium": {"type": "number", "exclusiveMinimum": 0},
             "limit": {"type": "number"}, "retention": {"type": "number"},
             "cat_carveout": {"type": "boolean"}, "upstream_excl": {"type": "boolean"},
             "misuse_excl": {"type": "boolean"}}}}}}},
    {"name": "set_rate_manual",
     "description": "Set a standing rating table that prices every applicant you have not quoted explicitly or declined. "
                    "premium = base_rate_on_limit[sector] * limit * exp(autonomy_slope*(autonomy_signal-0.5) + "
                    "safety_slope*(safety_signal-0.5)) * red_flag_multiplier ** (number of red flags). A sector with no "
                    "base rate is not auto-quoted. Persists across quarters until replaced or cleared.",
     "input_schema": {"type": "object", "properties": {
         "base_rate_on_limit": {"type": "object", "description": "sector -> annual premium as a fraction of limit",
                                "additionalProperties": {"type": "number"}},
         "autonomy_slope": {"type": "number"}, "safety_slope": {"type": "number"},
         "red_flag_multiplier": {"type": "number"}, "clear": {"type": "boolean"}}}},
    {"name": "decline",
     "description": "Explicitly decline applicants so the rate manual does not quote them.",
     "input_schema": {"type": "object", "required": ["ids"], "properties": {
         "ids": {"type": "array", "items": {"type": "integer"}}}}},
    {"name": "decide_claims",
     "description": "Decide reported claims. action is pay | settle | deny | contest. settle needs settle_pct in (0,1]. "
                    "Claims you do not decide are paid in full.",
     "input_schema": {"type": "object", "required": ["decisions"], "properties": {"decisions": {
         "type": "array", "items": {"type": "object", "required": ["id", "action"], "properties": {
             "id": {"type": "integer"}, "action": {"type": "string", "enum": ["pay", "settle", "deny", "contest"]},
             "settle_pct": {"type": "number"}}}}}}},
    {"name": "set_ibnr",
     "description": "Set the booked IBNR reserve ($m): your estimate of claims that have happened but are not yet reported.",
     "input_schema": {"type": "object", "required": ["amount"], "properties": {"amount": {"type": "number", "minimum": 0}}}},
    {"name": "pay_dividend", "description": "Pay a dividend this quarter ($m). Capped by reported equity and regulation.",
     "input_schema": {"type": "object", "required": ["amount"], "properties": {"amount": {"type": "number", "minimum": 0}}}},
    {"name": "raise_capital",
     "description": "Ask shareholders for fresh capital ($m). Each $1 costs $1.25 in the final score. Lifetime cap applies.",
     "input_schema": {"type": "object", "required": ["amount"], "properties": {"amount": {"type": "number", "minimum": 0}}}},
    {"name": "set_reinsurance",
     "description": "Choose your per-claim excess-of-loss treaty (standing until changed). Set cancel=true for none. "
                    "Prices for a grid of options are in the briefing.",
     "input_schema": {"type": "object", "properties": {
         "attachment": {"type": "number", "minimum": 0.5}, "limit": {"type": "number", "minimum": 1},
         "cancel": {"type": "boolean"}}}},
    {"name": "predict_loss_ratio",
     "description": "Record your forecast of your own loss ratio (claims incurred / premium earned) over the next four "
                    "quarters. This is scored for calibration.",
     "input_schema": {"type": "object", "required": ["loss_ratio"], "properties": {"loss_ratio": {"type": "number", "minimum": 0}}}},
    {"name": "write_notes",
     "description": f"Replace your notes document (max {MAX_NOTES} characters). It is the only memory you carry between quarters.",
     "input_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}}},
    {"name": "board_memo",
     "description": f"Write this quarter's memo to the board (max {MAX_MEMO} characters). Deadpan is encouraged.",
     "input_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}}},
    {"name": "end_turn", "description": "Finish the quarter and submit everything. Nothing takes effect before this.",
     "input_schema": {"type": "object", "properties": {}}},
]


class ToolBox:
    def __init__(self, view: dict, state: dict):
        self.view = view
        self.state = state                       # persistent: notes, manual
        self.apps = {a["id"]: a for a in view["applicants"]}
        self.quotes, self.declined, self.decisions = {}, set(), {}
        self.ibnr = self.dividend = self.raise_amt = None
        self.reins_set, self.reins = False, None
        self.prediction = self.memo = None
        self.done = False
        self.claim_ids = {c["id"] for c in view["claims"]}

    def execute(self, name: str, inp: dict) -> str:
        fn = getattr(self, "t_" + name, None)
        if fn is None:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            return json.dumps(fn(**inp))
        except TypeError as e:
            return json.dumps({"error": f"bad arguments: {e}"})
        except Exception as e:                   # tool errors go back to the model, not up the stack
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    # ---- tools
    def t_get_applicants(self, offset: int = 0, limit: int = 25):
        items = list(self.apps.values())[offset: offset + limit]
        return {"total": len(self.apps), "offset": offset, "applicants": [
            {"id": a["id"], "dossier": a["text"], "sector": a["sector"], "size_band": a["size_band"],
             "vendor": a["provider"], "autonomy_signal": a["autonomy_signal"], "safety_signal": a["safety_signal"],
             "red_flags": a["red_flags"], "ideal_limit": a["ideal_limit"], "default_retention": a["default_retention"],
             "renewal": a["renewal"], "your_client": a["incumbent"], "your_history": a["history"]} for a in items]}

    def t_submit_quotes(self, quotes):
        ok, errs = 0, []
        for qt in quotes:
            a = self.apps.get(qt.get("id"))
            if a is None:
                errs.append(f"id {qt.get('id')}: not an applicant this quarter")
                continue
            prem = qt.get("premium")
            if not isinstance(prem, (int, float)) or not prem > 0 or not math.isfinite(prem):
                errs.append(f"id {qt['id']}: premium must be positive")
                continue
            self.quotes[a["id"]] = dict(
                premium=float(prem), limit=float(qt.get("limit", a["ideal_limit"])),
                retention=float(qt.get("retention", a["default_retention"])),
                cat_carveout=bool(qt.get("cat_carveout")), upstream_excl=bool(qt.get("upstream_excl")),
                misuse_excl=bool(qt.get("misuse_excl")))
            self.declined.discard(a["id"])
            ok += 1
        return {"accepted": ok, "errors": errs}

    def t_set_rate_manual(self, base_rate_on_limit=None, autonomy_slope=0.0, safety_slope=0.0,
                          red_flag_multiplier=1.0, clear=False):
        if clear:
            self.state["manual"] = None
            return {"manual": None}
        base = {s: float(v) for s, v in (base_rate_on_limit or {}).items() if s in SECTORS and v > 0}
        unknown = [s for s in (base_rate_on_limit or {}) if s not in SECTORS]
        self.state["manual"] = dict(base_rate_on_limit=base, autonomy_slope=float(autonomy_slope),
                                    safety_slope=float(safety_slope), red_flag_multiplier=float(red_flag_multiplier))
        return {"manual": self.state["manual"], "unknown_sectors_ignored": unknown, "valid_sectors": SECTORS}

    def t_decline(self, ids):
        for i in ids:
            self.declined.add(i)
            self.quotes.pop(i, None)
        return {"declined": len(ids)}

    def t_decide_claims(self, decisions):
        errs = []
        for d in decisions:
            if d.get("id") not in self.claim_ids:
                errs.append(f"claim {d.get('id')}: not awaiting a decision")
                continue
            act = d.get("action")
            if act == "settle" and not (0 < float(d.get("settle_pct", 0)) <= 1):
                errs.append(f"claim {d['id']}: settle needs settle_pct in (0,1]")
                continue
            self.decisions[d["id"]] = {"action": act, "settle_pct": float(d.get("settle_pct", 1.0))}
        return {"recorded": len(self.decisions), "errors": errs}

    def t_set_ibnr(self, amount):
        self.ibnr = max(0.0, float(amount))
        return {"ibnr": self.ibnr}

    def t_pay_dividend(self, amount):
        self.dividend = max(0.0, float(amount))
        return {"dividend_requested": self.dividend}

    def t_raise_capital(self, amount):
        self.raise_amt = max(0.0, float(amount))
        return {"capital_requested": self.raise_amt}

    def t_set_reinsurance(self, attachment=None, limit=None, cancel=False):
        self.reins_set = True
        if cancel or attachment is None or limit is None:
            self.reins = None
            return {"reinsurance": None}
        self.reins = {"attachment": float(attachment), "limit": float(limit)}
        return {"reinsurance": self.reins}

    def t_predict_loss_ratio(self, loss_ratio):
        self.prediction = float(loss_ratio)
        return {"recorded": self.prediction}

    def t_write_notes(self, text):
        self.state["notes"] = str(text)[:MAX_NOTES]
        return {"saved_chars": len(self.state["notes"]), "truncated": len(str(text)) > MAX_NOTES}

    def t_board_memo(self, text):
        self.memo = str(text)[:MAX_MEMO]
        return {"recorded": True}

    def t_end_turn(self):
        self.done = True
        return {"ended": True, "quotes_submitted": len(self.quotes), "manual_set": bool(self.state.get("manual")),
                "claims_decided": len(self.decisions), "claims_undecided_will_be_paid": len(self.claim_ids - set(self.decisions)),
                "note": "if some warnings above look wrong it is too late to change them"}

    # ---- assemble the market-facing actions
    def manual_quote(self, a: dict, m: dict):
        base = m["base_rate_on_limit"].get(a["sector"])
        if not base:
            return None
        limit = a["ideal_limit"]
        mod = math.exp(m["autonomy_slope"] * (a["autonomy_signal"] - 0.5) + m["safety_slope"] * (a["safety_signal"] - 0.5))
        mod *= m["red_flag_multiplier"] ** len(a["red_flags"])
        return dict(premium=base * limit * mod, limit=limit, retention=a["default_retention"],
                    cat_carveout=False, upstream_excl=False, misuse_excl=False)

    def actions(self) -> dict:
        quotes = dict(self.quotes)
        m = self.state.get("manual")
        if m:
            for i, a in self.apps.items():
                if i not in quotes and i not in self.declined:
                    q = self.manual_quote(a, m)
                    if q and q["premium"] > 0:
                        quotes[i] = q
        out = dict(quotes=quotes, decisions=self.decisions, ibnr=self.ibnr, dividend=self.dividend or 0.0)
        if self.raise_amt:
            out["raise_capital"] = self.raise_amt
        if self.reins_set:
            out["reinsurance"] = self.reins
        return out
