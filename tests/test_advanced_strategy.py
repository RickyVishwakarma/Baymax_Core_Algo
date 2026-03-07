from __future__ import annotations

from datetime import datetime, timedelta

from trading_system.models import MarketBar, Side
from trading_system.strategy.moving_average import MovingAverageCrossStrategy


def test_advanced_strategy_emits_scored_signal() -> None:
    strategy = MovingAverageCrossStrategy(
        mode="advanced",
        short_window=3,
        long_window=6,
        order_size_units=1.0,
        trend_ema_fast=4,
        trend_ema_slow=8,
        momentum_window=4,
        breakout_window=6,
        atr_period=5,
        volume_window=5,
        min_signal_score=1.2,
        use_volume_confirmation=False,
        signal_cooldown_bars=0,
    )

    ts = datetime(2026, 1, 1, 9, 15, 0)
    signal = None
    for i in range(40):
        close = 100.0 + i * 0.8
        bar = MarketBar(
            ts=ts + timedelta(minutes=i),
            symbol="TEST",
            open=close - 0.2,
            high=close + 0.5,
            low=close - 0.6,
            close=close,
            volume=1000 + i * 5,
        )
        signal = strategy.on_bar(bar) or signal

    assert signal is not None
    assert signal.side in {Side.BUY, Side.SELL}
    assert signal.score > 0
    assert signal.confidence > 0
    assert signal.size > 0
