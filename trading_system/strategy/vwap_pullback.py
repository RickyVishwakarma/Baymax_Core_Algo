from __future__ import annotations

from collections import deque
from datetime import datetime
import logging

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy

logger = logging.getLogger(__name__)

class VwapPullbackStrategy(Strategy):
    """
    Strategy 3: VWAP Pullback + RSI Reversal
    Waits for price to pull back to the Daily VWAP zone. 
    Triggers a BUY if RSI hits 40-45 and momentum reverses upwards.
    Triggers a SELL if RSI hits 55-60 and momentum reverses downwards.
    """
    def __init__(
        self,
        rsi_period: int = 14,
        vwap_tolerance_pct: float = 0.002, # 0.2% away from VWAP is considered a "touch"
        order_size_units: float = 0.1,
    ):
        self.rsi_period = rsi_period
        self.vwap_tolerance_pct = vwap_tolerance_pct
        self.order_size_units = order_size_units
        
        self.closes: deque[float] = deque(maxlen=100)
        
        # RSI State (Wilder's Smoothing)
        self.avg_gain: float | None = None
        self.avg_loss: float | None = None
        self.current_rsi: float | None = None
        self.prev_rsi: float | None = None
        
        # VWAP State
        self.current_date = None
        self.cumulative_vol_price = 0.0
        self.cumulative_vol = 0.0
        self.current_vwap = 0.0

    def _update_rsi(self, change: float) -> None:
        gain = max(0.0, change)
        loss = max(0.0, -change)
        
        if self.avg_gain is None or self.avg_loss is None:
            # Simple average for the first 'period'
            if len(self.closes) < self.rsi_period:
                return # Wait for enough data
            # Calculate initial SMA
            changes = [self.closes[i] - self.closes[i-1] for i in range(1, len(self.closes))]
            gains = [max(0.0, c) for c in changes[-self.rsi_period:]]
            losses = [max(0.0, -c) for c in changes[-self.rsi_period:]]
            self.avg_gain = sum(gains) / self.rsi_period
            self.avg_loss = sum(losses) / self.rsi_period
        else:
            # Wilder's Smoothing
            self.avg_gain = ((self.avg_gain * (self.rsi_period - 1)) + gain) / self.rsi_period
            self.avg_loss = ((self.avg_loss * (self.rsi_period - 1)) + loss) / self.rsi_period
            
        if self.avg_loss == 0:
            self.current_rsi = 100.0
        else:
            rs = self.avg_gain / self.avg_loss
            self.current_rsi = 100.0 - (100.0 / (1.0 + rs))

    def on_bar(self, bar: MarketBar) -> Signal | None:
        bar_date = bar.ts.date()
        
        # Day Rollover Reset
        if self.current_date != bar_date:
            self.current_date = bar_date
            self.cumulative_vol_price = 0.0
            self.cumulative_vol = 0.0
            self.current_vwap = 0.0
            
        # Update Daily VWAP
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        self.cumulative_vol_price += typical_price * bar.volume
        self.cumulative_vol += bar.volume
        
        if self.cumulative_vol > 0:
            self.current_vwap = self.cumulative_vol_price / self.cumulative_vol
            
        # Update RSI
        if len(self.closes) > 0:
            change = bar.close - self.closes[-1]
            self.prev_rsi = self.current_rsi
            self._update_rsi(change)
            
        self.closes.append(bar.close)
        
        if self.current_rsi is None or self.prev_rsi is None or self.current_vwap == 0.0:
            return None
            
        # Check Pullback Confluence
        distance_to_vwap = abs(bar.close - self.current_vwap) / self.current_vwap
        near_vwap = distance_to_vwap <= self.vwap_tolerance_pct
        
        signal = None
        
        # BUY Trigger: Price near VWAP, RSI was in 40-45 zone and has now hooked UP (momentum shift)
        if near_vwap and bar.close > self.current_vwap:
            if 40 <= self.prev_rsi <= 48 and self.current_rsi > self.prev_rsi:
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.BUY,
                    size=self.order_size_units,
                    reason="vwap_pullback_long",
                    score=1.0,
                    confidence=1.0,
                    regime="pullback"
                )
                
        # SELL Trigger: Price near VWAP, RSI was in 52-60 zone and has now hooked DOWN
        elif near_vwap and bar.close < self.current_vwap:
            if 52 <= self.prev_rsi <= 60 and self.current_rsi < self.prev_rsi:
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.SELL,
                    size=self.order_size_units,
                    reason="vwap_pullback_short",
                    score=1.0,
                    confidence=1.0,
                    regime="pullback"
                )

        return signal

    def is_bullish(self) -> bool | None:
        if self.current_vwap == 0.0:
            return None
        return self.closes[-1] > self.current_vwap if len(self.closes) > 0 else None
