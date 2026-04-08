from __future__ import annotations

from collections import deque

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy

class MeanReversionStrategy(Strategy):
    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        order_size_units: float = 0.1,
    ):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.order_size_units = order_size_units
        
        # Keep history to compute RSI
        self.close_history: deque[float] = deque(maxlen=rsi_period + 1)
        self.last_rsi: float | None = None

    def _calculate_rsi(self) -> float | None:
        values = list(self.close_history)
        if len(values) <= self.rsi_period:
            return None
        
        gains = 0.0
        losses = 0.0
        for i in range(1, len(values)):
            delta = values[i] - values[i - 1]
            if delta > 0:
                gains += delta
            else:
                losses += -delta
                
        avg_gain = gains / self.rsi_period
        avg_loss = losses / self.rsi_period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def on_bar(self, bar: MarketBar) -> Signal | None:
        self.close_history.append(bar.close)
        
        rsi = self._calculate_rsi()
        if rsi is None:
            return None
            
        signal = None
        
        # Simple threshold crossings
        if rsi <= self.rsi_oversold and (self.last_rsi is None or self.last_rsi > self.rsi_oversold):
            signal = Signal(
                symbol=bar.symbol,
                side=Side.BUY,
                size=self.order_size_units,
                reason=f"rsi_mean_reversion_oversold_{rsi:.1f}",
                score=1.0,
                confidence=1.0,
                regime="mean_reversion",
            )
        elif rsi >= self.rsi_overbought and (self.last_rsi is None or self.last_rsi < self.rsi_overbought):
            signal = Signal(
                symbol=bar.symbol,
                side=Side.SELL,
                size=self.order_size_units,
                reason=f"rsi_mean_reversion_overbought_{rsi:.1f}",
                score=1.0,
                confidence=1.0,
                regime="mean_reversion",
            )

        self.last_rsi = rsi
        return signal
