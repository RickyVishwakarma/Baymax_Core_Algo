from __future__ import annotations

from datetime import datetime, timedelta
import logging

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy

logger = logging.getLogger(__name__)

class OrbVwapStrategy(Strategy):
    """
    Strategy 1: ORB + VWAP Confluence
    Tracks the highest high and lowest low of the Opening Range (e.g., first 30 minutes).
    Issues a BUY signal when price closes above OR High AND is above Daily VWAP.
    Issues a SELL signal when price closes below OR Low AND is below Daily VWAP.
    """
    def __init__(
        self,
        orb_minutes: int = 30,
        order_size_units: float = 0.1,
    ):
        self.orb_minutes = orb_minutes
        self.order_size_units = order_size_units
        
        # State
        self.current_date = None
        self.session_start_time: datetime | None = None
        
        # ORB Trackers
        self.orb_high = -float('inf')
        self.orb_low = float('inf')
        self.orb_established = False
        
        # VWAP Trackers
        self.cumulative_vol_price = 0.0
        self.cumulative_vol = 0.0
        self.current_vwap = 0.0
        
        # Trade Management
        self.position_side: Side | None = None

    def on_bar(self, bar: MarketBar) -> Signal | None:
        bar_date = bar.ts.date()
        
        # Day Rollover Reset
        if self.current_date != bar_date:
            self.current_date = bar_date
            self.session_start_time = bar.ts
            self.orb_high = -float('inf')
            self.orb_low = float('inf')
            self.orb_established = False
            self.cumulative_vol_price = 0.0
            self.cumulative_vol = 0.0
            self.current_vwap = 0.0
            self.position_side = None
            
        # Update Daily VWAP
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        self.cumulative_vol_price += typical_price * bar.volume
        self.cumulative_vol += bar.volume
        
        if self.cumulative_vol > 0:
            self.current_vwap = self.cumulative_vol_price / self.cumulative_vol
            
        # Update Opening Range
        if self.session_start_time is not None:
            time_elapsed = (bar.ts - self.session_start_time).total_seconds() / 60.0
            
            if time_elapsed <= self.orb_minutes:
                # Still inside the Opening Range window
                self.orb_high = max(self.orb_high, bar.high)
                self.orb_low = min(self.orb_low, bar.low)
                return None  # No trades during ORB formation
            else:
                self.orb_established = True
                
        if not self.orb_established:
            return None
            
        signal = None
        
        # Signal Generation Logic
        if self.position_side is None:
            # Check for Long Breakout (Close > OR_High AND Close > VWAP)
            if bar.close > self.orb_high and bar.close > self.current_vwap:
                self.position_side = Side.BUY
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.BUY,
                    size=self.order_size_units,
                    reason="orb_vwap_breakout_up",
                    score=1.0,
                    confidence=1.0,
                    regime="orb_vwap"
                )
            # Check for Short Breakout (Close < OR_Low AND Close < VWAP)
            elif bar.close < self.orb_low and bar.close < self.current_vwap:
                self.position_side = Side.SELL
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.SELL,
                    size=self.order_size_units,
                    reason="orb_vwap_breakout_down",
                    score=1.0,
                    confidence=1.0,
                    regime="orb_vwap"
                )
        else:
            # Exit Logic (Trailing stop could be managed by Risk Manager, but we can add a VWAP cross exit)
            if self.position_side == Side.BUY and bar.close < self.current_vwap:
                self.position_side = None
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.SELL,
                    size=self.order_size_units,
                    reason="orb_vwap_exit_long",
                    score=1.0,
                    confidence=1.0,
                    regime="orb_vwap"
                )
            elif self.position_side == Side.SELL and bar.close > self.current_vwap:
                self.position_side = None
                signal = Signal(
                    symbol=bar.symbol,
                    side=Side.BUY,
                    size=self.order_size_units,
                    reason="orb_vwap_exit_short",
                    score=1.0,
                    confidence=1.0,
                    regime="orb_vwap"
                )

        return signal

    def is_bullish(self) -> bool | None:
        if self.current_vwap == 0.0:
            return None
        # In VWAP strategies, trend is traditionally measured relative to the VWAP line
        return self.closes[-1] > self.current_vwap if hasattr(self, 'closes') and len(self.closes) > 0 else None
