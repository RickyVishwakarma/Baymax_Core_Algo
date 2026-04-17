# Baymax Core Algo: System Architecture

This document provides a high-level overview of the data flow and component architecture of the Baymax Core trading system.

## 🏛️ High-Level Architecture

```mermaid
graph TD
    %% External Interfaces
    DhanHQ[Dhan HQ v2 API] <-->|JWT Auth / Order API| Exec[Execution Handler]
    DhanWS[Dhan Live Feed] -->|Binary WebSocket| Agg[Data Aggregator]

    %% Data Pipeline
    Agg -->|1-Min MarketBar| Engine[Trading Engine]

    %% The Brain
    subgraph The Brain (Event Loop)
        Engine -->|Bar| PF[Portfolio Manager]
        Engine -->|Bar| ML[AI Regime Classifier]
        Engine -->|Bar| Strat[Strategy: Supertrend]
        
        Strat -.->|Signal| ML
        ML -.->|Filter/Override| Sizing[Dynamic Position Sizer]
    end

    %% Risk & Execution
    Sizing -->|Sized Signal| Risk[Risk Manager]
    Risk -->|ATR Tracker| Risk
    Risk -.->|Rejected| Log[Logger]
    Risk -.->|Approved Order| Exec

    %% Feedback Loop
    Exec -->|Fill Event| PF
```

## 🧩 Component Breakdown

### 1. Data Ingestion (`data/`)
- **Dhan Socket (`dhan_socket.py`)**: Connects to `wss://api-feed.dhan.co`. Receives binary packets, unpacks struct formats (Int32, Float32), and yields raw ticks.
- **Aggregator (`aggregator.py`)**: Batches the raw ticks into precise 1-minute `MarketBar` objects (OHLCV).

### 2. The Engine (`engine.py`)
The central nervous system. It orchestrates the flow of every 1-minute bar:
1. Updates the Portfolio MTM (Mark-to-Market).
2. Updates the ATR Volatility Tracker.
3. Checks for **Velocity Exits** (stalled momentum).
4. Checks for **ATR Trailing Stops** (dynamic risk limits).

### 3. The Strategy (`strategy/supertrend.py`)
A pure math implementation of the ATR-based Supertrend. It generates basic `BUY`/`SELL` signals.

### 4. The Intelligence Layer (`ml/regime.py`)
Intercepts the strategy's signal.
- Calculates **Choppiness Index (CI)** and **ADX**.
- Blocks the trade if the market is moving sideways.
- Employs a **Breakout Override**: Forces the trade through if the current candle is explosively volatile.

### 5. Position Sizing & Risk Management (`risk/`)
- **Position Sizer**: Takes the approved signal and dynamically calculates exactly how many shares to buy to risk exactly 2% of total equity.
- **Risk Manager**: Performs final sanity checks (Max Notional limits, Margin limits, Drawdown limits).

### 6. Execution & Portfolio (`execution/` & `portfolio/`)
- Sends the valid order to Dhan HQ v2.
- Awaits the fill confirmation.
- The `PortfolioManager` logs the exact entry price and timestamp, which is crucial for the Velocity Exit calculations.
