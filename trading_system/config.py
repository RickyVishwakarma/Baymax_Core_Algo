from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class StrategyConfig:
    mode: str = "advanced"
    short_window: int = 5
    long_window: int = 20
    order_size_units: float = 0.1
    use_rsi: bool = True
    rsi_period: int = 14
    rsi_oversold: float = 35.0
    rsi_overbought: float = 65.0
    use_bollinger: bool = True
    bollinger_window: int = 20
    bollinger_stddev: float = 2.0
    use_macd: bool = True
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    min_confirmations: int = 1
    trend_ema_fast: int = 12
    trend_ema_slow: int = 34
    momentum_window: int = 10
    breakout_window: int = 20
    volatility_window: int = 20
    atr_period: int = 14
    target_volatility_pct: float = 1.0
    min_signal_score: float = 2.2
    max_size_multiplier: float = 3.0
    use_volume_confirmation: bool = True
    volume_window: int = 20
    regime_trend_threshold: float = 0.6
    regime_chop_threshold: float = 0.2
    signal_cooldown_bars: int = 2
    score_hysteresis: float = 0.25


@dataclass(slots=True)
class DataConfig:
    source: str = "tradingview"
    csv_path: str | None = None
    tradingview_screener: str = "crypto"
    tradingview_exchange: str = "BINANCE"
    tradingview_symbol: str = "BTCUSDT"
    poll_seconds: int = 5
    max_bars: int | None = None
    emit_on_same_timestamp: bool = True
    request_timeout_seconds: int = 15
    retry_delay_seconds: int = 3


@dataclass(slots=True)
class TradingConfig:
    symbol: str = "BTCUSDT"
    starting_cash: float = 100_000.0
    max_position_units: float = 2.0
    max_notional_per_order: float = 15_000.0
    max_drawdown_pct: float = 0.15
    allow_short: bool = True
    max_exposure_pct: float = 1.0
    max_bar_range_pct: float = 0.20
    min_cash_buffer_pct: float = 0.01
    fee_bps: float = 5.0
    slippage_bps: float = 3.0
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    data: DataConfig = field(default_factory=DataConfig)


def load_config(path: str | None) -> TradingConfig:
    if not path:
        return TradingConfig()

    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    strategy_raw = raw.get("strategy", {})
    data_raw = raw.get("data", {})

    strategy_cfg = StrategyConfig(
        mode=str(strategy_raw.get("mode", "advanced")).lower(),
        short_window=int(strategy_raw.get("short_window", 5)),
        long_window=int(strategy_raw.get("long_window", 20)),
        order_size_units=float(strategy_raw.get("order_size_units", 0.1)),
        use_rsi=bool(strategy_raw.get("use_rsi", True)),
        rsi_period=int(strategy_raw.get("rsi_period", 14)),
        rsi_oversold=float(strategy_raw.get("rsi_oversold", 35.0)),
        rsi_overbought=float(strategy_raw.get("rsi_overbought", 65.0)),
        use_bollinger=bool(strategy_raw.get("use_bollinger", True)),
        bollinger_window=int(strategy_raw.get("bollinger_window", 20)),
        bollinger_stddev=float(strategy_raw.get("bollinger_stddev", 2.0)),
        use_macd=bool(strategy_raw.get("use_macd", True)),
        macd_fast=int(strategy_raw.get("macd_fast", 12)),
        macd_slow=int(strategy_raw.get("macd_slow", 26)),
        macd_signal=int(strategy_raw.get("macd_signal", 9)),
        min_confirmations=int(strategy_raw.get("min_confirmations", 1)),
        trend_ema_fast=int(strategy_raw.get("trend_ema_fast", 12)),
        trend_ema_slow=int(strategy_raw.get("trend_ema_slow", 34)),
        momentum_window=int(strategy_raw.get("momentum_window", 10)),
        breakout_window=int(strategy_raw.get("breakout_window", 20)),
        volatility_window=int(strategy_raw.get("volatility_window", 20)),
        atr_period=int(strategy_raw.get("atr_period", 14)),
        target_volatility_pct=float(strategy_raw.get("target_volatility_pct", 1.0)),
        min_signal_score=float(strategy_raw.get("min_signal_score", 2.2)),
        max_size_multiplier=float(strategy_raw.get("max_size_multiplier", 3.0)),
        use_volume_confirmation=bool(strategy_raw.get("use_volume_confirmation", True)),
        volume_window=int(strategy_raw.get("volume_window", 20)),
        regime_trend_threshold=float(strategy_raw.get("regime_trend_threshold", 0.6)),
        regime_chop_threshold=float(strategy_raw.get("regime_chop_threshold", 0.2)),
        signal_cooldown_bars=int(strategy_raw.get("signal_cooldown_bars", 2)),
        score_hysteresis=float(strategy_raw.get("score_hysteresis", 0.25)),
    )

    raw_max_bars = data_raw.get("max_bars", None)
    max_bars = int(raw_max_bars) if raw_max_bars is not None else None
    data_cfg = DataConfig(
        source=str(data_raw.get("source", "tradingview")).lower(),
        csv_path=data_raw.get("csv_path"),
        tradingview_screener=str(data_raw.get("tradingview_screener", "crypto")),
        tradingview_exchange=str(data_raw.get("tradingview_exchange", "BINANCE")),
        tradingview_symbol=str(data_raw.get("tradingview_symbol", "BTCUSDT")),
        poll_seconds=int(data_raw.get("poll_seconds", 5)),
        max_bars=max_bars,
        emit_on_same_timestamp=bool(data_raw.get("emit_on_same_timestamp", True)),
        request_timeout_seconds=int(data_raw.get("request_timeout_seconds", 15)),
        retry_delay_seconds=int(data_raw.get("retry_delay_seconds", 3)),
    )

    return TradingConfig(
        symbol=str(raw.get("symbol", "BTCUSDT")),
        starting_cash=float(raw.get("starting_cash", 100_000.0)),
        max_position_units=float(raw.get("max_position_units", 2.0)),
        max_notional_per_order=float(raw.get("max_notional_per_order", 15_000.0)),
        max_drawdown_pct=float(raw.get("max_drawdown_pct", 0.15)),
        allow_short=bool(raw.get("allow_short", True)),
        max_exposure_pct=float(raw.get("max_exposure_pct", 1.0)),
        max_bar_range_pct=float(raw.get("max_bar_range_pct", 0.20)),
        min_cash_buffer_pct=float(raw.get("min_cash_buffer_pct", 0.01)),
        fee_bps=float(raw.get("fee_bps", 5.0)),
        slippage_bps=float(raw.get("slippage_bps", 3.0)),
        strategy=strategy_cfg,
        data=data_cfg,
    )
