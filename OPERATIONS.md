# Operations Guide: Day-to-Day Trading

This guide ensures you maintain the highest level of reliability for your live trading sessions.

## 🕒 Market Schedule (IST)
- **09:00 AM**: Generate new Dhan Access Token via Dhan HQ Marketplace.
- **09:05 AM**: Update `.env` with the new token.
- **09:10 AM**: Run `check_dhan_balance.py` to verify connectivity.
- **09:14 AM**: Launch the engine in `dhan` execution mode.
- **09:15 AM**: Market Opens.
- **03:30 PM**: Market Closes. Press `Ctrl+C` to stop the engine manually.

## 🔑 Daily Token Refresh
1. Login to [Dhan HQ Marketplace](https://dhanhq.co/).
2. Navigate to **Access Token** section.
3. Copy the JWT string.
4. Edit `.env` in the bot root:
   ```ini
   DHAN_ACCESS_TOKEN=eyJ0...
   ```

## 📊 Monitoring the Engine
While the bot is running, it outputs log lines for every significant action.

| Log Prefix | Meaning | Action Required |
| :--- | :--- | :--- |
| `INFO regime` | AI is scanning the market | None (Monitoring) |
| `INFO signal` | Supertrend triggered a trade | None |
| `WARNING velocity_exit` | Momentum stalled, exiting trade | Check if profit was locked |
| `INFO fill` | Order executed at Dhan HQ | Verify in Dhan Mobile App |
| `CRITICAL execution_failed` | API connection lost | Verify internet/token immediately |

## 🧪 Status Checks
Run these scripts to verify system health without placing trades:
- **Balance Check**: `python check_dhan_balance.py`
- **Socket Check**: `python diagnose_ws.py`
- **Quote Check**: `python -m trading_system.main --config config_multi.json --source dhan_v2 --quote-only`

## 🚨 Emergency Shutdown
If you need to stop all trading immediately:
1. Press `Ctrl+C` in the terminal to stop the engine.
2. Login to your **Dhan Mobile App**.
3. Use the **"Exit All Positions"** feature in the portfolio tab to flatten any remaining risk manually.
