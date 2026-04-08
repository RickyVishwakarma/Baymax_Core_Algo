"""
AI Regime Classifier — Stress Test
====================================
Scenario A: CHOPPY market (small random oscillations) → signals should be BLOCKED
Scenario B: TRENDING market (steady upward march) → signals should PASS THROUGH
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone, timedelta
from collections.abc import Iterator

from trading_system.models import MarketBar, Side, Signal
from trading_system.engine import TradingEngine
from trading_system.risk.basic import BasicRiskManager
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.portfolio.manager import PortfolioManager
from trading_system.strategy.base import Strategy
from trading_system.ml.regime import MultiSymbolRegimeClassifier, RegimeClassifier
from trading_system.data.feed import MarketDataFeed

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ─── Helper feeds ─────────────────────────────────────────────────────────────

def make_choppy_bars(symbol: str, n: int = 50) -> list[MarketBar]:
    """Synthetic bars oscillating ±0.5% randomly around a fixed price."""
    import math
    bars = []
    base = 1000.0
    ts = datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc)
    for i in range(n):
        # Zigzag: small alternating moves — classic choppy structure
        delta = 5.0 * (1 if i % 2 == 0 else -1)
        close = base + delta
        bars.append(MarketBar(
            ts=ts + timedelta(minutes=i),
            symbol=symbol,
            open=close + 1.0,
            high=close + 3.0,
            low=close - 3.0,
            close=close,
            volume=10000.0,
        ))
    return bars


def make_trending_bars(symbol: str, n: int = 50) -> list[MarketBar]:
    """Synthetic bars marching steadily upward — classic trending structure."""
    bars = []
    price = 1000.0
    ts = datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc)
    for i in range(n):
        price += 8.0  # consistent upward push
        bars.append(MarketBar(
            ts=ts + timedelta(minutes=i),
            symbol=symbol,
            open=price - 4.0,
            high=price + 2.0,
            low=price - 6.0,
            close=price,
            volume=20000.0,
        ))
    return bars


class SequentialFeed(MarketDataFeed):
    def __init__(self, bars: list[MarketBar]):
        self._bars = bars

    def stream(self) -> Iterator[MarketBar]:
        yield from self._bars


class AlwaysBuyStrategy(Strategy):
    """Fires a BUY signal on every single bar."""
    def on_bar(self, bar: MarketBar) -> Signal | None:
        return Signal(
            symbol=bar.symbol, side=Side.BUY, size=1.0,
            reason="test_always_buy", score=1.0, confidence=1.0, regime="test",
        )


def run_scenario(label: str, bars: list[MarketBar]) -> int:
    """Run the engine and count how many fills actually happened."""
    fill_count = 0

    def on_fill(bar, fill, signal, pf):
        nonlocal fill_count
        fill_count += 1

    engine = TradingEngine(
        data_feed=SequentialFeed(bars),
        strategy_factory=AlwaysBuyStrategy,
        risk_manager=BasicRiskManager(
            max_position_units=999.0,
            max_notional_per_order=1_000_000.0,
            max_drawdown_pct=1.0,
            allow_short=True,
            max_exposure_pct=1.0,
            max_bar_range_pct=1.0,
            min_cash_buffer_pct=0.0,
        ),
        execution=PaperExecutionHandler(fee_bps=0.0, slippage_bps=0.0),
        portfolio=PortfolioManager(starting_cash=1_000_000.0),
        trailing_stop_pct=0.0,
        regime_classifier=MultiSymbolRegimeClassifier(
            window=14,
            block_threshold=0.35,
            pass_threshold=0.55,
        ),
        on_fill_callback=on_fill,
    )
    engine.run()
    return fill_count


# ─── Also test the classifier in isolation ────────────────────────────────────

def test_classifier_isolation():
    print("\n─── Unit Test: RegimeClassifier in isolation ───")
    
    choppy_bars = make_choppy_bars("CHOPTEST", 60)
    classifier = RegimeClassifier(window=14)
    last = None
    for b in choppy_bars:
        last = classifier.update(b)
    print(f"  CHOPPY market CI={last.choppiness_index:.1f}  ADX={last.adx:.1f}  "
          f"score={last.score:.3f}  regime={last.regime}")
    assert last.regime in ("choppy", "neutral"), f"Expected choppy/neutral, got {last.regime}"
    
    trend_bars = make_trending_bars("TRENDTEST", 60)
    classifier2 = RegimeClassifier(window=14)
    last2 = None
    for b in trend_bars:
        last2 = classifier2.update(b)
    print(f"  TRENDING market CI={last2.choppiness_index:.1f}  ADX={last2.adx:.1f}  "
          f"score={last2.score:.3f}  regime={last2.regime}")
    assert last2.regime in ("trending", "neutral"), f"Expected trending/neutral, got {last2.regime}"
    
    print("  ✅ Classifier isolation tests passed.")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  AI REGIME CLASSIFIER — ENGINE INTEGRATION TEST")
    print("=" * 55)

    test_classifier_isolation()

    choppy_fills = run_scenario("CHOPPY", make_choppy_bars("CHOP", 50))
    trending_fills = run_scenario("TRENDING", make_trending_bars("TREND", 50))

    print(f"\n─── Engine Integration Results ───")
    print(f"  CHOPPY  market: {choppy_fills:>3} fills  (AI should BLOCK most signals)")
    print(f"  TRENDING market: {trending_fills:>3} fills  (AI should PASS signals through)")

    # Core assertion: trending should yield more fills than choppy
    if trending_fills > choppy_fills:
        print(f"\n  ✅ PASSED — Regime classifier is correctly throttling choppy signals.")
        print(f"     Blocked {50 - choppy_fills} out of 50 choppy signals.")
        print(f"     Permitted {trending_fills} out of 50 trending signals.")
    else:
        print(f"\n  ⚠️  Unexpected result — review thresholds or synthetic data.")
        sys.exit(1)

    print("=" * 55)
