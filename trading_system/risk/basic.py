from __future__ import annotations

from trading_system.models import MarketBar, Order, PortfolioState, Position, Side
from trading_system.risk.base import RiskManager


class BasicRiskManager(RiskManager):
    def __init__(
        self,
        max_position_units: float,
        max_notional_per_order: float,
        max_drawdown_pct: float,
        allow_short: bool = True,
        max_exposure_pct: float = 1.0,
        max_bar_range_pct: float = 0.20,
        min_cash_buffer_pct: float = 0.01,
    ):
        self.max_position_units = max_position_units
        self.max_notional_per_order = max_notional_per_order
        self.max_drawdown_pct = max_drawdown_pct
        self.allow_short = allow_short
        self.max_exposure_pct = max(0.05, max_exposure_pct)
        self.max_bar_range_pct = max(0.0, max_bar_range_pct)
        self.min_cash_buffer_pct = max(0.0, min_cash_buffer_pct)

    def validate(
        self,
        order: Order,
        bar: MarketBar,
        portfolio: PortfolioState,
        position: Position,
    ) -> tuple[bool, str]:
        notional = abs(order.size * bar.close)
        if notional > self.max_notional_per_order:
            return False, "order_notional_limit"

        signed = order.size if order.side == Side.BUY else -order.size
        next_units = position.units + signed

        if not self.allow_short and next_units < 0:
            return False, "short_not_allowed"

        if abs(next_units) > self.max_position_units:
            return False, "position_limit"

        drawdown = 0.0
        if portfolio.peak_equity > 0:
            drawdown = (portfolio.peak_equity - portfolio.equity) / portfolio.peak_equity
        if drawdown > self.max_drawdown_pct:
            return False, "max_drawdown_triggered"

        if bar.close > 0:
            bar_range_pct = (bar.high - bar.low) / bar.close
            if bar_range_pct > self.max_bar_range_pct:
                return False, "bar_range_too_high"

        if portfolio.equity > 0:
            projected_exposure = abs(next_units * bar.close) / portfolio.equity
            if projected_exposure > self.max_exposure_pct:
                return False, "exposure_limit"

            projected_cash = portfolio.cash - (signed * bar.close)
            if projected_cash / portfolio.equity < self.min_cash_buffer_pct:
                return False, "cash_buffer_limit"

        return True, "ok"
