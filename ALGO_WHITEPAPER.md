# Algorithm Whitepaper: The Math of Baymax Core

This document explains the mathematical models and logic behind the Baymax Core Algo trading engine.

## 1. Execution Strategy: Supertrend (10, 3.0)
The Supertrend is a volatility-adjusted trend-following indicator.

- **Median Price**: `(High + Low) / 2`
- **Volatilty Buffer**: `ATR(10) * 3.0`
- **Upper Band**: `Median Price + Buffer`
- **Lower Band**: `Median Price - Buffer`

**Logic**: The bot enters a **LONG** position when the price closes above the Upper Band. It stays in that position until the price crosses below the dynamic Lower Band (Trailing Stop).

## 2. The AI Guard: Regime Classifier
The bot uses a multi-factor "Regime Score" (0.0 to 1.0) to filter out bad trades.

### Factor A: Choppiness Index (CI)
Measures the "Fractal Dimension" of price movement.
- `CI = 100 * LOG10( SUM(TrueRange, N) / (MAX(High, N) - MIN(Low, N)) ) / LOG10(N)`
- **Interpretation**: 
  - CI > 61.8 (Fibonacci High) = Market is **Too Choppy** (Blocked).
  - CI < 38.2 (Fibonacci Low) = Market is **Trending** (Permitted).

### Factor B: Average Directional Index (ADX)
Measures the pure strength of a trend regardless of direction.
- `ADX > 25` = Strong momentum present.
- `ADX < 20` = Weak/Sideways movement.

### The Blend
`Total Score = (CI_Score * 0.5) + (ADX_Score * 0.5)`
Only scores above **0.35** are allowed to place orders.

## 3. The Breakout Override (Alpha Boost)
Rolling indicators (CI, ADX) suffer from lag. If an explosive move happens after a period of chop, the AI might block it. The Breakout Override solves this.

- **Trigger**: `Current_True_Range > (14_Period_ATR * 2.0)`
- **Logic**: If the current 1-minute candle's volatility is 200% larger than the recent average, an institutional move is occurring. The engine bypasses the Regime Block and forces the trade through.

## 4. The Exit Engine

### A. ATR-Based Dynamic Trailing Stop
A static percentage stop (e.g., 5%) is flawed because it ignores market volatility.
- **Formula**: `Stop_Price = Peak_Price - (ATR(14) * 3.0)`
- **Logic**: The stop loss boundary automatically widens in highly volatile markets (preventing whipsaws) and tightens in consolidating markets to lock in profits.

### B. Velocity Exit (PnL per Minute)
Velocity measures the "Speed of Profit" to ensure capital efficiency.
- **Formula**: `Velocity = (Current_PnL_Pct) / (Minutes_Held)`
- **Logic**: If you are in a trade for 20 minutes and profit is only 0.05%, your Velocity is `0.0025%/min`. If this falls below the threshold (e.g., `0.0001`), the engine kills the trade.

## 5. Dynamic Position Sizing (Risk Percent Model)
The system trades "Risk Capital" rather than fixed shares, ensuring mathematical equality across all trades regardless of asset price or volatility.

- **Risk Capital**: `Total_Equity * 0.02` (Risking exactly 2% of the portfolio).
- **Stop Distance**: `ATR(14) * 3.0`
- **Share Size**: `Risk_Capital / Stop_Distance`
- **Logic**: You will automatically buy fewer shares of highly volatile stocks and more shares of quiet stocks. If the trailing stop is hit, you always lose exactly 2%.
