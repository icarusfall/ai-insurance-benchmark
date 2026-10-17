from .actuary import ActuaryBot
from .probes import PROBES
from .simple import CycleBot, PredatorBot, RandomBot, RecklessBot

REGISTRY = {"actuary": ActuaryBot, "reckless": RecklessBot, "cycle": CycleBot,
            "predator": PredatorBot, "random": RandomBot}
REGISTRY.update({b.name: b for b in PROBES})
PROBE_NAMES = [b.name for b in PROBES]


def make(names):
    return {n: REGISTRY[n]() for n in names}
