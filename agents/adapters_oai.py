"""OpenAI-style Chat Completions adapter. Serves OpenAI directly and OpenRouter (same wire format).

Conversation state is kept in the Anthropic-shaped message list the bot builds; this adapter converts it
to chat-completions form on every call. The assistant message is passed back verbatim (so provider
extras such as OpenRouter's reasoning details survive within a quarter).
"""
import json
import time

from .adapters import Turn
from .http import post_json


def to_tools(tools: list) -> list:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}} for t in tools]


def to_messages(system: str, messages: list) -> list:
    out = [{"role": "system", "content": system}]
    for m in messages:
        c = m["content"]
        if m["role"] == "user":
            if isinstance(c, str):
                out.append({"role": "user", "content": c})
            else:
                for b in c:
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]})
        else:
            nat = [b for b in c if isinstance(b, dict) and b.get("type") == "_openai_message"]
            out.append(nat[0]["message"] if nat else {"role": "assistant", "content": ""})
    return out


class OpenAIChatAdapter:
    def __init__(self, model: str, cfg: dict, base_url: str, api_key: str, openrouter: bool = False):
        self.model, self.cfg, self.base_url, self.openrouter = model, cfg, base_url.rstrip("/"), openrouter
        if not api_key:
            raise RuntimeError("missing API key for " + base_url)
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if openrouter:
            self.headers.update({"X-Title": "ai-insurance-benchmark"})

    def complete(self, system: str, messages: list, tools: list, max_tokens: int = 16000) -> Turn:
        body = {"model": self.model, "messages": to_messages(system, messages), "tools": to_tools(tools)}
        if self.openrouter:
            body["max_tokens"] = max_tokens
            if self.cfg.get("effort"):
                body["reasoning"] = {"effort": self.cfg["effort"]}
        else:
            body["max_completion_tokens"] = max_tokens
            if self.cfg.get("effort"):
                body["reasoning_effort"] = self.cfg["effort"]
        t0 = time.time()
        j = post_json(f"{self.base_url}/chat/completions", self.headers, body)
        dt = time.time() - t0
        choice = j["choices"][0]
        msg = choice["message"]
        calls = []
        for tc in msg.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
                if not isinstance(args, dict):
                    raise ValueError
            except ValueError:
                args = {"_unparseable_arguments": str(tc["function"]["arguments"])[:200]}
            calls.append((tc["id"], tc["function"]["name"], args))
        finish = choice.get("finish_reason")
        if msg.get("refusal") or finish == "content_filter":
            stop = "refusal"
        elif calls:
            stop = "tool_use"
        elif finish == "length":
            stop = "max_tokens"
        else:
            stop = "end_turn"
        u = j.get("usage") or {}
        det = u.get("prompt_tokens_details") or {}
        cached = det.get("cached_tokens") or 0
        usage = dict(input=max((u.get("prompt_tokens") or 0) - cached - (det.get("cache_write_tokens") or 0), 0),
                     output=u.get("completion_tokens") or 0, cache_read=cached,
                     cache_write=det.get("cache_write_tokens") or 0,
                     reasoning=(u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
        native = {k: v for k, v in msg.items() if not (k in ("annotations", "audio", "refusal") and not v)}
        return Turn([{"type": "_openai_message", "message": native}], msg.get("content") or "", calls, stop, usage, dt,
                    j.get("id", ""), cost=u.get("cost") if self.openrouter else None)
