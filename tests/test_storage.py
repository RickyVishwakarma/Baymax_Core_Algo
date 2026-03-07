from __future__ import annotations

from datetime import datetime

from trading_system.models import Fill, Side, Signal
from trading_system.storage import SQLiteRunStore


def test_sqlite_run_store_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "runs.db"
    store = SQLiteRunStore(str(db_path))
    run_id = store.start_run(symbol="TEST", source="csv", strategy_mode="advanced", run_name="unit")

    ts = datetime(2026, 1, 1, 9, 15, 0)
    store.record_bar(run_id=run_id, ts=ts, symbol="TEST", close=100.0, equity=100000.0, cash=100000.0, units=0.0)
    fill = Fill(symbol="TEST", side=Side.BUY, size=1.0, fill_price=100.0, fee_paid=0.01)
    signal = Signal(symbol="TEST", side=Side.BUY, size=1.0, reason="unit", score=1.0, confidence=1.0, regime="test")
    store.record_fill(run_id=run_id, ts=ts, fill=fill, signal=signal, equity_after=99999.99)
    store.end_run(run_id=run_id, final_cash=99900.0, final_equity=100100.0, final_units=1.0)

    bars = store.load_bars(run_id)
    fills = store.load_fills(run_id)
    assert len(bars) == 1
    assert len(fills) == 1
