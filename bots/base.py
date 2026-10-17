"""Bot interface. Views and actions are plain dicts (see engine/market.py)."""
from collections import defaultdict


class Bot:
    name = "base"

    def reset(self, seed: int, seat: int):
        self.seed = seed
        self.seat = seat

    def act(self, view: dict) -> dict:
        return {"quotes": {}, "decisions": {}, "ibnr": None, "dividend": 0.0}

    def on_bound(self, client: int, q: int, info: dict):
        pass

    def on_quarter_end(self, q: int):
        pass


def nested_float():
    return defaultdict(float)
