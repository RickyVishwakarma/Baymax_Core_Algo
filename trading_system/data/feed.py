from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timezone
import csv
import json
import logging
import time
from urllib import error, request

from trading_system.models import MarketBar


logger = logging.getLogger(__name__)


def fetch_tradingview_quote(
    *,
    screener: str,
    exchange: str,
    symbol: str,
    request_timeout_seconds: int = 15,
) -> MarketBar:
    """Fetch a single latest OHLCV bar from TradingView scanner."""
    payload = {
        "symbols": {
            "tickers": [f"{exchange}:{symbol}"],
            "query": {"types": []},
        },
        "columns": ["open", "high", "low", "close", "volume", "time"],
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=f"https://scanner.tradingview.com/{screener}/scan",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=max(3, request_timeout_seconds)) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    rows = raw.get("data", [])
    if not rows:
        raise RuntimeError("TradingView returned no rows")

    cols = rows[0].get("d", [])
    if len(cols) < 5:
        raise RuntimeError("TradingView response missing OHLCV columns")

    open_px = float(cols[0])
    high_px = float(cols[1])
    low_px = float(cols[2])
    close_px = float(cols[3])
    volume = float(cols[4])

    ts_col = cols[5] if len(cols) > 5 else None
    if isinstance(ts_col, (int, float)):
        ts = datetime.fromtimestamp(float(ts_col), tz=timezone.utc).replace(tzinfo=None)
    else:
        ts = datetime.utcnow()

    return MarketBar(
        ts=ts,
        symbol=symbol,
        open=open_px,
        high=high_px,
        low=low_px,
        close=close_px,
        volume=volume,
    )


class MarketDataFeed(ABC):
    @abstractmethod
    def stream(self) -> Iterator[MarketBar]:
        raise NotImplementedError


class CsvMarketDataFeed(MarketDataFeed):
    def __init__(self, path: str, symbol: str):
        self.path = path
        self.symbol = symbol

    def stream(self) -> Iterator[MarketBar]:
        with open(self.path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield MarketBar(
                    ts=datetime.fromisoformat(row["timestamp"]),
                    symbol=self.symbol,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )


class TradingViewPollingFeed(MarketDataFeed):
    """Polling feed using TradingView scanner endpoint (unofficial/public behavior may change)."""

    def __init__(
        self,
        screener: str,
        exchange: str,
        symbol: str,
        poll_seconds: int = 5,
        max_bars: int | None = None,
        emit_on_same_timestamp: bool = True,
        request_timeout_seconds: int = 15,
        retry_delay_seconds: int = 3,
    ):
        self.screener = screener
        self.exchange = exchange
        self.symbol = symbol
        self.poll_seconds = max(1, poll_seconds)
        self.max_bars = max_bars
        self.emit_on_same_timestamp = emit_on_same_timestamp
        self.request_timeout_seconds = max(3, request_timeout_seconds)
        self.retry_delay_seconds = max(1, retry_delay_seconds)
        self.url = f"https://scanner.tradingview.com/{self.screener}/scan"
        self._last_ts: datetime | None = None

    def _fetch_one(self) -> MarketBar:
        return fetch_tradingview_quote(
            screener=self.screener,
            exchange=self.exchange,
            symbol=self.symbol,
            request_timeout_seconds=self.request_timeout_seconds,
        )

    def stream(self) -> Iterator[MarketBar]:
        emitted = 0
        while self.max_bars is None or emitted < self.max_bars:
            try:
                bar = self._fetch_one()
            except (error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
                logger.warning("data_fetch_error source=tradingview symbol=%s error=%s", self.symbol, exc)
                time.sleep(self.retry_delay_seconds)
                continue

            should_emit = False
            if self._last_ts is None:
                should_emit = True
            elif bar.ts > self._last_ts:
                should_emit = True
            elif self.emit_on_same_timestamp:
                should_emit = True

            if should_emit:
                self._last_ts = bar.ts
                emitted += 1
                yield bar

            time.sleep(self.poll_seconds)
