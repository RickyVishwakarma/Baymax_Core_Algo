# 🤖 Baymax Core Algo — Automated Multi-Stock Trading Engine

> A production-grade, multi-stock algorithmic trading platform for the National Stock Exchange (NSE). 
> Integrated with **Dhan HQ v2** for ultra-low latency execution and real-time WebSocket data.

---

## ⚡ Core Features
- **Dhan HQ v2 Native**: Full support for JWT-based auth and binary WebSocket feeds.
- **AI Regime Guard**: Uses Choppiness Index and ADX to block signals in sideways markets.
- **Velocity Exit Engine**: Automatically kills stagnant trades where price momentum has stalled.
- **7-Factor Risk Engine**: Institutional-grade pre-trade validation on every order.
- **Multi-Asset Architecture**: Run dozens of stocks in parallel on a single thread.
- **Zero External ML Dependencies**: Pure Python implementation of all indicators and models.

---

## 🚀 Quick Start (Production)

### 1. Daily Authentication
Dhan access tokens expire every 24 hours. Update your `.env` daily:
```bash
DHAN_CLIENT_ID="1111214059"
DHAN_ACCESS_TOKEN="eyJ0..." # Get from Dhan HQ Market Place
```

### 2. Live Market Execution
To run the engine in production mode using the **WebSocket Feed** and **Live Dhan Execution**:
```powershell
python -m trading_system.main --config config_multi.json --source dhan_v2 --execution dhan
```

### 3. Safety Verification (Paper-Trade)
Before going live, always run a session in paper-mode to verify signal quality:
```powershell
python -m trading_system.main --config config_multi.json --source dhan_v2 --execution paper
```

---

## 🛠 Project Structure
```text
.
├── .env                      # Production credentials (DHAN_ACCESS_TOKEN)
├── config_multi.json         # Master configuration for Nifty Basket
├── trading_runs.db           # SQLite database for trade persistence
└── trading_system/
    ├── engine.py             # Event loop & Velocity Exit logic
    ├── data/
    │   ├── dhan_socket.py    # Binary WebSocket client (NSE Real-time)
    │   └── dhan_manager.py   # NSE Scrip/Symbol mapping
    ├── execution/
    │   └── dhan.py           # Live Order Management (Dhan v2)
    ├── ml/
    │   └── regime.py         # AI Regime Classifier (CI + ADX)
    └── strategy/
        └── supertrend.py     # ATR-based Trend Following
```

---

## ⚙️ Configuration Reference
The `config_multi.json` controls the personality of the bot.

| Parameter | Meaning | Recommended |
| :--- | :--- | :--- |
| `min_velocity_threshold` | Min % profit growth per minute | `0.0001` (0.01%/min) |
| `trailing_stop_pct` | Max drop from peak price before exit | `0.03` (3%) |
| `block_threshold` | AI Score below this triggers a block | `0.35` (Filter chop) |
| `multiplier` | Supertrend volatility width | `3.0` (Institutional) |

---

## 📈 Analytics & Reporting
After every run, the bot generates a performance report:
```powershell
python -m trading_system.main --config config_multi.json --report-path my_trades.md
```

---

## 🛡️ Security & Reliability
- **Fault-Tolerant Sockets**: Automatic reconnection if the Dhan feed drops.
- **Circuit Breakers**: Global Max Drawdown (15%) halts the entire engine.
- **Grace Periods**: Velocity exits are ignored for the first 60 seconds of a trade.

---

## 🗺️ Documentation
- [OPERATIONS.md](OPERATIONS.md): Daily token refresh & Monitoring.
- [ALGO_WHITEPAPER.md](ALGO_WHITEPAPER.md): Strategy math & Indicator logic.
- [DEPLOYMENT.md](DEPLOYMENT.md): How to deploy Baymax on a Mumbai VPS.
