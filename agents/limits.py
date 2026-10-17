"""Per-provider concurrency caps, shared by every adapter in the process (rate limits are per account)."""
import threading

LIMITS = {"gemini": 2, "openai": 6, "openrouter": 6, "anthropic": 6}
_sems = {}
_lock = threading.Lock()


def semaphore(provider: str) -> threading.Semaphore:
    with _lock:
        if provider not in _sems:
            _sems[provider] = threading.Semaphore(LIMITS.get(provider, 4))
        return _sems[provider]


class Limited:
    """Wrap an adapter so at most N calls per provider are in flight at once."""

    def __init__(self, adapter, provider: str):
        self._a, self._sem = adapter, semaphore(provider)

    def complete(self, *args, **kw):
        with self._sem:
            return self._a.complete(*args, **kw)
