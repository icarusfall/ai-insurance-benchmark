"""Named, independent RNG streams so exogenous randomness never depends on insurer actions."""
import hashlib

import numpy as np


def stream(seed: int, name: str) -> np.random.Generator:
    h = int.from_bytes(hashlib.blake2b(name.encode(), digest_size=8).digest(), "big")
    return np.random.default_rng(np.random.SeedSequence([int(seed), h]))
