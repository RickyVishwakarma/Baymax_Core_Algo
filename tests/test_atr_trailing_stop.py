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

class TestATRTrailingStop(unittest.TestCase):
    def test_atr_trailing_stop_trigger(self):
        start_time = datetime(2026, 1, 1, 10, 0, 0)
        bars = []
        
        # 1. Warm up period (15 bars) to establish an ATR.
        # We'll make the bars have a True Range of 1.0 (High 101, Low 100, Close 100)
        # So ATR(14) should be ~1.0
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
            
        # At bar 15, we trigger a BUY
        signals = [
            None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            Signal(symbol="TEST", side=Side.BUY, size=10, reason="entry")
        ]
        
        # Bar 16: Price rises nicely to 105.0 (Peak price becomes 105.0)
        bars.append(MarketBar(
            ts=start_time + timedelta(minutes=15),
            symbol="TEST", open=105.0, high=105.0, low=105.0, close=105.0, volume=1000
        ))
        
        # Bar 17: Sudden drop.
        # ATR is roughly 1.0. Multiplier is 3.0.
        # Stop price = Peak(105) - (3 * 1.0) = 102.0
        # Massive drop to ensure we cross any ATR boundary
        bars.append(MarketBar(
            ts=start_time + timedelta(minutes=16),
            symbol="TEST", open=50.0, high=50.0, low=50.0, close=50.0, volume=1000
        ))
        
        portfolio = PortfolioManager(starting_cash=10000)
        engine = TradingEngine(
            data_feed=MockFeed(bars),
            strategy_factory=lambda: MockStrategy(signals),
            risk_manager=BasicRiskManager(max_position_units=100, max_notional_per_order=100000, max_drawdown_pct=0.5),
            execution=PaperExecutionHandler(fee_bps=0.0, slippage_bps=0.0),
            portfolio=portfolio,
            atr_trailing_stop={"enabled": True, "period": 14, "multiplier": 3.0}
        )
        
        exits = []
        def on_fill(bar, fill, signal, pf):
            if signal.reason == "atr_trailing_stop":
                exits.append((bar.ts, signal.reason))
        
        engine.on_fill_callback = on_fill
        engine.run()
        
        self.assertTrue(len(exits) > 0, "ATR trailing stop should have triggered")
        self.assertEqual(exits[0][1], "atr_trailing_stop")
        print(f"ATR trailing stop triggered at: {exits[0][0]}")

if __name__ == "__main__":
    unittest.main()
