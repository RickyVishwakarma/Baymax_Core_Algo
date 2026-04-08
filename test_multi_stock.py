import time
from datetime import datetime, timezone, timedelta
from typing import Iterator

from trading_system.data.feed import MarketDataFeed
from trading_system.models import MarketBar, Side
from trading_system.engine import TradingEngine
from trading_system.risk.basic import BasicRiskManager
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.portfolio.manager import PortfolioManager
from trading_system.strategy.base import Strategy, Signal

# Mock Multi-Stock Data Feed
class MockMultiStockFeed(MarketDataFeed):
    def __init__(self, symbols, ticks=10):
        self.symbols = symbols
        self.ticks = ticks
        self.start_ts = datetime.now(timezone.utc)

    def stream(self) -> Iterator[MarketBar]:
        for i in range(self.ticks):
            for i_sym, sym in enumerate(self.symbols):
                if i < 5:
                    price = 100.0 + (i * 2.0)
                else:
                    price = 108.0 - ((i - 4) * 3.0) 
                 
                yield MarketBar(
                    ts=self.start_ts + timedelta(minutes=i),
                    symbol=sym,
                    open=price - 1.0,
                    high=price + 2.0,
                    low=price - 2.0,
                    close=price,
                    volume=1000.0
                )

# Aggressive strategy that fires on every tick for testing
class TriggerHappyStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.tick_count = 0
        
    def on_bar(self, bar: MarketBar) -> Signal | None:
        self.tick_count += 1
        # Always just buy to get long exposure immediately, skip the first few noisy ticks
        if self.tick_count == 1:
            return Signal(symbol=bar.symbol, side=Side.BUY, size=5.0, score=1.0, confidence=1.0, regime="test", reason="Buy Initial Pump")
        return None

def main():
    print("=======================================")
    print("STARTING MULTI-STOCK ENGINE STRESS TEST")
    print("=======================================")
    
    symbols = ["TCS", "INFY", "RELIANCE"]
    
    # Setup instances
    feed = MockMultiStockFeed(symbols=symbols, ticks=9)
    strategy_factory = lambda: TriggerHappyStrategy()
    risk = BasicRiskManager(
        max_position_units=100.0,
        max_notional_per_order=50000.0,
        max_drawdown_pct=0.5,
        allow_short=True,
        max_exposure_pct=1.0,
        max_bar_range_pct=0.20,
        min_cash_buffer_pct=0.01,
    )
    execution = PaperExecutionHandler(fee_bps=5.0, slippage_bps=0.0)
    portfolio = PortfolioManager(starting_cash=100_000.0)

    # Attach simple callbacks
    def on_bar(bar, pf):
        pass # print(f"[{bar.symbol}] Current Price: {bar.close} | Basket Equity: {pf.state.equity:.2f}")

    def on_fill(bar, fill, signal, pf):
        pass # logger handles it

    engine = TradingEngine(
        data_feed=feed,
        strategy_factory=strategy_factory,
        risk_manager=risk,
        execution=execution,
        portfolio=portfolio,
        trailing_stop_pct=0.02, # 2% trailing stop threshold
        on_bar_callback=on_bar,
        on_fill_callback=on_fill
    )

    # Run the engine
    engine.run()
    
    print("\n=======================================")
    print("TEST COMPLETED. FINAL PORTFOLIO STATUS:")
    print("=======================================")
    print(f"Total Portfolio Equity: Rs {portfolio.state.equity:.2f}")
    print(f"Total Available Cash:   Rs {portfolio.state.cash:.2f}")
    for sym, pos in portfolio.positions.items():
        print(f"Position -> {sym:<10} | Units: {pos.units} | Avg Entry: Rs {pos.avg_entry_price:.2f}")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    main()
