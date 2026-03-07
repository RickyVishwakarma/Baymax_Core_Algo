from __future__ import annotations

from abc import ABC, abstractmethod

from trading_system.models import MarketBar, Signal


class Strategy(ABC):
    @abstractmethod
    def on_bar(self, bar: MarketBar) -> Signal | None:
        raise NotImplementedError
