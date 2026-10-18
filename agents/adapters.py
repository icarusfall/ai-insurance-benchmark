"""Model adapters. Each turns (system, messages, tools) into a normalised Turn.

Design choices (deliberate, for comparability):
- No sampling parameters; adaptive thinking where the model supports it; effort only if set in models.yaml.
- No refusal fallbacks: a silent switch to another model mid-game would contaminate the result.
  Refusals are surfaced (stop_reason == "refusal") and logged.
- A fresh conversation every quarter, so no thinking-block history editing is ever needed.
"""
import time
from dataclasses import dataclass, field


@dataclass
class Turn:
    raw: list                      # assistant content to echo back unchanged
    text: str
    tool_calls: list               # [(id, name, input_dict)]
    stop_reason: str
    usage: dict                    # input (uncached), output, cache_read, cache_write
    latency: float = 0.0
    request_id: str = ""
    cost: float = None             # provider-reported USD, if any (OpenRouter)


def with_cache_marker(messages: list) -> list:
    """Copy of the conversation with a cache breakpoint on the last block of the newest message.

    Within a quarter every tool round re-sends the whole conversation; with this marker each call reads the
    previous prefix from cache (0.1x input price) and writes only the new part (1.25x). The stored history
    is not modified, so there are never more than two breakpoints (system prompt + newest message)."""
    if not messages:
        return messages
    out = list(messages)
    last = dict(out[-1])
    content = last["content"]
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    else:
        content = [dict(b) if isinstance(b, dict) else b for b in content]
    if content and isinstance(content[-1], dict):
        content[-1] = {**content[-1], "cache_control": {"type": "ephemeral"}}
    last["content"] = content
    out[-1] = last
    return out


class AnthropicAdapter:
    def __init__(self, model: str, cfg: dict, max_retries: int = 4):
        import anthropic
        self.model = model
        self.cfg = cfg
        self.client = anthropic.Anthropic(max_retries=max_retries)

    def complete(self, system: str, messages: list, tools: list, max_tokens: int = 16000) -> Turn:
        kw = dict(model=self.model, max_tokens=max_tokens, tools=tools, messages=with_cache_marker(messages),
                  system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}])
        if self.cfg.get("thinking", "adaptive") == "adaptive":
            kw["thinking"] = {"type": "adaptive"}
        if self.cfg.get("effort"):
            kw["output_config"] = {"effort": self.cfg["effort"]}
        t0 = time.time()
        r = self.client.messages.create(**kw)
        dt = time.time() - t0
        u = r.usage
        usage = dict(input=u.input_tokens or 0, output=u.output_tokens or 0,
                     cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                     cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0)
        calls = [(b.id, b.name, b.input) for b in r.content if b.type == "tool_use"]
        text = "".join(b.text for b in r.content if b.type == "text")
        return Turn(list(r.content), text, calls, r.stop_reason, usage, dt, getattr(r, "_request_id", "") or "")


class ScriptedAdapter:
    """Test double: `policy(system, messages, tools) -> list of (name, input)` or a string (plain text)."""

    def __init__(self, policy):
        self.policy = policy
        self.n = 0

    def complete(self, system: str, messages: list, tools: list, max_tokens: int = 16000) -> Turn:
        out = self.policy(system, messages, tools)
        self.n += 1
        usage = dict(input=len(system) // 4 + sum(len(str(m)) for m in messages) // 4, output=50,
                     cache_read=0, cache_write=0)
        if isinstance(out, str):
            return Turn([{"type": "text", "text": out}], out, [], "end_turn", usage)
        calls = [(f"toolu_{self.n}_{i}", name, inp) for i, (name, inp) in enumerate(out)]
        raw = [{"type": "tool_use", "id": cid, "name": name, "input": inp} for cid, name, inp in calls]
        return Turn(raw, "", calls, "tool_use", usage)
