from __future__ import annotations

import logging

from trading_system.data.feed import MarketDataFeed
from trading_system.execution.base import ExecutionHandler
from trading_system.models import Order
from trading_system.portfolio.manager import PortfolioManager
from trading_system.risk.base import RiskManager
from trading_system.strategy.base import Strategy


logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(
        self,
        data_feed: MarketDataFeed,
        strategy: Strategy,
        risk_manager: RiskManager,
        execution: ExecutionHandler,
        portfolio: PortfolioManager,
        on_bar_callback=None,
        on_fill_callback=None,
    ):
        self.data_feed = data_feed
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.execution = execution
        self.portfolio = portfolio
        self.on_bar_callback = on_bar_callback
        self.on_fill_callback = on_fill_callback

    def run(self) -> None:
        for bar in self.data_feed.stream():
            self.portfolio.mark_to_market(bar)
            if self.on_bar_callback is not None:
                self.on_bar_callback(bar, self.portfolio)
            signal = self.strategy.on_bar(bar)
            if not signal:
                continue

            logger.info(
                "signal symbol=%s side=%s size=%.6f score=%.3f confidence=%.3f regime=%s reason=%s",
                signal.symbol,
                signal.side.value,
                signal.size,
                signal.score,
                signal.confidence,
                signal.regime,
                signal.reason,
            )

            order = Order(symbol=signal.symbol, side=signal.side, size=signal.size)
            is_valid, reason = self.risk_manager.validate(order, bar, self.portfolio.state, self.portfolio.position)
            if not is_valid:
                logger.info("risk_reject symbol=%s side=%s size=%.6f reason=%s", order.symbol, order.side.value, order.size, reason)
                continue

            fill = self.execution.execute(order, bar)
            self.portfolio.apply_fill(fill)
            self.portfolio.mark_to_market(bar)
            if self.on_fill_callback is not None:
                self.on_fill_callback(bar, fill, signal, self.portfolio)
            logger.info(
                "fill symbol=%s side=%s size=%.6f price=%.2f fee=%.4f equity=%.2f",
                fill.symbol,
                fill.side.value,
                fill.size,
                fill.fill_price,
                fill.fee_paid,
                self.portfolio.state.equity,
            )
