from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from trading_system.models import MarketBar

logger = logging.getLogger(__name__)

class TickToBarAggregator:
    """Aggregates real-time ticks into OHLCV bars based on time boundaries."""

    def __init__(self, on_bar_complete: Callable[[MarketBar], None]):
        self.on_bar_complete = on_bar_complete
        # symbol -> current_bar_dict
        self._current_bars: dict[str, dict] = {}

    def handle_tick(
        self, 
        symbol: str, 
        price: float, 
        volume: float, 
        ts: datetime | None = None
    ) -> None:
        """Processes a new tick and potentially emits a completed bar."""
        now = ts or datetime.now(timezone.utc)
        # Snap to the start of the current minute
        bar_ts = now.replace(second=0, microsecond=0)

        if symbol not in self._current_bars:
            self._start_new_bar(symbol, bar_ts, price, volume)
            return

        current = self._current_bars[symbol]
        
        # If the tick belongs to a new minute, finalize the old one
        if bar_ts > current["ts"]:
            self._emit_bar(symbol)
            self._start_new_bar(symbol, bar_ts, price, volume)
        else:
            # Update current bar
            current["high"] = max(current["high"], price)
            current["low"] = min(current["low"], price)
            current["close"] = price
            # Dhan volume is cumulative for the day. 
            # We track the 'offset' to calculate delta volume if needed, 
            # but usually, we just take the last volume value for the bar.
            current["volume"] = volume

    def _start_new_bar(self, symbol: str, ts: datetime, price: float, volume: float) -> None:
        self._current_bars[symbol] = {
            "ts": ts,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume
        }

    def _emit_bar(self, symbol: str) -> None:
        data = self._current_bars[symbol]
        bar = MarketBar(
            ts=data["ts"],
            symbol=symbol,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"]
        )
        self._current_bars.pop(symbol)
        self.on_bar_complete(bar)

    def flush_all(self) -> None:
        """Force emits all current incomplete bars."""
        symbols = list(self._current_bars.keys())
        for sym in symbols:
            self._emit_bar(sym)
