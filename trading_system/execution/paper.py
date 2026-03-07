from __future__ import annotations

from trading_system.models import Fill, MarketBar, Order, Side
from trading_system.execution.base import ExecutionHandler


class PaperExecutionHandler(ExecutionHandler):
    def __init__(self, fee_bps: float, slippage_bps: float):
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

    def execute(self, order: Order, bar: MarketBar) -> Fill:
        sign = 1 if order.side == Side.BUY else -1
        slip_multiplier = 1 + sign * (self.slippage_bps / 10_000)
        fill_price = bar.close * slip_multiplier
        fee_paid = abs(order.size * fill_price) * (self.fee_bps / 10_000)
        return Fill(
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            fill_price=fill_price,
            fee_paid=fee_paid,
        )
