import unittest
from datetime import datetime, timedelta
from trading_system.models import MarketBar, Side, Signal
from trading_system.engine import TradingEngine
from trading_system.portfolio.manager import PortfolioManager
from trading_system.risk.basic import BasicRiskManager
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.strategy.base import Strategy

class MockStrategy(Strategy):
    def __init__(self, signals):
        self.signals = signals
        self.idx = 0
    def on_bar(self, bar):
        if self.idx < len(self.signals):
            sig = self.signals[self.idx]
            self.idx += 1
            return sig
        return None

class MockFeed:
    def __init__(self, bars):
        self.bars = bars
    def stream(self):
        for bar in self.bars:
            yield bar

class TestVelocityExit(unittest.TestCase):
    def test_velocity_exit_trigger(self):
        # 1. Setup Bars
        # Minute 0: Entry at 100
        # Minute 1: 105 (Fast)
        # Minute 2: 105.1 (Slowing)
        # Minute 3: 105.1 (Stalled)
        start_time = datetime(2026, 1, 1, 10, 0, 0)
        bars = [
            MarketBar(ts=start_time, symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
            MarketBar(ts=start_time + timedelta(minutes=1), symbol="TEST", open=105, high=105, low=105, close=105, volume=1000),
            MarketBar(ts=start_time + timedelta(minutes=2), symbol="TEST", open=105.1, high=105.1, low=105.1, close=105.1, volume=1000),
            MarketBar(ts=start_time + timedelta(minutes=3), symbol="TEST", open=105.1, high=105.1, low=105.1, close=105.1, volume=1000),
            MarketBar(ts=start_time + timedelta(minutes=4), symbol="TEST", open=105.1, high=105.1, low=105.1, close=105.1, volume=1000),
        ]
        
        # 2. Setup Signal (Buy on first bar)
        signals = [Signal(symbol="TEST", side=Side.BUY, size=10, reason="entry")]
        
        # 3. Setup Engine
        # Threshold: 1% per minute (0.01)
        # Min 1: Velocity = (105-100)/100 / 1 = 0.05 (5%) -> STAYS
        # Min 2: Velocity = (105.1-100)/100 / 2 = 0.051 / 2 = 0.0255 (2.5%) -> STAYS
        # Min 3: Velocity = (105.1-100)/100 / 3 = 0.051 / 3 = 0.017 (1.7%) -> STAYS
        # We will set thrill to 0.02 (2% per min)
        
        portfolio = PortfolioManager(starting_cash=10000)
        engine = TradingEngine(
            data_feed=MockFeed(bars),
            strategy_factory=lambda sym=None: MockStrategy(signals),
            risk_manager=BasicRiskManager(max_position_units=100, max_notional_per_order=100000, max_drawdown_pct=0.5),
            execution=PaperExecutionHandler(fee_bps=0.0, slippage_bps=0.0),
            portfolio=portfolio,
            min_velocity_threshold=0.02
        )
        
        # Track exits
        exits = []
        def on_fill(bar, fill, signal, pf):
            if signal.reason == "velocity_exit":
                exits.append((bar.ts, signal.reason))
        
        engine.on_fill_callback = on_fill
        engine.run()
        
        self.assertTrue(any(e[1] == "velocity_exit" for e in exits), "Velocity exit should have triggered")
        print(f"Velocity exit triggered at: {exits[0][0]}")

if __name__ == "__main__":
    unittest.main()
