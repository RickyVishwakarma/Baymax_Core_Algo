"""
Pure-Python Market Regime Classifier
=====================================
Zero external dependencies. Uses two proven technical indicators:

1. Choppiness Index (CI)
   Measures how choppy/range-bound a market is.
   CI > 61.8  →  CHOPPY  (random sideways noise, avoid trading)
   CI < 38.2  →  TRENDING (strong directional movement, trade freely)
   Between    →  NEUTRAL  (apply partial throttle)

2. Average Directional Index (ADX)
   Measures overall trend strength regardless of direction.
   ADX > 25  →  TRENDING
   ADX < 20  →  CHOPPY / WEAK TREND

Combined Score:
   A weighted average of normalised CI and ADX scores produces a
   regime_score in [0.0, 1.0]:
       0.0 = definitely choppy
       1.0 = definitely trending

The engine uses this score to either:
   - Block  the signal entirely (score < block_threshold)
   - Pass   the signal through (score >= pass_threshold)
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from trading_system.models import MarketBar


@dataclass(slots=True)
class RegimeResult:
    regime: str           # "trending", "choppy", or "neutral"
    score: float          # 0.0 (choppy) → 1.0 (trending)
    choppiness_index: float | None
    adx: float | None
    bars_seen: int


class RegimeClassifier:
    """
    Per-symbol regime classifier fed one MarketBar at a time.

    Parameters
    ----------
    window : int
        Rolling lookback period for both CI and ADX (default 14).
    block_threshold : float
        If regime_score < block_threshold, suppress the trade signal.
    pass_threshold : float
        If regime_score >= pass_threshold, pass through unthrottled.
        Scores in (block_threshold, pass_threshold) are neutral.
    ci_weight : float
        Weight given to the Choppiness Index score (0-1).
        ADX weight = 1 - ci_weight.
    """

    CI_CHOPPY_LINE = 61.8
    CI_TREND_LINE = 38.2

    ADX_TREND_LINE = 25.0
    ADX_CHOPPY_LINE = 20.0

    def __init__(
        self,
        window: int = 14,
        block_threshold: float = 0.35,
        pass_threshold: float = 0.55,
        ci_weight: float = 0.5,
    ) -> None:
        if window < 4:
            raise ValueError("window must be at least 4")
        self.window = window
        self.block_threshold = block_threshold
        self.pass_threshold = pass_threshold
        self.ci_weight = max(0.0, min(1.0, ci_weight))
        self.adx_weight = 1.0 - self.ci_weight

        # Rolling OHLCV history
        self._highs: deque[float] = deque(maxlen=window + 1)
        self._lows: deque[float] = deque(maxlen=window + 1)
        self._closes: deque[float] = deque(maxlen=window + 1)

        # ADX internals (smoothed)
        self._prev_plus_dm: float = 0.0
        self._prev_minus_dm: float = 0.0
        self._prev_atr14: float = 0.0
        self._prev_adx: float = 0.0
        self._dx_values: deque[float] = deque(maxlen=window)

        self._bars_seen: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, bar: MarketBar) -> RegimeResult:
        """Feed one bar; returns the current regime classification."""
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        self._closes.append(bar.close)
        self._bars_seen += 1

        ci = self._choppiness_index()
        adx = self._adx()

        score = self._combine(ci, adx)
        regime = self._classify(score)

        return RegimeResult(
            regime=regime,
            score=score,
            choppiness_index=ci,
            adx=adx,
            bars_seen=self._bars_seen,
        )

    def is_ready(self) -> bool:
        """True once enough bars have been seen for a reliable signal."""
        return self._bars_seen >= self.window + 1

    # ------------------------------------------------------------------
    # Choppiness Index
    # ------------------------------------------------------------------

    def _choppiness_index(self) -> float | None:
        n = len(self._highs)
        if n < self.window + 1:
            return None

        highs = list(self._highs)
        lows = list(self._lows)
        closes = list(self._closes)

        # True ranges for the last window bars
        atr_sum = 0.0
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            atr_sum += tr

        period_high = max(highs[-self.window:])
        period_low = min(lows[-self.window:])
        high_low_range = period_high - period_low

        if high_low_range <= 0 or atr_sum <= 0:
            return None

        ci = 100.0 * math.log10(atr_sum / high_low_range) / math.log10(self.window)
        return ci

    # ------------------------------------------------------------------
    # Average Directional Index (Wilder's smoothing)
    # ------------------------------------------------------------------

    def _adx(self) -> float | None:
        if len(self._highs) < 2:
            return None

        h = list(self._highs)
        l = list(self._lows)
        c = list(self._closes)
        i = len(h) - 1

        # True Range
        tr = max(
            h[i] - l[i],
            abs(h[i] - c[i - 1]),
            abs(l[i] - c[i - 1]),
        )

        # Directional movement
        up_move = h[i] - h[i - 1]
        down_move = l[i - 1] - l[i]

        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

        # Wilder smoothing
        k = 1.0 / self.window
        self._prev_atr14 = self._prev_atr14 * (1 - k) + tr * k
        self._prev_plus_dm = self._prev_plus_dm * (1 - k) + plus_dm * k
        self._prev_minus_dm = self._prev_minus_dm * (1 - k) + minus_dm * k

        if self._prev_atr14 == 0:
            return None

        plus_di = 100.0 * self._prev_plus_dm / self._prev_atr14
        minus_di = 100.0 * self._prev_minus_dm / self._prev_atr14

        di_sum = plus_di + minus_di
        if di_sum == 0:
            return None

        dx = 100.0 * abs(plus_di - minus_di) / di_sum
        self._dx_values.append(dx)

        if len(self._dx_values) < self.window:
            return None

        adx = sum(self._dx_values) / len(self._dx_values)
        return adx

    # ------------------------------------------------------------------
    # Combine scores
    # ------------------------------------------------------------------

    def _combine(self, ci: float | None, adx: float | None) -> float:
        """Return combined trend score in [0.0, 1.0]."""
        scores: list[tuple[float, float]] = []  # (score, weight)

        if ci is not None:
            # CI: 100=choppy → 0.0, 0=trending → 1.0
            # Normalise between CI_TREND_LINE and CI_CHOPPY_LINE
            ci_norm = 1.0 - (ci - self.CI_TREND_LINE) / (self.CI_CHOPPY_LINE - self.CI_TREND_LINE)
            ci_norm = max(0.0, min(1.0, ci_norm))
            scores.append((ci_norm, self.ci_weight))

        if adx is not None:
            # ADX: 0=choppy → 0.0, 50+=trending → 1.0
            adx_norm = (adx - self.ADX_CHOPPY_LINE) / (self.ADX_TREND_LINE - self.ADX_CHOPPY_LINE)
            adx_norm = max(0.0, min(1.0, adx_norm))
            scores.append((adx_norm, self.adx_weight))

        if not scores:
            return 0.5  # Neutral when insufficient data

        total_weight = sum(w for _, w in scores)
        return sum(s * w for s, w in scores) / total_weight

    def _classify(self, score: float) -> str:
        if score >= self.pass_threshold:
            return "trending"
        if score <= self.block_threshold:
            return "choppy"
        return "neutral"


class MultiSymbolRegimeClassifier:
    """
    Wrapper that maintains one RegimeClassifier per symbol.
    Injected directly into TradingEngine.
    """

    def __init__(
        self,
        window: int = 14,
        block_threshold: float = 0.35,
        pass_threshold: float = 0.55,
        ci_weight: float = 0.5,
    ) -> None:
        self._params = dict(
            window=window,
            block_threshold=block_threshold,
            pass_threshold=pass_threshold,
            ci_weight=ci_weight,
        )
        self._classifiers: dict[str, RegimeClassifier] = {}

    def update(self, bar: MarketBar) -> RegimeResult:
        if bar.symbol not in self._classifiers:
            self._classifiers[bar.symbol] = RegimeClassifier(**self._params)
        return self._classifiers[bar.symbol].update(bar)

    def should_block(self, bar: MarketBar) -> tuple[bool, RegimeResult]:
        result = self.update(bar)
        blocked = result.regime == "choppy" and result.bars_seen >= self._params["window"] + 1
        return blocked, result
