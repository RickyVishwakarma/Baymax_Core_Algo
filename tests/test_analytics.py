from __future__ import annotations

from trading_system.analytics import build_backtest_report


def test_build_backtest_report_smoke() -> None:
    equities = [100000.0, 100100.0, 100050.0, 100300.0]
    fills = [
        ("2026-01-01T09:15:00", "BUY", 1.0, 100.0, 0.01),
        ("2026-01-01T10:15:00", "SELL", 1.0, 102.0, 0.01),
    ]
    report = build_backtest_report(equities, fills)

    assert report.bars == 4
    assert report.trade_count == 2
    assert report.end_equity == 100300.0
