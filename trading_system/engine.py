from __future__ import annotations

import logging

from trading_system.data.feed import MarketDataFeed
from trading_system.execution.base import ExecutionHandler
from trading_system.models import Order, Signal, Side
from trading_system.ml.regime import MultiSymbolRegimeClassifier
from trading_system.portfolio.manager import PortfolioManager
from trading_system.risk.base import RiskManager
from trading_system.strategy.base import Strategy


logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(
        self,
        data_feed: MarketDataFeed,
        strategy_factory,
        risk_manager: RiskManager,
        execution: ExecutionHandler,
        portfolio: PortfolioManager,
        trailing_stop_pct: float = 0.0,
        regime_classifier: MultiSymbolRegimeClassifier | None = None,
        on_bar_callback=None,
        on_fill_callback=None,
    ):
        self.data_feed = data_feed
        self.strategy_factory = strategy_factory
        self.strategies: dict[str, Strategy] = {}
        self.risk_manager = risk_manager
        self.execution = execution
        self.portfolio = portfolio
        self.trailing_stop_pct = trailing_stop_pct
        self.regime_classifier = regime_classifier
        self.on_bar_callback = on_bar_callback
        self.on_fill_callback = on_fill_callback

    def run(self) -> None:
        for bar in self.data_feed.stream():
            self.portfolio.mark_to_market(bar)
            if self.on_bar_callback is not None:
                self.on_bar_callback(bar, self.portfolio)
                
            if bar.symbol not in self.strategies:
                self.strategies[bar.symbol] = self.strategy_factory()
            strategy = self.strategies[bar.symbol]
            
            signal = None
            position = self.portfolio.get_position(bar.symbol)
            
            # Trailing Stop-Loss Override
            if self.trailing_stop_pct > 0.0 and position.units != 0:
                if position.units > 0:
                    drop_pct = (position.peak_price - bar.close) / position.peak_price
                    if drop_pct >= self.trailing_stop_pct:
                        logger.warning("trailing_stop symbol=%s side=SELL drop=%.4f", bar.symbol, drop_pct)
                        signal = Signal(symbol=bar.symbol, side=Side.SELL, size=position.units, reason="trailing_stop", score=1.0, confidence=1.0, regime="risk")
                elif position.units < 0:
                    rise_pct = (bar.close - position.peak_price) / position.peak_price
                    if rise_pct >= self.trailing_stop_pct:
                        logger.warning("trailing_stop symbol=%s side=BUY rise=%.4f", bar.symbol, rise_pct)
                        signal = Signal(symbol=bar.symbol, side=Side.BUY, size=abs(position.units), reason="trailing_stop", score=1.0, confidence=1.0, regime="risk")
            
            # Standard strategy evaluation
            if signal is None:
                signal = strategy.on_bar(bar)

            if not signal:
                continue

            # ── AI Regime Gate ────────────────────────────────────────────
            # Only fires on strategy signals (not trailing-stop overrides).
            # Trailing stops always bypass the regime filter.
            if self.regime_classifier is not None and signal.reason != "trailing_stop":
                blocked, regime_result = self.regime_classifier.should_block(bar)
                logger.debug(
                    "regime symbol=%s regime=%s score=%.3f ci=%s adx=%s",
                    bar.symbol,
                    regime_result.regime,
                    regime_result.score,
                    f"{regime_result.choppiness_index:.1f}" if regime_result.choppiness_index else "n/a",
                    f"{regime_result.adx:.1f}" if regime_result.adx else "n/a",
                )
                if blocked:
                    logger.info(
                        "regime_block symbol=%s regime=%s score=%.3f reason=%s",
                        bar.symbol, regime_result.regime, regime_result.score, signal.reason,
                    )
                    continue
            elif self.regime_classifier is not None and signal.reason != "trailing_stop":
                # Update classifier state even when not blocking
                self.regime_classifier.update(bar)
            # ─────────────────────────────────────────────────────────────

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
            is_valid, reason = self.risk_manager.validate(order, bar, self.portfolio.state, position)
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
