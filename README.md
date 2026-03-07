# Automated Trading Platform

A configurable, paper-trading system for stocks, forex, and crypto.

## Purpose

This project is a starter framework for algorithmic trading experiments. It helps you:
- run strategy logic on live polled market data or CSV replay,
- apply basic risk checks before simulated execution,
- track portfolio cash, position, and equity,
- estimate next-session open with a lightweight prediction mode.

It is designed for education, prototyping, and system validation before any real-money integration.

## Disclaimer

This software is for educational and paper-trading use only. Do not use it for live capital without proper compliance, risk controls, monitoring, and broker-certified execution.

## What The System Does

- Event-driven trading engine
- Strategy: MA crossover + optional RSI/Bollinger/MACD confirmations
- Advanced mode: multi-factor scoring (trend, momentum, breakout, volatility regime, volume confirmation)
- Risk controls: position limit, order notional limit, drawdown guard
- Advanced risk guards: exposure cap, volatility spike filter, cash-buffer guard, short enable/disable
- Paper execution model: slippage + fee simulation
- Portfolio accounting: cash, units, equity, peak equity
- Data sources:
  - TradingView scanner polling (`tradingview`)
  - CSV historical replay (`csv`)
- Prediction mode (`--predict-next-open`) using TradingView free scanner fields

## Architecture

- `trading_system/main.py`: CLI entrypoint and mode routing
- `trading_system/engine.py`: orchestration loop
- `trading_system/data/feed.py`: TradingView polling and CSV replay feeds
- `trading_system/strategy/moving_average.py`: signal generation
- `trading_system/risk/basic.py`: pre-trade validation
- `trading_system/execution/paper.py`: simulated fill model
- `trading_system/portfolio/manager.py`: portfolio state updates
- `trading_system/config.py`: typed config loader
- `trading_system/predict/opening.py`: next-open prediction logic
- `trading_system/storage/sqlite_store.py`: persistent SQLite run/fill/equity storage
- `trading_system/analytics/backtest.py`: backtesting metrics/report generation
- `config.example.json`: base runtime config
- `sample_data/bars.csv`: sample replay data

## Requirements

- Python 3.11+
- Internet access for TradingView modes
- Windows PowerShell examples are shown below

## Quick Commands

Use these copy-paste commands from project root (`C:\Users\ricky\OneDrive\Documents\New project`).

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### Run Modes

```powershell
# Live mode (uses config data.source=tradingview)
python -m trading_system.main --config config.example.json

# CSV replay mode
python -m trading_system.main --source csv --data sample_data/bars.csv --config config.example.json

# Short smoke run
python -m trading_system.main --config config.example.json --max-bars 10

# CSV run with persistent DB + analytics markdown report
python -m trading_system.main --source csv --data sample_data/bars.csv --config config.example.json --db-path trading_runs.db --report-path backtest_report.md --run-name my_backtest
```

### Prediction Mode

```powershell
# Predict next open using config symbol
python -m trading_system.main --config config.example.json --predict-next-open

# With custom windows
python -m trading_system.main --config config.example.json --predict-next-open --lookback-days 180 --gap-window 30
```

### Common Asset Commands

```powershell
# NSE stock (example: TCS)
python -c "from trading_system.predict.opening import predict_next_open as p; print(p(screener='india', exchange='NSE', symbol='TCS'))"

# Forex (EURUSD)
python -c "from trading_system.predict.opening import predict_next_open as p; print(p(screener='forex', exchange='FX_IDC', symbol='EURUSD'))"

# Crypto (BTCUSDT)
python -c "from trading_system.predict.opening import predict_next_open as p; print(p(screener='crypto', exchange='BINANCE', symbol='BTCUSDT'))"
```

### Testing

```powershell
pytest -q
```

## Persistent Storage And Analytics

- By default, runs are persisted to SQLite (`trading_runs.db`) unless `--disable-storage` is set.
- Stored entities:
  - run metadata and final portfolio state
  - per-bar equity snapshots
  - fill history with score/confidence/regime/reason
- Analytics are computed after each trading run and printed to terminal:
  - trade count, win rate, max drawdown, return, sharpe-like, profit factor
- To export analytics:
  - markdown report: `--report-path backtest_report.md`
  - json report: `--report-path backtest_report.json`

## Quick Start (Step-by-Step)

1. Open terminal in project root.
2. Create virtual environment:

```powershell
python -m venv .venv
```

3. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Install project:

```powershell
pip install -e .
```

5. Run a short CSV smoke test:

```powershell
python -m trading_system.main --source csv --data sample_data/bars.csv --config config.example.json --max-bars 50
```

If you see final cash/equity/units output, setup is working.

## Configuration

All runtime behavior is controlled by JSON config.

### Top-Level

- `symbol`: internal strategy/risk symbol label
- `starting_cash`: initial cash
- `max_position_units`: max absolute position size
- `max_notional_per_order`: max notional allowed per order
- `max_drawdown_pct`: stop new trades after drawdown breach
- `allow_short`: enable/disable shorting
- `max_exposure_pct`: cap total exposure vs equity
- `max_bar_range_pct`: reject trades during extreme candle ranges
- `min_cash_buffer_pct`: keep minimum cash buffer
- `fee_bps`, `slippage_bps`: execution cost model

### Data Block (`data`)

- `source`: `tradingview` or `csv`
- `csv_path`: file path for CSV mode
- `tradingview_screener`: e.g. `india`, `crypto`, `forex`
- `tradingview_exchange`: e.g. `NSE`, `BINANCE`, `FX_IDC`
- `tradingview_symbol`: e.g. `RELIANCE`, `BTCUSDT`, `EURUSD`
- `poll_seconds`: polling interval
- `max_bars`: stop after N bars (or `null` for continuous)
- `emit_on_same_timestamp`: whether repeated same-candle emissions are allowed
- `request_timeout_seconds`: HTTP timeout
- `retry_delay_seconds`: retry backoff

### Strategy Block (`strategy`)

- MA crossover: `short_window`, `long_window`
- Strategy mode: `mode` (`advanced` or `classic`)
- Position sizing: `order_size_units`
- RSI: `use_rsi`, `rsi_period`, `rsi_oversold`, `rsi_overbought`
- Bollinger: `use_bollinger`, `bollinger_window`, `bollinger_stddev`
- MACD: `use_macd`, `macd_fast`, `macd_slow`, `macd_signal`
- Confirmation gate: `min_confirmations`
- Advanced trend/momentum: `trend_ema_fast`, `trend_ema_slow`, `momentum_window`, `breakout_window`
- Advanced volatility/sizing: `atr_period`, `target_volatility_pct`, `min_signal_score`, `max_size_multiplier`
- Advanced filters: `use_volume_confirmation`, `volume_window`, `regime_trend_threshold`, `regime_chop_threshold`
- Signal pacing: `signal_cooldown_bars`, `score_hysteresis`

## How To Use

### 1) Live TradingView Polling

```powershell
python -m trading_system.main --config config.example.json
```

This is continuous mode unless `max_bars` is set.

### 2) CSV Replay

```powershell
python -m trading_system.main --source csv --data sample_data/bars.csv --config config.example.json
```

### 3) Short Validation Run

```powershell
python -m trading_system.main --config config.example.json --max-bars 10
```

## Asset Class Examples

### India Stock (NSE)

```json
"data": {
  "source": "tradingview",
  "tradingview_screener": "india",
  "tradingview_exchange": "NSE",
  "tradingview_symbol": "TCS"
}
```

### Forex

```json
"data": {
  "source": "tradingview",
  "tradingview_screener": "forex",
  "tradingview_exchange": "FX_IDC",
  "tradingview_symbol": "EURUSD"
}
```

### Crypto

```json
"data": {
  "source": "tradingview",
  "tradingview_screener": "crypto",
  "tradingview_exchange": "BINANCE",
  "tradingview_symbol": "BTCUSDT"
}
```

## Prediction Mode (Next Open)

Run:

```powershell
python -m trading_system.main --config config.example.json --predict-next-open
```

Output includes:
- reference close
- predicted next open
- 1-sigma range
- mean gap percent and gap volatility
- number of observations used

Optional parameters:

```powershell
python -m trading_system.main --config config.example.json --predict-next-open --lookback-days 180 --gap-window 30
```

Notes:
- Prediction mode uses TradingView free scanner fields.
- Available shifted daily history is limited on free fields, so observations may be small.

## Data Format For CSV Mode

CSV must have header exactly:

```text
timestamp,open,high,low,close,volume
```

Timestamp example:

```text
2026-03-06T09:15:00
```

Encoding recommendation:
- UTF-8 without BOM

## Troubleshooting

### No output in live mode

- Expected if no trade/error is triggered.
- Use `--max-bars` for short visible runs.

### Process times out in assistant-run terminal

- Live mode is long-running.
- Run directly in your own terminal for continuous output.

### JSON/CSV parsing errors

- Ensure files are UTF-8 without BOM.
- Verify CSV headers exactly match required names.

### TradingView returns no rows for symbol

- Confirm exact `screener`, `exchange`, `symbol` combination from TradingView.
- Not all symbols are always available from scanner endpoint.

## Testing

If dev dependencies are installed:

```powershell
pytest -q
```

## Known Limitations

- TradingView scanner endpoint behavior is unofficial and can change.
- Paper execution only (no real broker API integration).
- No persistent DB storage for orders/fills/state.
- Single-process architecture.
- Prediction mode is a simple statistical estimate, not a guaranteed forecast.

## Future Scope

### Near-Term

- Better symbol discovery/normalization for scanner endpoints
- Improved observability (heartbeat logs, structured logs, diagnostics)
- Stronger input validation (encoding, schema checks, config lints)
- Backtest report output (trade list, drawdown curve, metrics)

### Medium-Term

- Broker integration layer with idempotent order routing
- Persistent storage for positions, fills, and audit trails
- Strategy registry and multi-strategy execution
- Portfolio-level risk and circuit breakers

### Long-Term

- Walk-forward optimization and parameter governance
- Event streaming architecture for scale
- Monitoring dashboards and alerting
- Deployment hardening (secrets, RBAC, CI/CD controls)

## Suggested First Workflow

1. Run CSV mode with sample data.
2. Adjust strategy parameters in config.
3. Run short TradingView mode with `max_bars`.
4. Validate prediction output across stock/forex/crypto.
5. Add your own CSV data and compare behavior.
6. Only then start production-hardening tasks.
