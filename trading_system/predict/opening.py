from __future__ import annotations

from dataclasses import dataclass
import json
import math
from urllib import error, request


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: list[float], sample_mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - sample_mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


@dataclass(slots=True)
class OpenPrediction:
    symbol: str
    reference_close: float
    predicted_open: float
    lower_bound: float
    upper_bound: float
    avg_gap_pct: float
    stdev_gap_pct: float
    observations: int


def _normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().replace(" ", "")
    if ":" in cleaned:
        cleaned = cleaned.split(":", 1)[1]
    return cleaned


def _infer_screener(exchange: str) -> str:
    ex = exchange.upper()
    if ex in {"NSE", "BSE"}:
        return "india"
    if ex in {"BINANCE", "COINBASE", "KRAKEN", "BYBIT", "BITSTAMP", "KUCOIN"}:
        return "crypto"
    if ex in {"FX_IDC", "FOREXCOM", "OANDA", "FXCM", "IDEALPRO"}:
        return "forex"
    return "america"


def _scan_symbol(screener: str, exchange: str, symbol: str, columns: list[str]) -> list[float | int | None]:
    payload = {
        "symbols": {
            "tickers": [f"{exchange.upper()}:{_normalize_symbol(symbol)}"],
            "query": {"types": []},
        },
        "columns": columns,
    }
    req = request.Request(
        url=f"https://scanner.tradingview.com/{screener}/scan",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=20) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    rows = raw.get("data", [])
    if not rows:
        raise RuntimeError(f"TradingView returned no rows for {exchange}:{symbol}")

    return rows[0].get("d", [])


def predict_next_open(
    exchange: str,
    symbol: str,
    screener: str | None = None,
    lookback_days: int = 120,
    gap_window: int = 20,
) -> OpenPrediction:
    # lookback_days kept for CLI compatibility; TradingView free scanner exposes recent shifted bars.
    _ = lookback_days

    resolved_screener = (screener or _infer_screener(exchange)).lower()
    columns = ["open", "close", "open[1]", "close[1]", "open[2]", "close[2]", "time"]

    try:
        values = _scan_symbol(resolved_screener, exchange, symbol, columns)
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Failed to fetch market data from TradingView: {exc}") from exc

    mapped = {columns[i]: values[i] if i < len(values) else None for i in range(len(columns))}

    open_0 = float(mapped["open"]) if mapped["open"] is not None else None
    close_0 = float(mapped["close"]) if mapped["close"] is not None else None
    open_1 = float(mapped["open[1]"]) if mapped["open[1]"] is not None else None
    close_1 = float(mapped["close[1]"]) if mapped["close[1]"] is not None else None
    open_2 = float(mapped["open[2]"]) if mapped["open[2]"] is not None else None
    close_2 = float(mapped["close[2]"]) if mapped["close[2]"] is not None else None

    if close_0 is None:
        raise RuntimeError("TradingView response missing current close")

    gaps: list[float] = []
    if open_0 is not None and close_1 is not None and close_1 > 0:
        gaps.append((open_0 / close_1) - 1.0)
    if open_1 is not None and close_2 is not None and close_2 > 0:
        gaps.append((open_1 / close_2) - 1.0)

    if not gaps:
        raise RuntimeError("Insufficient TradingView daily gap fields to forecast next open")

    tail = gaps[-max(1, min(gap_window, len(gaps))) :]
    avg_gap = _mean(tail)
    gap_sd = _stdev(tail, avg_gap)

    reference_close = close_0
    predicted_open = reference_close * (1.0 + avg_gap)
    lower_bound = reference_close * (1.0 + avg_gap - gap_sd)
    upper_bound = reference_close * (1.0 + avg_gap + gap_sd)

    return OpenPrediction(
        symbol=_normalize_symbol(symbol),
        reference_close=reference_close,
        predicted_open=predicted_open,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        avg_gap_pct=avg_gap * 100.0,
        stdev_gap_pct=gap_sd * 100.0,
        observations=len(tail),
    )