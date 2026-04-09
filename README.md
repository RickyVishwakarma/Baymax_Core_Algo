# 🤖 Baymax Core Algo — Automated Multi-Stock Trading Engine

> A production-grade, multi-stock algorithmic trading platform for the Indian equity market (NSE/BSE).
> Paper-trades and live-trades across the Nifty 50 with dynamic trailing stop-losses, AI regime filtering,
> 5 pluggable strategies, 7-factor risk management, and parallel grid-search optimisation.
> **Zero external ML dependencies** — pure Python, runs anywhere.

---

## Table of Contents

- [Features at a Glance](#features-at-a-glance)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration Guide](#configuration-guide)
  - [Full Config Reference](#full-config-reference)
  - [Example Configs](#example-configs)
- [CLI Reference — Every Command](#cli-reference--every-command)
  - [Live Multi-Stock Paper Trading](#1-live-multi-stock-paper-trading)
  - [Single-Stock Paper Trading](#2-single-stock-paper-trading)
  - [Fetch a Quick Price Quote](#3-fetch-a-quick-price-quote)
  - [Predict Next Market Open](#4-predict-next-market-open)
  - [Backtest from CSV](#5-backtest-from-csv)
  - [Grid-Search Optimisation](#6-grid-search-optimisation)
  - [Stress Test (Synthetic)](#7-stress-test-synthetic)
  - [Limit Bars for Testing](#8-limit-bars-for-testing)
  - [Disable Database Storage](#9-disable-database-storage)
  - [Export Analytics Report](#10-export-analytics-report)
  - [Live Trading via Groww](#11-live-trading-via-groww-api)
- [Strategy Guide](#strategy-guide)
  - [Supertrend (Recommended)](#1-supertrend-recommended)
  - [Moving Average Cross](#2-moving-average-crossover)
  - [Mean Reversion (RSI)](#3-mean-reversion-rsi)
  - [Breakout](#4-breakout)
  - [VWAP](#5-vwap)
- [Risk Management](#risk-management)
  - [Per-Order Checks](#per-order-checks-7-factors)
  - [Dynamic Trailing Stop-Loss](#dynamic-trailing-stop-loss)
  - [Global Kill-Switch](#global-kill-switch)
- [Portfolio Manager](#portfolio-manager)
- [Execution Modes](#execution-modes)
- [Data Persistence (SQLite)](#data-persistence-sqlite)
- [Architecture Deep Dive](#architecture-deep-dive)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Security Warning](#security-warning)

---

## Features at a Glance

| Feature | Status |
|---------|--------|
| Multi-stock basket scanning (Nifty 50) | ✅ Live |
| 5 pluggable trading strategies | ✅ Live |
| Dynamic trailing stop-loss (per-position) | ✅ Live |
| AI/ML Regime Classifier (Choppiness Index + ADX) | ✅ Live |
| 7-factor risk validation on every order | ✅ Live |
| Paper trading with realistic fees + slippage | ✅ Live |
| TradingView real-time data feed (batch) | ✅ Live |
| CSV historical data backtesting | ✅ Live |
| Parallel grid-search parameter optimizer | ✅ Live |
| Next-open statistical price prediction | ✅ Live |
| SQLite trade/run persistence | ✅ Live |
| Markdown and JSON analytics reports | ✅ Live |
| Groww brokerage live execution | ⚠️ Ready (awaiting API subscription) |
| WebSocket real-time data feed | 🔜 Planned |
| Web dashboard UI | 🔜 Planned |
| Telegram/Discord alerts | 🔜 Planned |

---

## 2. Maturity Level Assessment

### Overall Level: **Advanced Retail / Early Institutional (L3 of 5)**

| Level | Description | Status |
|-------|-------------|--------|
| L1 — Beginner | Simple buy/sell scripts, no risk controls | — |
| L2 — Intermediate | Single stock, basic strategy, paper trade | — |
| **L3 — Advanced Retail** | **Multi-asset, real risk engine, ML filtering, optimizer** | **⭐ Current** |
| L4 — Early Institutional | WebSocket feeds, live execution, portfolio hedging | Next step |
| L5 — Full Institutional | Co-location, <1ms latency, SEBI registration | Hedge funds |

---

## Quick Start

### 1. Clone & Setup

```powershell
# Navigate to the project
cd "c:\Users\ricky\OneDrive\Documents\New project"

# Create a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install requests python-dotenv
```

### 2. Configure

The project uses externalized environment variables for security. **Never hardcode secrets in source code.**

1. Copy the example template:
   ```powershell
   cp .env.example .env
   ```
2. Open `.env` and enter your credentials:
   ```ini
   GROWW_API_KEY=eyJ...
   GROWW_API_SECRET=your_jwt_secret
   ```

> [!CAUTION]
> **SECURE YOUR SECRETS:** The `.env` file is ignored by Git (`.gitignore`) to prevent accidental leaks. If you accidentally committed your keys previously, ensure you rotate them immediately in the Groww Portal.

### 3. Run

```powershell
# Multi-stock paper trading (TCS, INFY, RELIANCE)
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_multi.json

# Quick price check
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_multi.json --quote-only
```

Press `Ctrl+C` at any time to gracefully stop the engine.

---

## Project Structure

```
New project/
│
├── .env                          # API secrets (never commit!)
├── config.json                   # Single-stock config template
├── config_multi.json             # Active multi-stock config (AI regime enabled)
├── param_grid.example.json       # Parameter grid for optimizer
├── test_multi_stock.py           # Multi-stock + trailing stop stress test
├── test_regime_classifier.py     # AI regime classifier test
├── trading_runs.db               # SQLite database (auto-created)
├── README.md                     # This documentation
│
└── trading_system/
    ├── __init__.py
    ├── models.py                 # Data classes: Bar, Signal, Fill, Position, etc.
    ├── config.py                 # Configuration schema + JSON loader
    ├── engine.py                 # TradingEngine: event loop + trailing stop + regime gate
    ├── main.py                   # CLI entry point (all commands)
    │
    ├── data/
    │   └── feed.py               # TradingView batch feed, CSV feed
    │
    ├── ml/                       # ← NEW: AI/ML layer
    │   ├── __init__.py
    │   └── regime.py             # RegimeClassifier (Choppiness Index + ADX, pure Python)
    │
    ├── strategy/
    │   ├── base.py               # Strategy abstract base class
    │   ├── registry.py           # StrategyRegistry (name → class factory)
    │   ├── supertrend.py         # ATR-based Supertrend
    │   ├── moving_average.py     # Fast/slow EMA crossover
    │   ├── mean_reversion.py     # RSI-based mean reversion
    │   ├── breakout.py           # N-period high/low breakout
    │   └── vwap.py               # Volume-Weighted Average Price
    │
    ├── risk/
    │   ├── base.py               # RiskManager abstract base
    │   └── basic.py              # BasicRiskManager (7-factor validation)
    │
    ├── portfolio/
    │   └── manager.py            # Multi-symbol position & equity tracker
    │
    ├── execution/
    │   ├── base.py               # ExecutionHandler abstract base
    │   ├── paper.py              # Paper trading (simulated fills)
    │   └── groww.py              # Live Groww API execution
    │
    ├── predict/
    │   └── opening.py            # Statistical next-open predictor
    │
    ├── analytics/
    │   ├── __init__.py           # Exports: build_backtest_report, report_to_markdown
    │   ├── backtest.py           # BacktestReport generation
    │   └── optimizer.py          # Grid-search parallel optimizer
    │
    └── storage/
        ├── __init__.py
        └── sqlite_store.py       # SQLiteRunStore: persistent run/bar/fill storage
```

---

## Configuration Guide

### Full Config Reference

Create a JSON file with any of these fields. All fields are optional — omitted fields use the defaults shown.

```json
{
  "_comment": "=== Portfolio & Risk ===",
  "symbols":                ["BTCUSDT"],
  "starting_cash":          100000.0,
  "max_position_units":     2.0,
  "max_notional_per_order": 15000.0,
  "max_drawdown_pct":       0.15,
  "trailing_stop_pct":      0.0,
  "allow_short":            true,
  "max_exposure_pct":       1.0,
  "max_bar_range_pct":      0.20,
  "min_cash_buffer_pct":    0.01,
  "fee_bps":                5.0,
  "slippage_bps":           3.0,

  "_comment2": "=== Execution ===",
  "execution": {
    "type": "paper"
  },

  "_comment3": "=== AI Regime Classifier (NEW) ===",
  "ml_regime": {
    "enabled":         false,
    "window":          14,
    "block_threshold": 0.35,
    "pass_threshold":  0.55,
    "ci_weight":       0.5
  },

  "_comment4": "=== Strategy ===",
  "strategy": {
    "name": "supertrend",
    "params": {
      "atr_period": 10,
      "multiplier": 3.0,
      "order_size_units": 1.0
    }
  },

  "_comment5": "=== Data Feed ===",
  "data": {
    "source":                    "tradingview",
    "tradingview_screener":      "india",
    "tradingview_exchange":      "NSE",
    "tradingview_symbols":       ["TCS", "INFY", "RELIANCE"],
    "poll_seconds":              5,
    "max_bars":                  null,
    "emit_on_same_timestamp":    true,
    "request_timeout_seconds":   15,
    "retry_delay_seconds":       3
  }
}
```

#### Config field explanations

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbols` | `list[str]` | `["BTCUSDT"]` | Symbols to trade (for metadata/storage) |
| `starting_cash` | `float` | `100000` | Starting paper portfolio in ₹ |
| `max_position_units` | `float` | `2.0` | Maximum shares held per stock |
| `max_notional_per_order` | `float` | `15000` | Maximum ₹ value of a single order |
| `max_drawdown_pct` | `float` | `0.15` | Global kill-switch: halt all trading at 15% drawdown |
| `trailing_stop_pct` | `float` | `0.0` | Trailing stop-loss % (0 = disabled, 0.05 = 5%) |
| `allow_short` | `bool` | `true` | Allow short-selling |
| `max_exposure_pct` | `float` | `1.0` | Max single-stock exposure as fraction of equity |
| `max_bar_range_pct` | `float` | `0.20` | Reject bars where (high-low)/close > 20% |
| `min_cash_buffer_pct` | `float` | `0.01` | Minimum cash reserve as % of equity |
| `fee_bps` | `float` | `5.0` | Brokerage fee in basis points |
| `slippage_bps` | `float` | `3.0` | Simulated order slippage in basis points |
| `execution.type` | `str` | `"paper"` | `"paper"` or `"groww"` |
| **`ml_regime.enabled`** | `bool` | `false` | Enable AI regime filter |
| **`ml_regime.window`** | `int` | `14` | Rolling lookback bars for CI and ADX |
| **`ml_regime.block_threshold`** | `float` | `0.35` | Score < threshold → block signal (choppy) |
| **`ml_regime.pass_threshold`** | `float` | `0.55` | Score ≥ threshold → pass signal (trending) |
| **`ml_regime.ci_weight`** | `float` | `0.5` | Blend: 0.5 = equal CI + ADX, 1.0 = CI only |
| `strategy.name` | `str` | `"moving_average"` | Strategy from registry |
| `strategy.params` | `dict` | `{}` | Strategy constructor keyword arguments |
| `data.source` | `str` | `"tradingview"` | `"tradingview"` or `"csv"` |
| `data.tradingview_screener` | `str` | `"crypto"` | `"india"` for NSE, `"crypto"` for Binance |
| `data.tradingview_exchange` | `str` | `"BINANCE"` | Exchange prefix: `"NSE"`, `"BSE"`, `"BINANCE"` |
| `data.tradingview_symbols` | `list[str]` | `["BTCUSDT"]` | Tickers to fetch in batch |
| `data.poll_seconds` | `int` | `5` | Polling interval in seconds |
| `data.max_bars` | `int\|null` | `null` | Stop after N bars (`null` = infinite) |
| `data.csv_path` | `str\|null` | `null` | Path to CSV historical data file |

### Example Configs

#### Multi-stock Nifty (current active config)

```json
{
  "symbols": ["TCS", "INFY", "RELIANCE"],
  "starting_cash": 100000.0,
  "max_position_units": 2.0,
  "max_notional_per_order": 15000.0,
  "max_drawdown_pct": 0.15,
  "max_exposure_pct": 0.50,
  "trailing_stop_pct": 0.05,
  "execution": { "type": "paper" },
  "ml_regime": {
    "enabled": true,
    "window": 14,
    "block_threshold": 0.35,
    "pass_threshold": 0.55,
    "ci_weight": 0.5
  },
  "strategy": {
    "name": "supertrend",
    "params": { "atr_period": 10, "multiplier": 3.0 }
  },
  "data": {
    "source": "tradingview",
    "tradingview_screener": "india",
    "tradingview_exchange": "NSE",
    "tradingview_symbols": ["TCS", "INFY", "RELIANCE"],
    "poll_seconds": 1
  }
}
```

#### Full Nifty 50 scanner

Change the symbols lists to include all 50 tickers:

```json
{
  "symbols": ["RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBI","BHARTIARTL","ITC","KOTAKBANK","LT","HCLTECH","AXISBANK","ASIANPAINT","MARUTI","SUNPHARMA","TITAN","BAJFINANCE","DMART","NESTLEIND","ULTRACEMCO","NTPC","WIPRO","M&M","POWERGRID","ONGC","JSWSTEEL","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","INDUSINDBK","BAJAJFINSV","TECHM","GRASIM","DIVISLAB","DRREDDY","CIPLA","BRITANNIA","APOLLOHOSP","EICHERMOT","SBILIFE","TATACONSUM","HEROMOTOCO","COALINDIA","BPCL","UPL","HINDALCO","BAJAJ-AUTO","LTIM"],
  "data": {
    "tradingview_symbols": ["RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","...all 50..."]
  }
}
```

#### CSV backtest config

```json
{
  "symbols": ["INFY"],
  "strategy": {
    "name": "mean_reversion",
    "params": { "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70 }
  },
  "data": {
    "source": "csv",
    "csv_path": "data/infy_2024.csv"
  }
}
```

CSV file format (required columns):
```csv
timestamp,open,high,low,close,volume
2024-01-02T09:15:00,1850.00,1865.50,1845.00,1860.25,125000
2024-01-02T09:16:00,1860.30,1862.00,1858.00,1861.50,89000
```

---

## CLI Reference — Every Command

All commands are run from the project root with the virtual environment activated.

### 1. Live Multi-Stock Paper Trading

Starts the engine with real-time TradingView data and paper-trades TCS, INFY, RELIANCE simultaneously with a 5% trailing stop-loss.

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_multi.json
```

The `-u` flag enables unbuffered output so you see log lines immediately.

### 2. Single-Stock Paper Trading

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config.json
```

### 3. Fetch a Quick Price Quote

Get the latest OHLCV quote for all configured symbols without trading:

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_multi.json --quote-only
```

**Output:**
```
Symbol: TCS
Timestamp (UTC): 2026-04-08T09:15:00
Open: 3450.50
High: 3465.00
Low: 3440.00
Close: 3458.75
Volume: 245000
---
Symbol: INFY
...
```

### 4. Predict Next Market Open

Statistically predicts the next session's opening price based on historical overnight gap patterns:

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config.json --predict-next-open
```

With custom lookback:

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config.json --predict-next-open --lookback-days 180 --gap-window 30
```

**Output:**
```
Symbol: INFY
Reference close: 1923.50
Predicted next open: 1925.12
Range (1-sigma): 1918.30 to 1931.94
Avg overnight gap (%): 0.0842
Gap volatility (%): 0.3510
Observations: 20
```

### 5. Backtest from CSV

Run the engine against historical CSV data:

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config my_config.json --source csv --data data/infy_2024.csv
```

### 6. Grid-Search Optimisation

Test thousands of strategy parameter combinations in parallel:

```powershell
.\.venv\Scripts\python.exe -m trading_system.analytics.optimizer ^
  --config config.json ^
  --data data/infy_2024.csv ^
  --grid param_grid.example.json ^
  --workers 0 ^
  --top-n 10
```

| Flag | Description |
|------|-------------|
| `--config` | Base config (strategy name, risk params) |
| `--data` | CSV file with historical bars |
| `--grid` | JSON parameter grid (see below) |
| `--workers 0` | Use all CPU cores (default) |
| `--top-n 10` | Show best 10 results |

**Example parameter grid (`param_grid.example.json`):**
```json
{
  "short_window": [5, 10, 15],
  "long_window": [20, 30, 40],
  "rsi_oversold": [30, 35],
  "rsi_overbought": [65, 70]
}
```
This generates `3 × 3 × 2 × 2 = 36` parameter combinations tested in parallel.

**Supertrend grid example:**
```json
{
  "atr_period": [7, 10, 14, 20],
  "multiplier": [1.5, 2.0, 3.0, 4.0]
}
```
This generates `4 × 4 = 16` backtests.

**Output:**
```
--- Top 10 Results (Sorted by Sharpe Ratio) ---
#1
  Params: {'atr_period': 10, 'multiplier': 3.0}
  Sharpe: 1.420 | Profit Factor: 2.150
  Return: 12.34% | Max DD: 3.21%
  Trades: 47 | Win Rate: 58.3%
```

### 7. Stress Tests (Synthetic)

#### Multi-stock engine + trailing stop test

```powershell
.\.venv\Scripts\python.exe test_multi_stock.py
```

**Output:**
```
=======================================
STARTING MULTI-STOCK ENGINE STRESS TEST
=======================================
[INFO] signal symbol=TCS side=BUY ...
[WARNING] trailing_stop symbol=TCS side=SELL drop=0.0280
[INFO] fill symbol=TCS side=SELL ...
=======================================
TEST COMPLETED. FINAL PORTFOLIO STATUS:
=======================================
Total Portfolio Equity: Rs 100073.46
Total Available Cash:   Rs 100073.46
Position -> TCS        | Units: 0.0 | Avg Entry: Rs 0.00
```

#### AI Regime Classifier test

Runs two synthetic scenarios: choppy oscillation vs steady trend. Verifies the classifier blocks noisy signals and passes trending ones.

```powershell
.\.venv\Scripts\python.exe test_regime_classifier.py
```

**Output:**
```
═══════════════════════════════════════════════════════
  AI REGIME CLASSIFIER — ENGINE INTEGRATION TEST
═══════════════════════════════════════════════════════

─── Unit Test: RegimeClassifier in isolation ───
  CHOPPY  market  CI=92.1  ADX=3.8   score=0.000  regime=choppy
  TRENDING market CI=8.5   ADX=100.0 score=1.000  regime=trending
  ✅ Classifier isolation tests passed.

─── Engine Integration Results ───
  CHOPPY  market:  14 fills  (AI should BLOCK most signals)
  TRENDING market:  50 fills  (AI should PASS signals through)

  ✅ PASSED — Regime classifier is correctly throttling choppy signals.
     Blocked 36 out of 50 choppy signals.
     Permitted 50 out of 50 trending signals.
═══════════════════════════════════════════════════════
```

### 8. Limit Bars for Testing

Stop after receiving N price bars (useful for quick tests):

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_multi.json --max-bars 50
```

### 9. Disable Database Storage

Run without writing to SQLite:

```powershell
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_multi.json --disable-storage
```

### 10. Export Analytics Report

Generate a markdown or JSON analytics report after a run:

```powershell
# Markdown report
.\.venv\Scripts\python.exe -u trading_system/main.py --config config.json --source csv --data data.csv --report-path report.md

# JSON report
.\.venv\Scripts\python.exe -u trading_system/main.py --config config.json --source csv --data data.csv --report-path report.json
```

### 11. Live Trading via Groww API

⚠️ **WARNING: This uses real money. Triple-check your config.**

```powershell
# 1. Set up .env with your Groww credentials
# 2. Set execution type in your config JSON:
#    "execution": { "type": "groww" }
# 3. Run
.\.venv\Scripts\python.exe -u trading_system/main.py --config config_live.json
```

### Complete CLI Flag Reference

```
usage: main.py [-h] [--config CONFIG] [--source {csv,tradingview}]
               [--data DATA] [--max-bars MAX_BARS] [--predict-next-open]
               [--lookback-days LOOKBACK_DAYS] [--gap-window GAP_WINDOW]
               [--quote-only] [--db-path DB_PATH] [--disable-storage]
               [--report-path REPORT_PATH] [--run-name RUN_NAME]
```

| Flag | Description |
|------|-------------|
| `--config` | Path to JSON configuration file |
| `--source` | Override data source: `csv` or `tradingview` |
| `--data` | CSV file path (when `--source csv`) |
| `--max-bars` | Stop after N bars |
| `--predict-next-open` | Predict next session open price and exit |
| `--lookback-days` | History window for prediction (default: 120) |
| `--gap-window` | Recent gap samples for prediction (default: 20) |
| `--quote-only` | Fetch latest OHLCV and exit (no trading) |
| `--db-path` | SQLite database path (default: `trading_runs.db`) |
| `--disable-storage` | Don't persist run data to SQLite |
| `--report-path` | Write analytics report to `.md` or `.json` |
| `--run-name` | Optional label for this run in the database |

---

## Strategy Guide

### 1. Supertrend (Recommended)

**Config name:** `"supertrend"`

An ATR-based trend-following strategy. Calculates dynamic upper/lower bands around the price and issues signals when the trend flips.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `atr_period` | `int` | `10` | Lookback periods for Average True Range |
| `multiplier` | `float` | `3.0` | Band width = `ATR × multiplier` |
| `order_size_units` | `float` | `0.1` | Shares per trade |

**Signals:**
- **BUY** → Price closes above the upper band (uptrend flip)
- **SELL** → Price closes below the lower band (downtrend flip)

```json
"strategy": {
  "name": "supertrend",
  "params": { "atr_period": 10, "multiplier": 3.0, "order_size_units": 1.0 }
}
```

### 2. Moving Average Crossover

**Config name:** `"moving_average"`

Classic fast/slow EMA crossover with optional RSI filtering.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `short_window` | `int` | `10` | Fast EMA period |
| `long_window` | `int` | `30` | Slow EMA period |
| `order_size_units` | `float` | `0.1` | Shares per trade |

**Signals:**
- **BUY** → Fast EMA crosses above slow EMA
- **SELL** → Fast EMA crosses below slow EMA

```json
"strategy": {
  "name": "moving_average",
  "params": { "short_window": 10, "long_window": 30 }
}
```

### 3. Mean Reversion (RSI)

**Config name:** `"mean_reversion"`

Relative Strength Index based strategy that buys oversold conditions and sells overbought.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rsi_period` | `int` | `14` | RSI calculation period |
| `rsi_oversold` | `float` | `30.0` | Buy threshold |
| `rsi_overbought` | `float` | `70.0` | Sell threshold |
| `order_size_units` | `float` | `0.1` | Shares per trade |

**Signals:**
- **BUY** → RSI crosses below `rsi_oversold` (stock is beaten down)
- **SELL** → RSI crosses above `rsi_overbought` (stock is overheated)

```json
"strategy": {
  "name": "mean_reversion",
  "params": { "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70 }
}
```

### 4. Breakout

**Config name:** `"breakout"`

N-period high/low channel breakout. Buys on new highs, sells on new lows.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_window` | `int` | `20` | Historical high/low lookback period |
| `order_size_units` | `float` | `0.1` | Shares per trade |

**Signals:**
- **BUY** → Close exceeds the highest high of the last N bars
- **SELL** → Close drops below the lowest low of the last N bars

```json
"strategy": {
  "name": "breakout",
  "params": { "lookback_window": 20 }
}
```

### 5. VWAP

**Config name:** `"vwap"`

Volume-Weighted Average Price strategy. Resets daily. Buys when price crosses above VWAP, sells when it crosses below.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `order_size_units` | `float` | `0.1` | Shares per trade |

**Signals:**
- **BUY** → Price crosses above the session VWAP
- **SELL** → Price crosses below the session VWAP

```json
"strategy": { "name": "vwap", "params": {} }
```

---

## Risk Management

### Per-Order Checks (7 Factors)

Every signal passes through `BasicRiskManager.validate()` before an order is placed. **Any** failing check rejects the trade.

| # | Check | Config Field | Reject Code |
|---|-------|-------------|-------------|
| 1 | Order value exceeds limit | `max_notional_per_order` | `order_notional_limit` |
| 2 | Short-selling attempted when disabled | `allow_short` | `short_not_allowed` |
| 3 | Position size would exceed cap | `max_position_units` | `position_limit` |
| 4 | Portfolio drawdown has exceeded threshold | `max_drawdown_pct` | `max_drawdown_triggered` |
| 5 | Current bar is too volatile | `max_bar_range_pct` | `bar_range_too_high` |
| 6 | Single-stock exposure too high | `max_exposure_pct` | `exposure_limit` |
| 7 | Cash buffer would be violated | `min_cash_buffer_pct` | `cash_buffer_limit` |

### Dynamic Trailing Stop-Loss

When `trailing_stop_pct > 0`, the engine continuously tracks the **highest price** (for long positions) or **lowest price** (for short positions) since the trade was opened.

**How it works:**
1. You buy TCS at ₹3400. `peak_price = 3400`
2. TCS rises to ₹3600. `peak_price` silently updates to ₹3600
3. TCS drops to ₹3420. Drop from peak = `(3600 - 3420) / 3600 = 5.0%`
4. If `trailing_stop_pct = 0.05`, the engine **immediately force-sells** all TCS units

The trailing stop **overrides** the strategy — it fires before the strategy even evaluates the bar.

```json
"trailing_stop_pct": 0.05
```

### Global Kill-Switch

If total portfolio equity drops by more than `max_drawdown_pct` from the all-time peak equity, **ALL** new trades across every symbol in the basket are blocked until the portfolio recovers.

---

## Portfolio Manager

The `PortfolioManager` tracks the complete financial state:

- **`positions: dict[str, Position]`** — Independent position per symbol with `units`, `avg_entry_price`, and `peak_price`
- **`current_prices: dict[str, float]`** — Latest known price per symbol
- **`state.cash`** — Available cash after all trades and fees
- **`state.equity`** — Total portfolio value: `cash + Σ(units × price)`
- **`state.peak_equity`** — All-time high equity (drives drawdown calculation)

Each symbol is fully isolated. TCS crashing 10% does not affect the INFY position's trailing stop calculation.

---

## Execution Modes

### Paper Mode (default)

Simulates order fills with realistic cost modelling:

```
fill_price = bar.close × (1 ± slippage_bps / 10000)
fee_paid   = |size × fill_price| × (fee_bps / 10000)
```

- BUY orders get slightly worse price (positive slippage)
- SELL orders get slightly worse price (negative slippage)

### Groww Mode (live)

Routes real orders through the Groww Trading API. Requires `.env` credentials and an active API subscription.

Set `"execution": { "type": "groww" }` in config.

---

## Data Persistence (SQLite)

Every run is automatically stored in `trading_runs.db` (configurable via `--db-path`).

Stored data:
- **Runs** — start/end time, strategy name, symbols, final equity, status
- **Bars** — timestamp, symbol, close price, equity, cash, position units
- **Fills** — timestamp, symbol, side, size, fill price, fee, equity after

Disable with `--disable-storage`.

---

## Architecture Deep Dive

### Bar Processing Pipeline (per market tick)

```
┌─────────────────────┐
│  TradingView Batch  │   1 HTTP request fetches ALL symbols
│  POST /scan         │
└─────────┬───────────┘
          │ list[MarketBar]
          ▼
┌─────────────────────┐
│  Deduplication      │   Skip if OHLCV unchanged since last poll
│  _last_bar_tuples   │
└─────────┬───────────┘
          │ per bar
          ▼
┌─────────────────────────────────────────────────────┐
│  TradingEngine.run()                                │
│                                                     │
│  Step 1: portfolio.mark_to_market(bar)              │
│          → updates price, equity, peak_price        │
│                                                     │
│  Step 2: on_bar_callback (UI/logging hook)          │
│                                                     │
│  Step 3: Get/create strategy for this symbol        │
│          → Factory spawns isolated model per ticker │
│                                                     │
│  Step 4: TRAILING STOP CHECK (always active)        │
│          → If drop ≥ trailing_stop_pct:             │
│            force-emit SELL, bypass strategy & AI    │
│                                                     │
│  Step 5: strategy.on_bar(bar) → Signal | None       │
│                                                     │
│  Step 5.5: ★ AI REGIME GATE (if enabled) ★         │
│          → RegimeClassifier updates Choppiness      │
│            Index + ADX from recent bar history      │
│          → score < block_threshold: BLOCK signal    │
│          → score ≥ pass_threshold: PASS signal      │
│          → (trailing stop signals skip this gate)   │
│                                                     │
│  Step 6: risk_manager.validate(order) → pass/reject │
│          → 7-factor check (notional, exposure, DD…) │
│                                                     │
│  Step 7: execution.execute(order, bar) → Fill       │
│                                                     │
│  Step 8: portfolio.apply_fill(fill)                 │
│          → update cash, position, peak_price        │
│                                                     │
│  Step 9: on_fill_callback (notification hook)       │
└─────────────────────────────────────────────────────┘
```

### Multi-Symbol Isolation

The engine uses a **strategy factory pattern**. For each symbol encountered in the data stream, it spawns a completely independent strategy instance:

```python
self.strategies: dict[str, Strategy] = {}

# On each bar:
if bar.symbol not in self.strategies:
    self.strategies[bar.symbol] = self.strategy_factory()
strategy = self.strategies[bar.symbol]
```

This means the Supertrend ATR calculation for TCS is completely separate from INFY's. No cross-contamination. Each stock has its own mathematical state.

---

## Environment Variables & Security

| Variable | Required | Description |
|----------|----------|-------------|
| `GROWW_API_KEY` | Only for live trading | Groww API JWT key |
| `GROWW_API_SECRET` | Only for live trading | Groww API JWT secret |

### Security Best Practices

1. **`.env` and `.gitignore`**: The `.env` file containing your real keys must never be committed to Git. The project is pre-configured with a `.gitignore` that excludes `.env`.
2. **Rotating Secrets**: If your GitGuardian alert fires, it means your keys are public. Go to your Groww Developer portal, **revoke the old keys**, and generate new ones.
3. **Template**: Use [.env.example](file:///c:/Users/ricky/OneDrive/Documents/New%20project/.env.example) to share required variable names without their values.

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `ModuleNotFoundError: requests` | Missing dependency | `pip install requests python-dotenv` |
| `403 Forbidden` from Groww | No API subscription | Subscribe to Groww Trading API |
| No output in terminal | Prices haven't changed | Normal during market close or polling dedup |
| `risk_reject ... position_limit` | Position cap reached | Increase `max_position_units` in config |
| `risk_reject ... cash_buffer_limit` | Not enough cash | Increase `starting_cash` or reduce `min_cash_buffer_pct` |
| `risk_reject ... max_drawdown_triggered` | Global kill-switch hit | Portfolio has fallen > `max_drawdown_pct` from peak |
| `regime_block symbol=... regime=choppy` | AI filter blocked a signal | Normal — market is choppy. Disable with `"enabled": false` in `ml_regime` |
| Engine exits immediately | `max_bars` set too low | Remove or increase `max_bars` in data config |

---

## Roadmap

| Priority | Feature | Status | Description |
|----------|---------|--------|-------------|
| ✅ Done | **Multi-Stock Basket Scanner** | ✅ Live | Scans 50 symbols simultaneously via batch TradingView API |
| ✅ Done | **Dynamic Trailing Stop-Loss** | ✅ Live | Per-position peak_price tracking with profit-lock circuit breaker |
| ✅ Done | **AI Regime Classifier** | ✅ Live | Choppiness Index + ADX, pure Python, no external dependencies |
| 🔴 P0 | **Web Dashboard** | 🔜 Planned | Real-time React/Next.js UI with candlestick charts, equity curve, and position table |
| 🟡 P1 | **WebSocket Data Feed** | 🔜 Planned | Replace polling with persistent WebSocket for <50ms latency |
| 🟡 P1 | **Telegram/Discord Alerts** | 🔜 Planned | Push notifications on fills, trailing stop triggers, and daily summaries |
| 🟢 P2 | **Dynamic Position Sizing** | 🔜 Planned | Risk exactly ₹X per trade instead of N units |
| 🟢 P2 | **Re-entry Cooldown** | 🔜 Planned | Prevent rapid re-entry after trailing stop fires |

### WebSocket Provider Comparison (for P1 upgrade)

When ready, the WebSocket feed can be implemented for any of these providers
without changing any strategy, risk, or portfolio code — only the data layer changes:

| Provider | Latency | Cost | Free Tier | Recommended For |
|----------|---------|------|-----------|----------------|
| **Zerodha Kite** | ~10ms | ₹2,000/mo | ❌ No | Enterprise / HFT |
| **Dhan API** | ~50ms | Free | ✅ Yes | Best free option |
| **Upstox v2** | ~80ms | Free | ✅ Yes | Alternative free |
| **Angel One** | ~100ms | Free | ✅ Yes | Beginner-friendly |
| TradingView (current) | 1,000–5,000ms | Free | ✅ Yes | Testing / paper only |

---

## Security Warning

> ⚠️ **This system is fully capable of executing real-money trades.**
> Always verify `"execution": { "type": "paper" }` in your config before running.
> Never commit your `.env` file. Add it to `.gitignore`.

---

*Built with Python 3.12 • Dependencies: `requests`, `python-dotenv` • Zero ML dependencies (pure stdlib)*
