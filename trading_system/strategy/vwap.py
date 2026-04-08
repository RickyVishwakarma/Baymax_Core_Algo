from __future__ import annotations

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy

class VWAPStrategy(Strategy):
    """
    Volume-Weighted Average Price (VWAP) Strategy.
    Resets the VWAP calculation at the start of each new trading session (day).
    Issues a Buy signal when price crosses above VWAP, and a Sell when crossing below.
    """
    def __init__(
        self,
        order_size_units: float = 0.1,
    ):
        self.order_size_units = order_size_units
        self.cumulative_tp_vol: float = 0.0
        self.cumulative_vol: float = 0.0
        self.current_date = None
        self.vwap: float | None = None
        self.prev_close: float | None = None

    def on_bar(self, bar: MarketBar) -> Signal | None:
        bar_date = bar.ts.date()
        
        # Reset VWAP at the start of a new day session
        if self.current_date != bar_date:
            self.current_date = bar_date
            self.cumulative_tp_vol = 0.0
            self.cumulative_vol = 0.0
            self.vwap = None
            
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        self.cumulative_tp_vol += typical_price * bar.volume
        self.cumulative_vol += bar.volume
        
        if self.cumulative_vol > 0:
            current_vwap = self.cumulative_tp_vol / self.cumulative_vol
        else:
            current_vwap = typical_price

        signal = None
        if self.vwap is not None and self.prev_close is not None:
            # Check price cross over VWAP
            if self.prev_close < self.vwap and bar.close > current_vwap:
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.BUY,
                    size=self.order_size_units,
                    reason="vwap_cross_up",
                    score=1.0,
                    confidence=1.0,
                    regime="vwap"
                )
            elif self.prev_close > self.vwap and bar.close < current_vwap:
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.SELL,
                    size=self.order_size_units,
                    reason="vwap_cross_down",
                    score=1.0,
                    confidence=1.0,
                    regime="vwap"
                )
                
        self.vwap = current_vwap
        self.prev_close = bar.close
        return signal
