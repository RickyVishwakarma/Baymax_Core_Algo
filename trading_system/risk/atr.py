from __future__ import annotations

from collections import defaultdict, deque
from trading_system.models import MarketBar

class MultiSymbolATRTracker:
    """
    Independent ATR calculator used by the Risk Manager.
    Tracks historical High/Low/Close prices for multiple symbols 
    to dynamically adjust stop losses.
    """
    def __init__(self, period: int = 14):
        self.period = period
        # Use period + 1 because ATR needs the previous close for the True Range calculation
        self.highs: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=period + 1))
        self.lows: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=period + 1))
        self.closes: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=period + 1))

    def update(self, bar: MarketBar) -> None:
        """Add a new bar to the symbol's rolling window."""
        self.highs[bar.symbol].append(bar.high)
        self.lows[bar.symbol].append(bar.low)
        self.closes[bar.symbol].append(bar.close)

    def get_atr(self, symbol: str) -> float | None:
        """
        Calculate and return the Average True Range for a symbol.
        Returns None if there isn't enough historical data yet.
        """
        closes = self.closes[symbol]
        highs = self.highs[symbol]
        lows = self.lows[symbol]

        if len(closes) <= self.period:
            return None
            
        trs = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)
            
        # Return simple moving average of True Range
        return sum(trs[-self.period:]) / self.period
