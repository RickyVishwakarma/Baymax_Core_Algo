from __future__ import annotations

import logging
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Iterator

from trading_system.data.feed import MarketDataFeed
from trading_system.models import MarketBar, Order, Fill, Side
from trading_system.execution.base import ExecutionHandler
from trading_system.engine import TradingEngine
from trading_system.risk.basic import BasicRiskManager
from trading_system.portfolio.manager import PortfolioManager
from trading_system.strategy.registry import StrategyRegistry

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class HighSpeedMockFeed(MarketDataFeed):
    """Generates synthetic bars at high speed for stress testing."""
    def __init__(self, symbols: list[str], n_bars_per_symbol: int = 100):
        self.symbols = symbols
        self.n_bars = n_bars_per_symbol
        
    def stream(self) -> Iterator[MarketBar]:
        start_ts = datetime.now(timezone.utc)
        for i in range(self.n_bars):
            for symbol in self.symbols:
                yield MarketBar(
                    ts=start_ts + timedelta(minutes=i),
                    symbol=symbol,
                    open=100.0 + random.random(),
                    high=102.0,
                    low=98.0,
                    close=101.0 + random.random(),
                    volume=1000
                )

class FaultyExecutionHandler(ExecutionHandler):
    """Execution handler that fails with a 20% probability to test resilience."""
    def __init__(self, failure_rate: float = 0.2):
        self.failure_rate = failure_rate
        self.total_calls = 0
        self.total_failures = 0

    def execute(self, order: Order, bar: MarketBar) -> Fill:
        self.total_calls += 1
        if random.random() < self.failure_rate:
            self.total_failures += 1
            raise RuntimeError(f"Simulated API Failure for {order.symbol}")
        
        return Fill(
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            fill_price=bar.close,
            fee_paid=0.0
        )

def run_stress_test(n_symbols: int = 50, n_bars: int = 100):
    print(f"\n{'='*60}")
    print(f" STARTING INSTITUTIONAL-LEVEL STRESS TEST")
    print(f" Symbols: {n_symbols} | Bars per Symbol: {n_bars} | Total Events: {n_symbols * n_bars}")
    print(f"{'='*60}")

    symbols = [f"SYMB_{i}" for i in range(n_symbols)]
    feed = HighSpeedMockFeed(symbols, n_bars)
    
    # Using Supertrend as it's more CPU-intensive than MovingAverage
    strategy_factory = lambda: StrategyRegistry.build("supertrend", atr_period=10, multiplier=3.0)
    
    risk = BasicRiskManager(
        max_position_units=10.0, 
        max_notional_per_order=20000.0,
        max_drawdown_pct=0.10
    )
    execution = FaultyExecutionHandler(failure_rate=0.1) # 10% failure rate
    portfolio = PortfolioManager(starting_cash=1000000.0)
    
    engine = TradingEngine(
        data_feed=feed,
        strategy_factory=strategy_factory,
        risk_manager=risk,
        execution=execution,
        portfolio=portfolio
    )

    start_time = time.time()
    engine.run()
    end_time = time.time()

    elapsed = end_time - start_time
    events = n_symbols * n_bars
    throughput = events / elapsed if elapsed > 0 else 0

    print(f"\n{'='*60}")
    print(f" STRESS TEST RESULTS")
    print(f"{'='*60}")
    print(f" Total Time:        {elapsed:.2f}s")
    print(f" Throughput:        {throughput:.2f} bars / sec")
    print(f" Avg Latency:       {(elapsed/events)*1000:.4f}ms per bar-process")
    print(f" Total Orders:      {execution.total_calls}")
    print(f" Handled Failures:  {execution.total_failures} (System stayed ALIVE)")
    print(f" Final Portfolio:   Rs {portfolio.state.equity:,.2f}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Test with 100 symbols (Nifty 50 + Next 50) and 200 iterations
    run_stress_test(n_symbols=100, n_bars=200)
