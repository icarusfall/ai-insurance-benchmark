import json

import agents.adapters_gemini as G
import agents.adapters_oai as O
from agents.tools import TOOLS


def test_gemini_schema_is_clean():
    bad = {"additionalProperties", "exclusiveMinimum", "$schema"}

    def walk(x):
        if isinstance(x, dict):
            assert not (bad & set(x)), x
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(G.to_declarations(TOOLS))
    names = [d["name"] for d in G.to_declarations(TOOLS)[0]["functionDeclarations"]]
    assert names == [t["name"] for t in TOOLS]


def test_openai_roundtrip(monkeypatch):
    seen = {}

    def fake_post(url, headers, body, **kw):
        seen["body"] = body
        return {"id": "chatcmpl-1", "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None, "refusal": None, "annotations": [],
            "tool_calls": [{"id": "call_1", "type": "function",
                            "function": {"name": "get_applicants", "arguments": '{"limit": 5}'}}]}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 300, "prompt_tokens_details": {"cached_tokens": 400},
                      "completion_tokens_details": {"reasoning_tokens": 250}}}
    monkeypatch.setattr(O, "post_json", fake_post)
    ad = O.OpenAIChatAdapter("gpt-x", {}, "https://example.invalid/v1", "sk-test-not-real")
    t = ad.complete("SYS", [{"role": "user", "content": "hi"}], TOOLS, 500)
    assert t.stop_reason == "tool_use" and t.tool_calls == [("call_1", "get_applicants", {"limit": 5})]
    assert t.usage["input"] == 600 and t.usage["cache_read"] == 400 and t.usage["output"] == 300 and t.usage["reasoning"] == 250
    assert seen["body"]["max_completion_tokens"] == 500 and seen["body"]["messages"][0]["role"] == "system"
    # next call: assistant echoed back verbatim, tool result becomes a tool message
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": t.raw},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "{}"}]}]
    conv = O.to_messages("SYS", msgs)
    assert [m["role"] for m in conv] == ["system", "user", "assistant", "tool"]
    assert conv[2]["tool_calls"][0]["id"] == "call_1" and "annotations" not in conv[2]
    assert conv[3]["tool_call_id"] == "call_1"


def test_openrouter_uses_reported_cost(monkeypatch):
    monkeypatch.setattr(O, "post_json", lambda *a, **k: {"id": "x", "choices": [{"finish_reason": "stop", "message": {
        "role": "assistant", "content": "ok"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.00042}})
    t = O.OpenAIChatAdapter("m", {}, "https://example.invalid", "sk-or-test-not-real", openrouter=True).complete("s", [{"role": "user", "content": "x"}], TOOLS)
    assert t.cost == 0.00042 and t.stop_reason == "end_turn"


def test_gemini_roundtrip(monkeypatch):
    def fake_post(url, headers, body, **kw):
        assert "x-goog-api-key" in headers and "key=" not in url
        return {"candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": [
            {"text": "thinking...", "thought": True},
            {"functionCall": {"name": "get_applicants", "args": {"limit": 5}}, "thoughtSignature": "SIG"}]}}],
            "usageMetadata": {"promptTokenCount": 900, "cachedContentTokenCount": 300, "candidatesTokenCount": 40,
                              "thoughtsTokenCount": 200}}
    monkeypatch.setattr(G, "post_json", fake_post)
    ad = G.GeminiAdapter("gem-x", {}, "AIzaFAKEKEYFORTESTS")
    t = ad.complete("SYS", [{"role": "user", "content": "hi"}], TOOLS, 500)
    assert t.stop_reason == "tool_use" and t.tool_calls[0][1] == "get_applicants"
    assert t.usage["input"] == 600 and t.usage["output"] == 240 and t.usage["cache_read"] == 300
    cid = t.tool_calls[0][0]
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": t.raw},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": cid, "content": '{"total": 3}'}]}]
    conv = G.to_contents(msgs)
    assert conv[1]["parts"][1]["thoughtSignature"] == "SIG"            # signature preserved
    fr = conv[2]["parts"][0]["functionResponse"]
    assert fr["name"] == "get_applicants" and fr["response"] == {"result": {"total": 3}}


def test_blocked_gemini_is_refusal(monkeypatch):
    monkeypatch.setattr(G, "post_json", lambda *a, **k: {"promptFeedback": {"blockReason": "SAFETY"}, "usageMetadata": {}})
    t = G.GeminiAdapter("g", {}, "AIzaFAKEKEYFORTESTS").complete("s", [{"role": "user", "content": "x"}], TOOLS)
    assert t.stop_reason == "refusal"


def test_openai_responses_roundtrip(monkeypatch):
    import agents.adapters_oai_responses as R

    def fake_post(url, headers, body, **kw):
        assert body["store"] is False and "reasoning.encrypted_content" in body["include"]
        assert body["tools"][0]["type"] == "function" and "function" not in body["tools"][0]
        return {"id": "resp_1", "status": "completed", "output": [
            {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "ENC"},
            {"type": "function_call", "call_id": "call_9", "name": "get_applicants", "arguments": '{"limit": 3}'}],
            "usage": {"input_tokens": 1000, "output_tokens": 500, "input_tokens_details": {"cached_tokens": 200},
                      "output_tokens_details": {"reasoning_tokens": 420}}}
    monkeypatch.setattr(R, "post_json", fake_post)
    ad = R.OpenAIResponsesAdapter("m", {}, "sk-test-not-real")
    t = ad.complete("SYS", [{"role": "user", "content": "hi"}], TOOLS, 500)
    assert t.tool_calls == [("call_9", "get_applicants", {"limit": 3})] and t.stop_reason == "tool_use"
    assert t.usage == dict(input=800, output=500, cache_read=200, cache_write=0, reasoning=420)
    inp = R.to_input([{"role": "user", "content": "hi"}, {"role": "assistant", "content": t.raw},
                      {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_9", "content": "{}"}]}])
    assert [i.get("type", i.get("role")) for i in inp] == ["user", "reasoning", "function_call", "function_call_output"]
    assert inp[1]["encrypted_content"] == "ENC"


def test_nonretryable_errors_are_not_swallowed(monkeypatch):
    import requests

    import agents.http as H

    class Resp:
        status_code, text, headers = 400, "bad request", {}
    monkeypatch.setattr(H.requests, "post", lambda *a, **k: Resp())
    try:
        H.post_json("https://example.invalid", {}, {})
        assert False
    except H.AdapterError as e:
        assert e.retryable is False
