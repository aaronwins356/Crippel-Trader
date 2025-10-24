"""Online trend estimation utilities."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.core import PriceTick


@dataclass
class EmaSlopeEstimator:
    """Compute EMA and its slope incrementally."""

    span: float
    alpha: float
    ema: float = 0.0
    slope: float = 0.0
    initialized: bool = False

    @classmethod
    def with_span(cls, span: float) -> "EmaSlopeEstimator":
        alpha = 2 / (span + 1)
        return cls(span=span, alpha=alpha)

    def update(self, tick: PriceTick) -> tuple[float, float]:
        price = tick.price
        if not self.initialized:
            self.ema = price
            self.slope = 0.0
            self.initialized = True
            return self.ema, self.slope
        prev_ema = self.ema
        self.ema += self.alpha * (price - self.ema)
        self.slope = self.ema - prev_ema
        return self.ema, self.slope
