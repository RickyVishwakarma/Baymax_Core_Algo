from __future__ import annotations

from collections import deque

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy

class SupertrendStrategy(Strategy):
    """
    Supertrend Strategy utilizes ATR and a multiplier to form a trailing stop trend line.
    It issues a Buy signal when the price closes above the upper channel, and a Sell signal 
    when it closes below the lower channel.
    """
    def __init__(
        self,
        atr_period: int = 10,
        multiplier: float = 3.0,
        fast_ema_period: int = 9,
        slow_ema_period: int = 21,
        order_size_units: float = 0.1,
    ):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.fast_ema_period = fast_ema_period
        self.slow_ema_period = slow_ema_period
        self.order_size_units = order_size_units
        
        self.highs: deque[float] = deque(maxlen=atr_period + 1)
        self.lows: deque[float] = deque(maxlen=atr_period + 1)
        self.closes: deque[float] = deque(maxlen=atr_period + 1)
        
        self.supertrend: float | None = None
        self.in_uptrend: bool = True
        self.final_upperband: float | None = None
        self.final_lowerband: float | None = None
        
        # EMA State
        self.fast_ema: float | None = None
        self.slow_ema: float | None = None

    def _calculate_atr(self) -> float | None:
        if len(self.closes) <= self.atr_period:
            return None
            
        trs = []
        for i in range(1, len(self.closes)):
            tr = max(
                self.highs[i] - self.lows[i],
                abs(self.highs[i] - self.closes[i-1]),
                abs(self.lows[i] - self.closes[i-1])
            )
            trs.append(tr)
            
        return sum(trs[-self.atr_period:]) / self.atr_period

    def _calculate_ema(self, current_val: float, prev_ema: float | None, period: int) -> float:
        if prev_ema is None:
            return sum(list(self.closes)[-period:]) / period if len(self.closes) >= period else current_val
        alpha = 2.0 / (period + 1.0)
        return (current_val - prev_ema) * alpha + prev_ema

    def on_bar(self, bar: MarketBar) -> Signal | None:
        self.highs.append(bar.high)
        self.lows.append(bar.low)
        self.closes.append(bar.close)
        
        # Update EMAs
        if len(self.closes) >= self.fast_ema_period:
            self.fast_ema = self._calculate_ema(bar.close, self.fast_ema, self.fast_ema_period)
        if len(self.closes) >= self.slow_ema_period:
            self.slow_ema = self._calculate_ema(bar.close, self.slow_ema, self.slow_ema_period)

        atr = self._calculate_atr()
        if atr is None:
            return None
            
        hl2 = (bar.high + bar.low) / 2.0
        basic_upperband = hl2 + self.multiplier * atr
        basic_lowerband = hl2 - self.multiplier * atr

        if self.final_upperband is None or self.final_lowerband is None:
            self.final_upperband = basic_upperband
            self.final_lowerband = basic_lowerband
            self.supertrend = self.final_upperband
            return None

        prev_close = self.closes[-2]

        if basic_upperband < self.final_upperband or prev_close > self.final_upperband:
            self.final_upperband = basic_upperband

        if basic_lowerband > self.final_lowerband or prev_close < self.final_lowerband:
            self.final_lowerband = basic_lowerband

        prev_uptrend = self.in_uptrend
        
        if self.supertrend == self.final_upperband and bar.close > self.final_upperband:
            self.in_uptrend = True
        elif self.supertrend == self.final_lowerband and bar.close < self.final_lowerband:
            self.in_uptrend = False
            
        self.supertrend = self.final_lowerband if self.in_uptrend else self.final_upperband

        # If trend flipped OR EMA crossed while in trend, issue signal
        signal = None
        ema_bullish = self.fast_ema is not None and self.slow_ema is not None and self.fast_ema > self.slow_ema
        ema_bearish = self.fast_ema is not None and self.slow_ema is not None and self.fast_ema < self.slow_ema
        
        # Standard Supertrend flip with EMA confirmation
        if self.in_uptrend and not prev_uptrend and ema_bullish:
            signal = Signal(
                symbol=bar.symbol,
                side=Side.BUY,
                size=self.order_size_units,
                reason="supertrend_ema_bullish",
                score=1.0,
                confidence=1.0,
                regime="supertrend"
            )
        elif not self.in_uptrend and prev_uptrend and ema_bearish:
            signal = Signal(
                symbol=bar.symbol,
                side=Side.SELL,
                size=self.order_size_units,
                reason="supertrend_ema_bearish",
                score=1.0,
                confidence=1.0,
                regime="supertrend"
            )
        
        # Delayed entry: Supertrend is already UP, but EMA just crossed UP
        # (This is harder to track without storing previous EMA states. 
        # For simplicity, we just use the confluence at the time of the Supertrend flip, 
        # or we can constantly emit signals if confluence exists and let the execution engine handle "already in position").
        # We will keep it strictly to the flip for now as per standard implementations.
            
        return signal

    def is_bullish(self) -> bool | None:
        return self.in_uptrend
