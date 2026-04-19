from __future__ import annotations

from abc import ABC, abstractmethod

from trading_system.models import MarketBar, Signal


class Strategy(ABC):
    @abstractmethod
    def on_bar(self, bar: MarketBar) -> Signal | None:
        raise NotImplementedError

    def is_bullish(self) -> bool | None:
        """Returns True if the macro trend is bullish, False if bearish, None if neutral/unknown."""
        return None
