import unittest
from datetime import datetime, timedelta, timezone
from trading_system.models import MarketBar, Side, Signal
from trading_system.data.resampler import TimeframeResampler
from trading_system.engine import TradingEngine
from trading_system.portfolio.manager import PortfolioManager
from trading_system.risk.basic import BasicRiskManager
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.strategy.base import Strategy

class MockHTFStrategy(Strategy):
    def __init__(self, is_bullish_val: bool):
        self.val = is_bullish_val
        self.called = 0
    def on_bar(self, bar):
        self.called += 1
        return None
    def is_bullish(self):
        return self.val

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

class TestMTFAlignment(unittest.TestCase):
    def test_resampler(self):
        resampler = TimeframeResampler(timeframe_minutes=5)
        start = datetime(2026, 1, 1, 9, 15, 0, tzinfo=timezone.utc)
        
        # 9:15, 9:16, 9:17, 9:18, 9:19
        for i in range(5):
            bar = MarketBar(symbol="TEST", ts=start + timedelta(minutes=i), open=10, high=12, low=8, close=11, volume=100)
            result = resampler.update(bar)
            self.assertIsNone(result, "Should not emit until boundary crossed")
            
        # 9:20 -> crosses boundary, should emit the 9:15 bar
        bar_920 = MarketBar(symbol="TEST", ts=start + timedelta(minutes=5), open=11, high=11, low=11, close=11, volume=100)
        result = resampler.update(bar_920)
        
        self.assertIsNotNone(result, "Should emit HTF bar when crossing boundary")
        self.assertEqual(result.ts.minute, 15, "Anchor TS should be 9:15")
        self.assertEqual(result.volume, 500, "Volume should be summed")
        
    def test_engine_mtf_block(self):
        # We will feed bars. 
        # The HTF strategy will say is_bullish = False (Bearish macro trend)
        # The 1m strategy will issue a BUY signal.
        # It should be blocked.
        start = datetime(2026, 1, 1, 9, 15, 0, tzinfo=timezone.utc)
        
        bars = []
        for i in range(6):
            bars.append(MarketBar(symbol="TEST", ts=start + timedelta(minutes=i), open=10, high=10, low=10, close=10, volume=100))
            
        # 6 bars: The 6th bar (9:20) triggers the 5m bar (9:15) emission to HTF strategy.
        # On the 6th bar, the 1m strategy fires a BUY.
        signals = [None, None, None, None, None, Signal(symbol="TEST", side=Side.BUY, size=1.0, reason="entry")]
        
        engine = TradingEngine(
            data_feed=MockFeed(bars),
            strategy_factory=lambda sym=None: MockStrategy(signals),
            risk_manager=BasicRiskManager(max_position_units=100, max_notional_per_order=1000000, max_drawdown_pct=0.5),
            execution=PaperExecutionHandler(fee_bps=0.0, slippage_bps=0.0),
            portfolio=PortfolioManager(starting_cash=100000.0),
            mtf_alignment={"enabled": True, "timeframe_minutes": 5}
        )
        
        # Override the HTF strategy factory for the test
        # Note: the engine calls strategy_factory() for both 1m and HTF.
        # So we patch self.htf_strategies directly
        engine.htf_strategies["TEST"] = MockHTFStrategy(is_bullish_val=False)
        
        fills = []
        def on_fill(bar, fill, signal, pf):
            fills.append(fill)
        engine.on_fill_callback = on_fill
        
        engine.run()
        
        self.assertEqual(len(fills), 0, "Trade should be BLOCKED by MTF alignment")
        print("Test Passed: 1m BUY signal blocked because 5m macro trend was BEARISH.")

if __name__ == "__main__":
    unittest.main()
