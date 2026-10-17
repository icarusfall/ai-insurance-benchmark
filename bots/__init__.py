from .actuary import ActuaryBot
from .simple import CycleBot, PredatorBot, RandomBot, RecklessBot

REGISTRY = {"actuary": ActuaryBot, "reckless": RecklessBot, "cycle": CycleBot,
            "predator": PredatorBot, "random": RandomBot}


def make(names):
    return {n: REGISTRY[n]() for n in names}
