import unittest
from datetime import datetime, timedelta
from trading_system.models import MarketBar
from trading_system.ml.regime import MultiSymbolRegimeClassifier

class TestRegimeOverride(unittest.TestCase):
    def test_breakout_override(self):
        # Initialize classifier with breakout multiplier of 2.0
        classifier = MultiSymbolRegimeClassifier(
            window=14,
            block_threshold=0.35,
            pass_threshold=0.55,
            ci_weight=0.5,
            breakout_atr_multiplier=2.0
        )
        
        start_time = datetime(2026, 1, 1, 10, 0, 0)
        
        # 1. Feed 14 bars of extremely tight, choppy action.
        # This will drive the Choppiness Index very high and ADX very low.
        for i in range(15):
            bar = MarketBar(
                ts=start_time + timedelta(minutes=i),
                symbol="TEST",
                open=100.0,
                high=100.5 if i % 2 == 0 else 100.0,
                low=100.0 if i % 2 == 0 else 99.5,
                close=100.2 if i % 2 == 0 else 99.8,
                volume=1000
            )
            blocked, result = classifier.should_block(bar)
            # The first 14 bars won't block because window is 14
            # But the 15th bar (index 14) should definitely block as it's choppy
            if i == 14:
                self.assertTrue(blocked, "Bar 15 should be blocked due to choppiness")
                self.assertEqual(result.regime, "choppy")
                self.assertFalse(result.is_breakout)

        # 2. The 16th bar is a MASSIVE breakout.
        # Previous ATR is roughly 0.5. We need a True Range > 1.0 (0.5 * 2.0).
        # We will make the True Range 5.0.
        breakout_bar = MarketBar(
            ts=start_time + timedelta(minutes=15),
            symbol="TEST",
            open=100.0,
            high=105.0,
            low=100.0,
            close=104.5,
            volume=50000
        )
        
        blocked, result = classifier.should_block(breakout_bar)
        
        # It should NOT be blocked, because of the breakout override!
        self.assertFalse(blocked, "Breakout bar should NOT be blocked")
        self.assertEqual(result.regime, "breakout_override", "Regime should be set to breakout_override")
        self.assertTrue(result.is_breakout, "is_breakout flag should be True")
        
        print(f"Test Passed: Breakout overridden! TR was explosive. Regime={result.regime}")

if __name__ == "__main__":
    unittest.main()
