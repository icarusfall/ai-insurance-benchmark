"""Model roster, price table and per-call cost. Prices are snapshotted into every call-log line."""
import os

import yaml

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models.yaml")


def load_models(path: str = _PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["models"]


def prices_for(model: str, models: dict = None) -> dict:
    cfg = (models or load_models())[model]
    i = float(cfg["input"])
    return dict(input=i, output=float(cfg["output"]),
                cache_read=float(cfg.get("cache_read", 0.1 * i)),
                cache_write=float(cfg.get("cache_write", 1.25 * i)))


def call_cost(prices: dict, usage: dict) -> float:
    """usage: input (uncached), output, cache_read, cache_write token counts."""
    return (usage.get("input", 0) * prices["input"] + usage.get("output", 0) * prices["output"]
            + usage.get("cache_read", 0) * prices["cache_read"]
            + usage.get("cache_write", 0) * prices["cache_write"]) / 1e6


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Spend cap shared across calls (thread-safe). A child budget also charges its parent."""

    def __init__(self, max_usd: float, parent: "Budget" = None):
        import threading
        self.max_usd = max_usd
        self.spent = 0.0
        self.parent = parent
        self._lock = threading.Lock()

    def add(self, usd: float):
        with self._lock:
            self.spent += usd
            over = self.spent > self.max_usd
        if self.parent:
            self.parent.add(usd)
        if over:
            raise BudgetExceeded(f"budget ${self.max_usd:.2f} exceeded (spent ${self.spent:.2f})")
