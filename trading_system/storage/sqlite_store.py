from __future__ import annotations

from datetime import datetime
import json
import sqlite3

from trading_system.models import Fill, Signal


class SQLiteRunStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    run_name TEXT,
                    symbol TEXT NOT NULL,
                    source TEXT NOT NULL,
                    strategy_mode TEXT NOT NULL,
                    config_json TEXT,
                    status TEXT NOT NULL DEFAULT 'running',
                    final_cash REAL,
                    final_equity REAL,
                    final_units REAL
                );

                CREATE TABLE IF NOT EXISTS bars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    close REAL NOT NULL,
                    equity REAL NOT NULL,
                    cash REAL NOT NULL,
                    units REAL NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_bars_run_ts ON bars(run_id, ts);

                CREATE TABLE IF NOT EXISTS fills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    fill_price REAL NOT NULL,
                    fee_paid REAL NOT NULL,
                    reason TEXT NOT NULL,
                    score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    regime TEXT NOT NULL,
                    equity_after REAL NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_fills_run_ts ON fills(run_id, ts);
                """
            )

    def start_run(
        self,
        *,
        symbol: str,
        source: str,
        strategy_mode: str,
        run_name: str | None = None,
        config_obj: dict | None = None,
    ) -> int:
        now = datetime.utcnow().isoformat()
        config_json = json.dumps(config_obj, separators=(",", ":")) if config_obj is not None else None
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO runs (started_at, run_name, symbol, source, strategy_mode, config_json, status)
                VALUES (?, ?, ?, ?, ?, ?, 'running')
                """,
                (now, run_name, symbol, source, strategy_mode, config_json),
            )
            return int(cur.lastrowid)

    def record_bar(
        self,
        *,
        run_id: int,
        ts: datetime,
        symbol: str,
        close: float,
        equity: float,
        cash: float,
        units: float,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bars (run_id, ts, symbol, close, equity, cash, units)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, ts.isoformat(), symbol, close, equity, cash, units),
            )

    def record_fill(
        self,
        *,
        run_id: int,
        ts: datetime,
        fill: Fill,
        signal: Signal,
        equity_after: float,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fills (
                    run_id, ts, symbol, side, size, fill_price, fee_paid,
                    reason, score, confidence, regime, equity_after
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    ts.isoformat(),
                    fill.symbol,
                    fill.side.value,
                    fill.size,
                    fill.fill_price,
                    fill.fee_paid,
                    signal.reason,
                    signal.score,
                    signal.confidence,
                    signal.regime,
                    equity_after,
                ),
            )

    def end_run(self, *, run_id: int, final_cash: float, final_equity: float, final_units: float, status: str = "completed") -> None:
        ended_at = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET ended_at = ?, status = ?, final_cash = ?, final_equity = ?, final_units = ?
                WHERE id = ?
                """,
                (ended_at, status, final_cash, final_equity, final_units, run_id),
            )

    def load_bars(self, run_id: int) -> list[tuple[str, float]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT ts, equity FROM bars WHERE run_id = ? ORDER BY ts", (run_id,)).fetchall()
        return [(str(ts), float(equity)) for ts, equity in rows]

    def load_fills(self, run_id: int) -> list[tuple[str, str, float, float, float]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ts, side, size, fill_price, fee_paid
                FROM fills
                WHERE run_id = ?
                ORDER BY ts
                """,
                (run_id,),
            ).fetchall()
        return [(str(ts), str(side), float(size), float(fill_price), float(fee)) for ts, side, size, fill_price, fee in rows]
