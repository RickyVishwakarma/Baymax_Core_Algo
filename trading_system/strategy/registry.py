from __future__ import annotations

from trading_system.strategy.base import Strategy
from trading_system.strategy.moving_average import MovingAverageCrossStrategy
# We will import mean_reversion and breakout later. We can use dynamic loading or just imports.
# Due to circular dependencies or neatness we can import them within the function or at the top.

class StrategyRegistry:
    @staticmethod
    def build(name: str, **kwargs) -> Strategy:
        n = name.lower()
        if n == "moving_average":
            from trading_system.strategy.moving_average import MovingAverageCrossStrategy
            return MovingAverageCrossStrategy(**kwargs)
        elif n == "mean_reversion":
            from trading_system.strategy.mean_reversion import MeanReversionStrategy
            return MeanReversionStrategy(**kwargs)
        elif n == "breakout":
            from trading_system.strategy.breakout import BreakoutStrategy
            return BreakoutStrategy(**kwargs)
        elif n == "supertrend":
            from trading_system.strategy.supertrend import SupertrendStrategy
            return SupertrendStrategy(**kwargs)
        elif n == "vwap":
            from trading_system.strategy.vwap import VWAPStrategy
            return VWAPStrategy(**kwargs)
        elif n == "orb_vwap":
            from trading_system.strategy.orb_vwap import OrbVwapStrategy
            return OrbVwapStrategy(**kwargs)
        elif n == "vwap_pullback":
            from trading_system.strategy.vwap_pullback import VwapPullbackStrategy
            return VwapPullbackStrategy(**kwargs)
        else:
            raise ValueError(f"Unknown strategy name: {name}")
