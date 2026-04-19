from __future__ import annotations

from trading_system.models import MarketBar

class TimeframeResampler:
    """
    Aggregates incoming 1-minute MarketBars into Higher Timeframe (HTF) bars.
    Useful for running background macro-trend filters (MTF Alignment).
    """
    def __init__(self, timeframe_minutes: int):
        if timeframe_minutes < 1:
            raise ValueError("Timeframe must be at least 1 minute")
        self.timeframe = timeframe_minutes
        self.current_bars: dict[str, MarketBar] = {}
        
    def update(self, bar: MarketBar) -> MarketBar | None:
        """
        Updates the resampled bar with a new 1m bar.
        If the incoming 1m bar crosses the timeframe boundary (e.g., crossing from 09:19 to 09:20 
        for a 5m timeframe), it returns the completed HTF bar. Otherwise returns None.
        """
        # Calculate the "anchor" timestamp for this HTF bar.
        # e.g., 09:17 with timeframe=5 -> 09:15 anchor
        minute = bar.ts.minute
        anchor_minute = (minute // self.timeframe) * self.timeframe
        anchor_ts = bar.ts.replace(minute=anchor_minute, second=0, microsecond=0)
        
        symbol = bar.symbol
        completed_bar = None
        
        if symbol in self.current_bars:
            current = self.current_bars[symbol]
            if anchor_ts > current.ts:
                # We crossed a boundary! The previous HTF bar is now complete.
                completed_bar = current
                self.current_bars[symbol] = None
                
        if symbol not in self.current_bars or self.current_bars[symbol] is None:
            # Start a new HTF bar
            self.current_bars[symbol] = MarketBar(
                ts=anchor_ts,
                symbol=symbol,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume
            )
        else:
            # Update the existing forming HTF bar
            current = self.current_bars[symbol]
            current.high = max(current.high, bar.high)
            current.low = min(current.low, bar.low)
            current.close = bar.close
            current.volume += bar.volume
            
        return completed_bar
