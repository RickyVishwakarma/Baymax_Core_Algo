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

## 3. The Velocity Engine (PnL per Minute)
Velocity measures the "Speed of Profit" to ensure capital efficiency.

- **Formula**: `Velocity = (Current_PnL_Pct) / (Minutes_Held)`
- **Scenario**: You are in a trade for 20 minutes and profit is only 0.05%.
- **Result**: `Velocity = 0.0025%/min`. 
- **Action**: If this is below your `min_velocity_threshold`, the bot exits immediately.

**Philosophy**: "If the trend doesn't pay you for your time, give the money back and find a faster horse."
