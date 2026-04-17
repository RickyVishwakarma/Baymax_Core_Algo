from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DataConfig:
    source: str = "tradingview"
    csv_path: str | None = None
    tradingview_screener: str = "crypto"
    tradingview_exchange: str = "BINANCE"
    tradingview_symbols: list[str] = field(default_factory=lambda: ["BTCUSDT"])
    poll_seconds: int = 5
    max_bars: int | None = None
    emit_on_same_timestamp: bool = True
    request_timeout_seconds: int = 15
    retry_delay_seconds: int = 3
    dhan_exchange: str = "NSE"
    dhan_symbols: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TradingConfig:
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT"])
    starting_cash: float = 100_000.0
    max_position_units: float = 2.0
    max_notional_per_order: float = 15_000.0
    max_drawdown_pct: float = 0.15
    trailing_stop_pct: float = 0.0
    atr_trailing_stop: dict = field(default_factory=lambda: {"enabled": False, "period": 14, "multiplier": 3.0})
    min_velocity_threshold: float = 0.0
    allow_short: bool = True
    max_exposure_pct: float = 1.0
    max_bar_range_pct: float = 0.20
    min_cash_buffer_pct: float = 0.01
    fee_bps: float = 5.0
    slippage_bps: float = 3.0
    execution: dict = field(default_factory=lambda: {"type": "paper"})
    strategy: dict = field(default_factory=lambda: {"name": "moving_average", "params": {}})
    position_sizing: dict = field(default_factory=lambda: {"type": "fixed"})
    ml_regime: dict = field(default_factory=lambda: {"enabled": False})
    data: DataConfig = field(default_factory=DataConfig)


def load_config(path: str | None) -> TradingConfig:
    if not path:
        return TradingConfig()

    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    strategy_raw = raw.get("strategy", {})
    data_raw = raw.get("data", {})

    if "name" not in strategy_raw:
        # backwards compat for old configs
        strategy_cfg = {"name": "moving_average", "params": strategy_raw}
    else:
        strategy_cfg = strategy_raw

    raw_max_bars = data_raw.get("max_bars", None)
    max_bars = int(raw_max_bars) if raw_max_bars is not None else None
    data_cfg = DataConfig(
        source=str(data_raw.get("source", "tradingview")).lower(),
        csv_path=data_raw.get("csv_path"),
        tradingview_screener=str(data_raw.get("tradingview_screener", "crypto")),
        tradingview_exchange=str(data_raw.get("tradingview_exchange", "BINANCE")),
        tradingview_symbols=data_raw.get("tradingview_symbols", [data_raw.get("tradingview_symbol", "BTCUSDT")]),
        poll_seconds=int(data_raw.get("poll_seconds", 5)),
        max_bars=max_bars,
        emit_on_same_timestamp=bool(data_raw.get("emit_on_same_timestamp", True)),
        request_timeout_seconds=int(data_raw.get("request_timeout_seconds", 15)),
        retry_delay_seconds=int(data_raw.get("retry_delay_seconds", 3)),
    )

    return TradingConfig(
        symbols=raw.get("symbols", [raw.get("symbol", "BTCUSDT")]),
        starting_cash=float(raw.get("starting_cash", 100_000.0)),
        max_position_units=float(raw.get("max_position_units", 2.0)),
        max_notional_per_order=float(raw.get("max_notional_per_order", 15_000.0)),
        max_drawdown_pct=float(raw.get("max_drawdown_pct", 0.15)),
        trailing_stop_pct=float(raw.get("trailing_stop_pct", 0.0)),
        atr_trailing_stop=raw.get("atr_trailing_stop", {"enabled": False, "period": 14, "multiplier": 3.0}),
        min_velocity_threshold=float(raw.get("min_velocity_threshold", 0.0)),
        allow_short=bool(raw.get("allow_short", True)),
        max_exposure_pct=float(raw.get("max_exposure_pct", 1.0)),
        max_bar_range_pct=float(raw.get("max_bar_range_pct", 0.20)),
        min_cash_buffer_pct=float(raw.get("min_cash_buffer_pct", 0.01)),
        fee_bps=float(raw.get("fee_bps", 5.0)),
        slippage_bps=float(raw.get("slippage_bps", 3.0)),
        execution=raw.get("execution", {"type": "paper"}),
        strategy=strategy_cfg,
        position_sizing=raw.get("position_sizing", {"type": "fixed"}),
        ml_regime=raw.get("ml_regime", {"enabled": False}),
        data=data_cfg,
    )
