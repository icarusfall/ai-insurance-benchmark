"""OpenAI Responses API adapter (stateless: store=false, encrypted reasoning passed back verbatim).

Newer OpenAI models reject function tools with reasoning on Chat Completions, so direct OpenAI uses this.
"""
import json
import time

from .adapters import Turn
from .http import post_json


def to_tools(tools: list) -> list:
    return [{"type": "function", "name": t["name"], "description": t["description"],
             "parameters": t["input_schema"]} for t in tools]


def to_input(messages: list) -> list:
    out = []
    for m in messages:
        c = m["content"]
        if m["role"] == "user":
            if isinstance(c, str):
                out.append({"role": "user", "content": c})
            else:
                for b in c:
                    out.append({"type": "function_call_output", "call_id": b["tool_use_id"], "output": b["content"]})
        else:
            for b in c:
                if isinstance(b, dict) and b.get("type") == "_openai_items":
                    out.extend(b["items"])
    return out


class OpenAIResponsesAdapter:
    def __init__(self, model: str, cfg: dict, api_key: str, base_url: str = "https://api.openai.com/v1"):
        if not api_key:
            raise RuntimeError("missing OPENAI_API_KEY")
        self.model, self.cfg, self.url = model, cfg, base_url.rstrip("/") + "/responses"
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def complete(self, system: str, messages: list, tools: list, max_tokens: int = 16000) -> Turn:
        body = {"model": self.model, "instructions": system, "input": to_input(messages), "tools": to_tools(tools),
                "max_output_tokens": max_tokens, "store": False, "include": ["reasoning.encrypted_content"]}
        if self.cfg.get("effort"):
            body["reasoning"] = {"effort": self.cfg["effort"]}
        t0 = time.time()
        j = post_json(self.url, self.headers, body)
        dt = time.time() - t0
        calls, text, refused = [], "", False
        for it in j.get("output", []):
            if it.get("type") == "function_call":
                try:
                    args = json.loads(it.get("arguments") or "{}")
                    if not isinstance(args, dict):
                        raise ValueError
                except ValueError:
                    args = {"_unparseable_arguments": str(it.get("arguments"))[:200]}
                calls.append((it["call_id"], it["name"], args))
            elif it.get("type") == "message":
                for c in it.get("content", []):
                    if c.get("type") == "output_text":
                        text += c.get("text", "")
                    elif c.get("type") == "refusal":
                        refused = True
        inc = (j.get("incomplete_details") or {}).get("reason")
        if refused or inc == "content_filter":
            stop = "refusal"
        elif calls:
            stop = "tool_use"
        elif inc == "max_output_tokens":
            stop = "max_tokens"
        else:
            stop = "end_turn"
        u = j.get("usage") or {}
        cached = (u.get("input_tokens_details") or {}).get("cached_tokens") or 0
        usage = dict(input=max((u.get("input_tokens") or 0) - cached, 0), output=u.get("output_tokens") or 0,
                     cache_read=cached, cache_write=0,
                     reasoning=(u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
        return Turn([{"type": "_openai_items", "items": j.get("output", [])}], text, calls, stop, usage, dt, j.get("id", ""))
