"""Cheap connectivity check for each configured provider key. Sends ~10-token prompts; never prints keys."""
import os
import re

import requests

from agents.env import load_env

PROMPT = "Reply with exactly: OK"


def scrub(s, keys):
    s = str(s)
    for k in keys:
        if k:
            s = s.replace(k, "***")
    return re.sub(r"(sk-|AIza)[A-Za-z0-9_\-]{8,}", "***", s)[:300]


def pick(ids, prefs):
    for p in prefs:
        c = sorted(i for i in ids if p in i and not any(x in i for x in ("preview", "audio", "realtime", "image", "tts", "transcribe", "search", "embedding", "vision", "live")))
        if c:
            return c[-1]
    return None


def main():
    load_env()
    keys = [os.environ.get(k) for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY")]

    # --- OpenAI
    k = os.environ.get("OPENAI_API_KEY")
    print("OpenAI:", end=" ")
    if not k:
        print("no key")
    else:
        try:
            h = {"Authorization": f"Bearer {k}"}
            r = requests.get("https://api.openai.com/v1/models", headers=h, timeout=30)
            if r.status_code != 200:
                print(f"list models HTTP {r.status_code}: {scrub(r.text, keys)}")
            else:
                ids = [m["id"] for m in r.json()["data"]]
                model = pick(ids, ["gpt-5-nano", "gpt-5-mini", "gpt-4.1-nano", "gpt-4o-mini", "nano", "mini"])
                r = requests.post("https://api.openai.com/v1/chat/completions", headers=h, timeout=60, json={
                    "model": model, "messages": [{"role": "user", "content": PROMPT}], "max_completion_tokens": 300})
                if r.status_code == 200:
                    j = r.json()
                    print(f"OK  model={model} reply={j['choices'][0]['message']['content']!r} usage={j['usage']}")
                else:
                    print(f"model={model} HTTP {r.status_code}: {scrub(r.text, keys)}")
        except Exception as e:
            print("error", scrub(e, keys))

    # --- Gemini
    k = os.environ.get("GEMINI_API_KEY")
    print("Gemini:", end=" ")
    if not k:
        print("no key")
    else:
        try:
            h = {"x-goog-api-key": k}
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers=h, timeout=30)
            if r.status_code != 200:
                print(f"list models HTTP {r.status_code}: {scrub(r.text, keys)}")
            else:
                ids = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                       if "generateContent" in m.get("supportedGenerationMethods", [])]
                model = pick(ids, ["flash-lite", "flash"])
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                  headers=h, timeout=60, json={"contents": [{"parts": [{"text": PROMPT}]}],
                                                              "generationConfig": {"maxOutputTokens": 300}})
                if r.status_code == 200:
                    j = r.json()
                    txt = "".join(p.get("text", "") for p in j["candidates"][0]["content"].get("parts", []))
                    print(f"OK  model={model} reply={txt!r} usage={j.get('usageMetadata')}")
                else:
                    print(f"model={model} HTTP {r.status_code}: {scrub(r.text, keys)}")
        except Exception as e:
            print("error", scrub(e, keys))

    # --- OpenRouter
    k = os.environ.get("OPENROUTER_API_KEY")
    print("OpenRouter:", end=" ")
    if not k:
        print("no key")
    else:
        try:
            h = {"Authorization": f"Bearer {k}"}
            r = requests.get("https://openrouter.ai/api/v1/auth/key", headers=h, timeout=30)
            info = r.json().get("data", {}) if r.status_code == 200 else scrub(r.text, keys)
            print("key info:", {x: info[x] for x in ("limit", "usage", "limit_remaining", "is_free_tier") if x in info}
                  if isinstance(info, dict) else f"HTTP {r.status_code} {info}")
            ms = requests.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
            cheap = [(float(m["pricing"]["prompt"]) + float(m["pricing"]["completion"]), m["id"]) for m in ms
                     if m.get("pricing") and float(m["pricing"].get("prompt", 0)) > 0
                     and any(s in m["id"] for s in ("openai/gpt-5-nano", "openai/gpt-5-mini", "google/gemini-2.5-flash-lite",
                                                    "google/gemini-3", "deepseek/", "qwen/"))]
            cheap.sort()
            model = cheap[0][1]
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=h, timeout=60, json={
                "model": model, "max_tokens": 300, "messages": [{"role": "user", "content": PROMPT}]})
            if r.status_code == 200:
                j = r.json()
                print(f"  OK  model={model} reply={j['choices'][0]['message']['content']!r} usage={j.get('usage')}")
            else:
                print(f"  model={model} HTTP {r.status_code}: {scrub(r.text, keys)}")
        except Exception as e:
            print("error", scrub(e, keys))


if __name__ == "__main__":
    main()
