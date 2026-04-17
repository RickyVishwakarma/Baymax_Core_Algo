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

class TestDynamicSizing(unittest.TestCase):
    def test_risk_percent_sizing(self):
        start_time = datetime(2026, 1, 1, 10, 0, 0)
        bars = []
        
        # 14 warmup bars with True Range = 1.0. (ATR = 1.0)
        for i in range(15):
            bars.append(MarketBar(
                ts=start_time + timedelta(minutes=i),
                symbol="TEST",
                open=100.5,
                high=101.0,
                low=100.0,
                close=100.5,
                volume=1000
            ))
            
        # The strategy issues a signal with a hardcoded size of 1.0
        # We want the engine to intercept this and dynamically calculate it.
        signals = [None] * 14 + [Signal(symbol="TEST", side=Side.BUY, size=1.0, reason="entry")]
        
        portfolio = PortfolioManager(starting_cash=100000.0) # $100k equity
        
        engine = TradingEngine(
            data_feed=MockFeed(bars),
            strategy_factory=lambda: MockStrategy(signals),
            risk_manager=BasicRiskManager(max_position_units=10000, max_notional_per_order=1000000, max_drawdown_pct=0.5),
            execution=PaperExecutionHandler(fee_bps=0.0, slippage_bps=0.0),
            portfolio=portfolio,
            atr_trailing_stop={"enabled": True, "period": 14, "multiplier": 3.0},
            position_sizing={
                "type": "risk_percent",
                "risk_pct": 0.02, # 2% of 100k = 2000
            }
        )
        
        fills = []
        def on_fill(bar, fill, signal, pf):
            fills.append(fill)
            
        engine.on_fill_callback = on_fill
        engine.run()
        
        self.assertEqual(len(fills), 1, "Should have 1 fill")
        
        # Calculation:
        # Risk Capital = 100000 * 0.02 = 2000
        # ATR = ~1.0
        # Stop Distance = 1.0 * 3.0 = 3.0
        # Expected Size = 2000 / 3.0 = 666.6667
        
        actual_size = fills[0].size
        self.assertAlmostEqual(actual_size, 666.6667, places=2)
        print(f"Test Passed: Size dynamically adjusted to {actual_size}")

if __name__ == "__main__":
    unittest.main()
