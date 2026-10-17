"""Gemini adapter (native generateContent API). Native content is passed back verbatim so thought
signatures on function calls survive within a quarter."""
import json
import time

from .adapters import Turn
from .http import post_json

KEEP = {"type", "description", "properties", "required", "items", "enum", "minimum", "maximum", "format", "nullable"}


def sanitize(schema):
    """Gemini accepts an OpenAPI subset; drop JSON-Schema keywords it rejects."""
    if isinstance(schema, dict):
        out = {k: sanitize(v) for k, v in schema.items() if k in KEEP or k == "properties"}
        if "properties" in out and isinstance(schema.get("properties"), dict):
            out["properties"] = {k: sanitize(v) for k, v in schema["properties"].items()}
        return out
    if isinstance(schema, list):
        return [sanitize(x) for x in schema]
    return schema


def to_declarations(tools: list) -> list:
    decls = []
    for t in tools:
        params = sanitize(t["input_schema"])
        d = {"name": t["name"], "description": t["description"]}
        if params.get("properties"):
            d["parameters"] = params
        decls.append(d)
    return [{"functionDeclarations": decls}]


def to_contents(messages: list) -> list:
    out, names = [], {}
    for m in messages:
        c = m["content"]
        if m["role"] == "user":
            if isinstance(c, str):
                out.append({"role": "user", "parts": [{"text": c}]})
            else:
                parts = []
                for b in c:
                    try:
                        payload = json.loads(b["content"])
                    except (ValueError, TypeError):
                        payload = b["content"]
                    fr = {"name": names.get(b["tool_use_id"], "unknown"),
                          "response": {"result": payload}}
                    if b["tool_use_id"].startswith("gem_id:"):
                        fr["id"] = b["tool_use_id"][len("gem_id:"):]
                    parts.append({"functionResponse": fr})
                out.append({"role": "user", "parts": parts})
        else:
            nat = [b for b in c if isinstance(b, dict) and b.get("type") == "_gemini_content"]
            if nat:
                out.append(nat[0]["content"])
                names.update(nat[0]["names"])
            else:
                out.append({"role": "model", "parts": [{"text": ""}]})
    return out


class GeminiAdapter:
    def __init__(self, model: str, cfg: dict, api_key: str):
        if not api_key:
            raise RuntimeError("missing GEMINI_API_KEY")
        self.model, self.cfg = model, cfg
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        self.headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        self.n = 0

    def complete(self, system: str, messages: list, tools: list, max_tokens: int = 16000) -> Turn:
        gen = {"maxOutputTokens": max_tokens}
        if self.cfg.get("thinking_config"):
            gen["thinkingConfig"] = self.cfg["thinking_config"]
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": to_contents(messages),
                "tools": to_declarations(tools), "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
                "generationConfig": gen}
        t0 = time.time()
        j = post_json(self.url, self.headers, body)
        dt = time.time() - t0
        u = j.get("usageMetadata") or {}
        cached = u.get("cachedContentTokenCount") or 0
        usage = dict(input=max((u.get("promptTokenCount") or 0) - cached, 0),
                     output=(u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0),
                     cache_read=cached, cache_write=0, reasoning=u.get("thoughtsTokenCount") or 0)
        cands = j.get("candidates") or []
        if not cands:
            return Turn([], "", [], "refusal", usage, dt, "")
        cand = cands[0]
        content = cand.get("content") or {"role": "model", "parts": []}
        content.setdefault("role", "model")
        calls, names, text = [], {}, ""
        for p in content.get("parts", []):
            if "functionCall" in p:
                fc = p["functionCall"]
                self.n += 1
                cid = f"gem_id:{fc['id']}" if fc.get("id") else f"gem_{self.n}"
                calls.append((cid, fc["name"], fc.get("args") or {}))
                names[cid] = fc["name"]
            elif p.get("text") and not p.get("thought"):
                text += p["text"]
        fin = cand.get("finishReason", "")
        if fin in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"):
            stop = "refusal"
        elif calls:
            stop = "tool_use"
        elif fin == "MAX_TOKENS":
            stop = "max_tokens"
        else:
            stop = "end_turn"
        return Turn([{"type": "_gemini_content", "content": content, "names": names}], text, calls, stop, usage, dt, "")
