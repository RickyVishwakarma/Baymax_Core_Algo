from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timezone
import csv
import json
import logging
import time
import threading
import queue
import asyncio

import requests

from trading_system.models import MarketBar
from trading_system.data.dhan_manager import DhanInstrumentManager
from trading_system.data.dhan_socket import DhanV2WebSocketClient
from trading_system.data.aggregator import TickToBarAggregator

logger = logging.getLogger(__name__)


def fetch_tradingview_quotes(
    *,
    screener: str,
    exchange: str,
    symbols: list[str],
    request_timeout_seconds: int = 15,
    session: requests.Session | None = None,
) -> list[MarketBar]:
    """Fetch latest OHLCV bars for multiple symbols from TradingView scanner using requests."""
    payload = {
        "symbols": {
            "tickers": [f"{exchange}:{sym}" for sym in symbols],
            "query": {"types": []},
        },
        "columns": ["name", "open", "high", "low", "close", "volume", "time"],
    }
    
    url = f"https://scanner.tradingview.com/{screener}/scan"
    headers = {"Content-Type": "application/json"}
    
    try:
        if session is not None:
            resp = session.post(url, json=payload, headers=headers, timeout=max(3, request_timeout_seconds))
        else:
            resp = requests.post(url, json=payload, headers=headers, timeout=max(3, request_timeout_seconds))
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch data: {str(e)}") from e

    rows = raw.get("data", [])
    if not rows:
        raise RuntimeError("TradingView returned no rows")

    bars = []
    
    for row in rows:
        cols = row.get("d", [])
        if len(cols) < 6:
            continue
            
        sym = str(cols[0])
        open_px = float(cols[1])
        high_px = float(cols[2])
        low_px = float(cols[3])
        close_px = float(cols[4])
        volume = float(cols[5])

        ts_col = cols[6] if len(cols) > 6 else None
        if isinstance(ts_col, (int, float)):
            ts = datetime.fromtimestamp(float(ts_col), tz=timezone.utc).replace(tzinfo=None)
        else:
            ts = datetime.utcnow()

        bars.append(MarketBar(
            ts=ts,
            symbol=sym,
            open=open_px,
            high=high_px,
            low=low_px,
            close=close_px,
            volume=volume,
        ))
        
    return bars


class MarketDataFeed(ABC):
    @abstractmethod
    def stream(self) -> Iterator[MarketBar]:
        raise NotImplementedError


class DhanWebSocketFeed(MarketDataFeed):
    """Real-time streaming feed using Dhan HQ WebSocket v2."""

    # Map our config strings to Dhan numeric segments
    # Used as fallback if manager doesn't return one
    SEGMENT_MAP = {
        "NSE": 1,   # NSE_EQ
        "BSE": 7,   # BSE_EQ
    }

    def __init__(
        self,
        client_id: str,
        access_token: str,
        exchange: str,
        symbols: list[str],
        instrument_manager: DhanInstrumentManager
    ):
        self.client_id = client_id
        self.access_token = access_token
        self.symbols = symbols
        self.instrument_manager = instrument_manager
        
        segment = self.SEGMENT_MAP.get(exchange.upper(), 1)
        
        # 1. Map symbols to SecurityIds
        self.instrument_ids: list[tuple[int, int]] = []
        self._id_to_symbol: dict[int, str] = {}
        
        for sym in symbols:
            try:
                meta = self.instrument_manager.get_instrument_metadata(exchange, sym)
                sec_id = int(meta["security_id"])
                seg_str = meta.get("segment", "NSE_EQ")
                
                str_to_int = {
                    "IDX_I": 0, "NSE_EQ": 1, "NSE_FNO": 2, "NSE_CURRENCY": 3,
                    "BSE_EQ": 4, "MCX_COMM": 5, "BSE_CURRENCY": 7, "BSE_FNO": 8
                }
                segment_int = str_to_int.get(seg_str, 1)
                
                self.instrument_ids.append((segment_int, sec_id))
                self._id_to_symbol[sec_id] = sym
            except Exception as e:
                logger.error("Failed to map symbol %s: %s", sym, e)

        if not self.instrument_ids:
            raise RuntimeError("No valid instruments found for Dhan subscription.")

        self._queue: queue.Queue[MarketBar] = queue.Queue()
        self._aggregator = TickToBarAggregator(on_bar_complete=self._queue.put)
        
        self._socket_client = DhanV2WebSocketClient(
            client_id=self.client_id,
            access_token=self.access_token,
            instruments=self.instrument_ids,
            on_tick=self._on_tick
        )
        self._thread: threading.Thread | None = None

    def _on_tick(self, sec_id: int, price: float, volume: float, ts: datetime):
        symbol = self._id_to_symbol.get(sec_id)
        if symbol:
            # We use UTC in the aggregator
            self._aggregator.handle_tick(symbol, price, volume, ts)

    def _run_socket_loop(self):
        """Asynchronous loop running in a background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._socket_client.run())
        finally:
            loop.close()

    def stream(self) -> Iterator[MarketBar]:
        """Starts the socket thread and yields bars from the queue."""
        logger.info("Starting Dhan WebSocket thread...")
        self._thread = threading.Thread(target=self._run_socket_loop, daemon=True)
        self._thread.start()
        
        try:
            while True:
                # Blocks until a 1-minute bar is finalized by the aggregator
                bar = self._queue.get()
                yield bar
        except KeyboardInterrupt:
            logger.info("Dhan stream interrupted.")
        finally:
            self._socket_client.stop()
            if self._thread:
                self._thread.join(timeout=1)


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
        symbols: list[str],
        poll_seconds: int = 5,
        max_bars: int | None = None,
        emit_on_same_timestamp: bool = True,
        request_timeout_seconds: int = 15,
        retry_delay_seconds: int = 3,
    ):
        self.screener = screener
        self.exchange = exchange
        self.symbols = symbols
        self.poll_seconds = max(1, poll_seconds)
        self.max_bars = max_bars
        self.emit_on_same_timestamp = emit_on_same_timestamp
        self.request_timeout_seconds = max(3, request_timeout_seconds)
        self.retry_delay_seconds = max(1, retry_delay_seconds)
        self.url = f"https://scanner.tradingview.com/{self.screener}/scan"
        self._last_ts: datetime | None = None
        self._last_bar_tuples: dict[str, tuple[float, float, float, float, float]] = {}
        self._session = requests.Session()

    def _fetch_many(self) -> list[MarketBar]:
        return fetch_tradingview_quotes(
            screener=self.screener,
            exchange=self.exchange,
            symbols=self.symbols,
            request_timeout_seconds=self.request_timeout_seconds,
            session=self._session,
        )

    def stream(self) -> Iterator[MarketBar]:
        emitted = 0
        while self.max_bars is None or emitted < self.max_bars:
            try:
                bars = self._fetch_many()
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                logger.warning("data_fetch_error source=tradingview symbols=%s error=%s", len(self.symbols), exc)
                time.sleep(self.retry_delay_seconds)
                continue

            for bar in bars:
                live_ts = datetime.now(timezone.utc)
                live_bar = MarketBar(
                    ts=live_ts,
                    symbol=bar.symbol,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
                
                bar_tuple = (bar.open, bar.high, bar.low, bar.close, bar.volume)
                last_bar_tuple = self._last_bar_tuples.get(bar.symbol)
    
                should_emit = False
                if last_bar_tuple is None:
                    should_emit = True
                elif bar_tuple != last_bar_tuple:
                    should_emit = True
                    
                if not should_emit and self.emit_on_same_timestamp:
                    should_emit = True
    
                if should_emit:
                    self._last_ts = live_bar.ts
                    self._last_bar_tuples[bar.symbol] = bar_tuple
                    emitted += 1
                    yield live_bar

            time.sleep(self.poll_seconds)
