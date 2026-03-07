from __future__ import annotations

from abc import ABC, abstractmethod

from trading_system.models import Fill, MarketBar, Order


class ExecutionHandler(ABC):
    @abstractmethod
    def execute(self, order: Order, bar: MarketBar) -> Fill:
        raise NotImplementedError
