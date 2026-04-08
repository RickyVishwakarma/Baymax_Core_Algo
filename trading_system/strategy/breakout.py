from __future__ import annotations

from collections import deque

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy

class BreakoutStrategy(Strategy):
    def __init__(
        self,
        lookback_window: int = 20,
        order_size_units: float = 0.1,
    ):
        if lookback_window < 2:
            raise ValueError("lookback_window must be at least 2")
            
        self.lookback_window = lookback_window
        self.order_size_units = order_size_units
        
        self.high_history: deque[float] = deque(maxlen=lookback_window)
        self.low_history: deque[float] = deque(maxlen=lookback_window)

    def on_bar(self, bar: MarketBar) -> Signal | None:
        if len(self.high_history) < self.lookback_window:
            self.high_history.append(bar.high)
            self.low_history.append(bar.low)
            return None
            
        highest_high = max(self.high_history)
        lowest_low = min(self.low_history)
        
        signal = None
        
        if bar.close > highest_high:
            signal = Signal(
                symbol=bar.symbol,
                side=Side.BUY,
                size=self.order_size_units,
                reason="breakout_up",
                score=1.0,
                confidence=1.0,
                regime="breakout",
            )
        elif bar.close < lowest_low:
            signal = Signal(
                symbol=bar.symbol,
                side=Side.SELL,
                size=self.order_size_units,
                reason="breakout_down",
                score=1.0,
                confidence=1.0,
                regime="breakout",
            )
            
        self.high_history.append(bar.high)
        self.low_history.append(bar.low)
        
        return signal
