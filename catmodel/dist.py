"""Severity of a catastrophe event: a Pareto tail above an event threshold, truncated at the largest possible loss.

An "event" is any occurrence with ground-up harm of at least `xm`. Above it, harm is Pareto with tail index `alpha`
(alpha <= 1 means an infinite mean without the cap), truncated at `cap` (say, a multiple of world GDP). Everything
here is closed form so the browser port can match it exactly.
"""
import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TruncatedPareto:
    xm: float        # event threshold: smallest harm that counts as an event
    alpha: float     # tail index of the survival function, S(x) ~ x^-alpha
    cap: float       # largest possible harm

    def __post_init__(self):
        if not (0 < self.xm < self.cap) or self.alpha <= 0:
            raise ValueError(f"bad severity {self}")

    @property
    def _c(self) -> float:
        return (self.xm / self.cap) ** self.alpha

    def sf(self, x):
        """P(X > x)."""
        x = np.asarray(x, dtype=float)
        c = self._c
        body = ((self.xm / np.maximum(x, self.xm)) ** self.alpha - c) / (1 - c)
        return np.where(x < self.xm, 1.0, np.where(x >= self.cap, 0.0, body))

    def _int_power(self, a: float, b: float) -> float:
        """Integral of (xm/x)^alpha over [a, b], xm <= a <= b."""
        if b <= a:
            return 0.0
        if abs(self.alpha - 1) < 1e-12:
            return self.xm * math.log(b / a)
        k = 1 - self.alpha
        return self.xm ** self.alpha * (b ** k - a ** k) / k

    def layer(self, retention: float, limit: float) -> float:
        """E[min(max(X - retention, 0), limit)] = integral of the survival function over the layer."""
        lo, hi = max(retention, 0.0), max(retention, 0.0) + max(limit, 0.0)
        flat = max(min(hi, self.xm) - lo, 0.0)                  # below xm the survival function is 1
        a, b = max(lo, self.xm), min(hi, self.cap)
        tail = (self._int_power(a, b) - self._c * max(b - a, 0.0)) / (1 - self._c) if b > a else 0.0
        return flat + tail

    def mean(self) -> float:
        return self.layer(0.0, self.cap)

    def quantile(self, p):
        """Inverse CDF: the harm exceeded with probability 1 - p."""
        s = 1 - np.asarray(p, dtype=float)
        c = self._c
        return self.xm * (c + s * (1 - c)) ** (-1.0 / self.alpha)

    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        return self.quantile(rng.random(n))
