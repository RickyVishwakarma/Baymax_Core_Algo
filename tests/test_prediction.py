from __future__ import annotations

from trading_system.predict.opening import _infer_screener, predict_next_open
import trading_system.predict.opening as opening


def test_predict_next_open_uses_tradingview_shifted_daily_fields() -> None:
    def fake_scan_symbol(screener: str, exchange: str, symbol: str, columns: list[str]):
        assert screener == "india"
        assert exchange == "NSE"
        assert symbol == "RELIANCE"
        # open, close, open[1], close[1], open[2], close[2], time
        return [105.0, 102.0, 101.0, 100.0, 99.0, 98.0, 1772768700]

    original = opening._scan_symbol
    opening._scan_symbol = fake_scan_symbol
    try:
        pred = predict_next_open(screener="india", exchange="NSE", symbol="RELIANCE", gap_window=20)
    finally:
        opening._scan_symbol = original

    # gaps: 105/100-1=5%, 101/98-1=3.0612%
    assert round(pred.reference_close, 2) == 102.00
    assert round(pred.avg_gap_pct, 4) == 4.0306
    assert round(pred.predicted_open, 2) == 106.11
    assert pred.observations == 2


def test_infer_screener() -> None:
    assert _infer_screener("NSE") == "india"
    assert _infer_screener("FX_IDC") == "forex"
    assert _infer_screener("BINANCE") == "crypto"