from __future__ import annotations

from abc import ABC, abstractmethod

from trading_system.models import MarketBar, Order, PortfolioState, Position


class RiskManager(ABC):
    @abstractmethod
    def validate(
        self,
        order: Order,
        bar: MarketBar,
        portfolio: PortfolioState,
        position: Position,
    ) -> tuple[bool, str]:
        raise NotImplementedError
