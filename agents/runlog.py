"""Append-only run logs: calls.jsonl (tokens, cost, latency) and game.jsonl (decisions, notes, memos)."""
import json
import os
import time


class RunLog:
    def __init__(self, root: str, run_id: str, meta: dict):
        self.dir = os.path.join(root, run_id)
        os.makedirs(self.dir, exist_ok=True)
        self.run_id = run_id
        with open(os.path.join(self.dir, "manifest.json"), "w") as f:
            json.dump(dict(run_id=run_id, started=time.time(), **meta), f, indent=2, default=str)

    def _write(self, name: str, obj: dict):
        with open(os.path.join(self.dir, name), "a") as f:
            f.write(json.dumps(obj, default=str) + "\n")

    def call(self, **kw):
        self._write("calls.jsonl", kw)

    def game(self, **kw):
        self._write("game.jsonl", kw)
