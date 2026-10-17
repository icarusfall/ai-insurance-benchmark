"""HTTP helper with retry/backoff. Keys travel only in headers and are scrubbed from any error text."""
import re
import time

import requests


class AdapterError(RuntimeError):
    pass


def scrub(s: str) -> str:
    return re.sub(r"(sk-[A-Za-z0-9_\-]{8,}|AIza[A-Za-z0-9_\-]{8,}|Bearer\s+\S+)", "***", str(s))[:500]


def post_json(url: str, headers: dict, body: dict, tries: int = 5, timeout: int = 300) -> dict:
    last = ""
    for attempt in range(tries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            last = f"{type(e).__name__}"
            time.sleep(min(2 ** attempt, 30))
            continue
        if r.status_code == 200:
            return r.json()
        last = f"HTTP {r.status_code}: {scrub(r.text)}"
        if r.status_code in (408, 409, 429, 500, 502, 503, 504, 529):
            try:
                wait = float(r.headers.get("retry-after", 0))
            except ValueError:
                wait = 0
            time.sleep(min(max(wait, 2 ** attempt), 60))
            continue
        break
    raise AdapterError(last)
