# 🤖 Baymax Core: Quickstart Guide

Welcome to the Baymax Core Trading Engine. This guide will walk you through exactly how to set up, optimize, and run your institutional-grade algorithmic trading bot.

---

## Step 1: Configure Your API Credentials

Before the bot can stream live market data or place trades, you must provide it with your broker's API credentials. 

1. Open the `.env` file in the root directory.
2. Log into your [DhanHQ Dashboard](https://hq.dhan.co). Ensure you are in the **Live Trading** environment (NOT the Sandbox).
3. Generate a new API token. **Ensure the "Live Market Feed / Data API" subscription is activated on your account.**
4. Paste the credentials into your `.env` file:
```env
DHAN_ACCESS_TOKEN=eyJ0eXAiOiJKV... (your massive token string here)
DHAN_CLIENT_ID=1111214059
```

---

## Step 2: Choose Your Stocks & Risk Limits

The brain of your bot is controlled by the `config_multi.json` file. Open it and define your trading parameters.

### Adding Stocks to Trade
Find the `symbols` array at the top of the file. You can add any NSE/BSE Equity or Index here.
```json
"symbols": ["TCS", "RELIANCE", "HDFCBANK", "NIFTY 50"],
```

### Setting Your Risk Constraints
The bot uses dynamic volatility sizing to protect your capital. Adjust these critical limits:
* `"starting_cash"`: How much virtual/real money the portfolio has.
* `"max_drawdown_pct": 0.15`: The bot will completely halt trading if your account loses 15% of its value.
* `"position_sizing.risk_pct": 0.02`: The bot will dynamically buy enough shares so that if your stop-loss is hit, you only lose exactly 2% of your total capital.

---

## Step 3: Run the Machine Learning Optimizer (Optional, but Recommended)

By default, the bot uses a standard Supertrend (10, 3.0). However, every stock behaves differently. You can use the offline Walk-Forward Optimizer to mathematically find the perfect parameters for a specific stock.

1. Download the last 30 days of 1-minute historical data for a stock (e.g., TCS) as a CSV file (`tcs.csv`). Ensure headers are: `timestamp,open,high,low,close,volume`.
2. Open your terminal and run the optimizer:
```powershell
python -m trading_system.analytics.optimizer --symbol TCS --data tcs.csv
```
3. The bot will simulate thousands of trades in the background and save the most profitable parameters to a file called `optimized_params.json`.
4. When the live bot starts, it will automatically detect this file and inject the customized settings exclusively for TCS!

---

## Step 4: Start the Live Trading Engine

Once your credentials are set and your config is ready, it is time to unleash the bot on the live market.

1. Open your terminal in the project directory.
2. Ensure you have activated your virtual environment:
```powershell
.\.venv\Scripts\activate
```
3. Run the engine using the Dhan Live WebSocket:
```powershell
python -m trading_system.main --config config_multi.json --source dhan_v2
```

### What to Expect Upon Startup:
* The bot will download/cache the latest **Scrip Master** from Dhan containing over 247,000 instruments.
* It will connect to the `wss://api-feed.dhan.co` WebSocket.
* It will establish the **AI Regime Classifier** and begin calculating the Choppiness Index in the background.
* It will silently aggregate incoming 1-minute data into 5-minute macro candles for **Multi-Timeframe Alignment**.

If a trade signal occurs during a highly choppy market, you will see a console log stating the trade was blocked. If a massive volume spike occurs, you will see a log stating the chop-filter was overridden.

> [!WARNING]
> Do **NOT** log into the Dhan website or mobile app simultaneously while the bot is running. Dhan only permits one active session at a time, and opening the app on your phone will forcibly disconnect your trading bot from the live data feed!
