from __future__ import annotations

from collections import deque
from math import sqrt

from trading_system.models import MarketBar, Side, Signal
from trading_system.strategy.base import Strategy


class MovingAverageCrossStrategy(Strategy):
    """Hybrid strategy with classic MA mode and advanced multi-factor mode."""

    def __init__(
        self,
        short_window: int,
        long_window: int,
        order_size_units: float,
        use_rsi: bool = True,
        rsi_period: int = 14,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 65.0,
        use_bollinger: bool = True,
        bollinger_window: int = 20,
        bollinger_stddev: float = 2.0,
        use_macd: bool = True,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        min_confirmations: int = 1,
        mode: str = "advanced",
        trend_ema_fast: int = 12,
        trend_ema_slow: int = 34,
        momentum_window: int = 10,
        breakout_window: int = 20,
        volatility_window: int = 20,
        atr_period: int = 14,
        target_volatility_pct: float = 1.0,
        min_signal_score: float = 2.2,
        max_size_multiplier: float = 3.0,
        use_volume_confirmation: bool = True,
        volume_window: int = 20,
        regime_trend_threshold: float = 0.6,
        regime_chop_threshold: float = 0.2,
        signal_cooldown_bars: int = 2,
        score_hysteresis: float = 0.25,
    ):
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")
        if trend_ema_fast >= trend_ema_slow:
            raise ValueError("trend_ema_fast must be smaller than trend_ema_slow")

        self.mode = mode.lower()
        self.short_window = short_window
        self.long_window = long_window
        self.order_size_units = order_size_units
        self.use_rsi = use_rsi
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.use_bollinger = use_bollinger
        self.bollinger_window = bollinger_window
        self.bollinger_stddev = bollinger_stddev
        self.use_macd = use_macd
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.min_confirmations = min_confirmations

        self.trend_ema_fast = trend_ema_fast
        self.trend_ema_slow = trend_ema_slow
        self.momentum_window = momentum_window
        self.breakout_window = breakout_window
        self.volatility_window = volatility_window
        self.atr_period = atr_period
        self.target_volatility_pct = max(0.1, target_volatility_pct)
        self.min_signal_score = max(0.5, min_signal_score)
        self.max_size_multiplier = max(1.0, max_size_multiplier)
        self.use_volume_confirmation = use_volume_confirmation
        self.volume_window = max(5, volume_window)
        self.regime_trend_threshold = regime_trend_threshold
        self.regime_chop_threshold = regime_chop_threshold
        self.signal_cooldown_bars = max(0, signal_cooldown_bars)
        self.score_hysteresis = max(0.0, score_hysteresis)

        history_size = max(
            long_window,
            rsi_period + 1,
            bollinger_window,
            macd_slow + macd_signal + 2,
            trend_ema_slow + 3,
            momentum_window + 2,
            breakout_window + 3,
            atr_period + 3,
            volume_window + 3,
            volatility_window + 3,
            128,
        )
        self.close_history: deque[float] = deque(maxlen=history_size)
        self.high_history: deque[float] = deque(maxlen=history_size)
        self.low_history: deque[float] = deque(maxlen=history_size)
        self.volume_history: deque[float] = deque(maxlen=history_size)
        self.prev_above: bool | None = None
        self.last_signal_side: Side | None = None
        self.bars_since_signal = history_size

    @staticmethod
    def _clamp(lo: float, hi: float, value: float) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def _sma(values: list[float], window: int) -> float:
        return sum(values[-window:]) / window

    def _rsi(self, values: list[float]) -> float | None:
        if len(values) <= self.rsi_period:
            return None
        recent = values[-(self.rsi_period + 1) :]
        gains = 0.0
        losses = 0.0
        for idx in range(1, len(recent)):
            delta = recent[idx] - recent[idx - 1]
            if delta > 0:
                gains += delta
            else:
                losses += -delta
        avg_gain = gains / self.rsi_period
        avg_loss = losses / self.rsi_period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _bollinger(self, values: list[float]) -> tuple[float, float] | None:
        if len(values) < self.bollinger_window:
            return None
        window = values[-self.bollinger_window :]
        mean = sum(window) / len(window)
        variance = sum((v - mean) ** 2 for v in window) / len(window)
        std = sqrt(variance)
        lower = mean - self.bollinger_stddev * std
        upper = mean + self.bollinger_stddev * std
        return lower, upper

    def _ema_series(self, values: list[float], period: int) -> list[float]:
        alpha = 2.0 / (period + 1.0)
        ema = values[0]
        out = [ema]
        for price in values[1:]:
            ema = alpha * price + (1.0 - alpha) * ema
            out.append(ema)
        return out

    def _macd(self, values: list[float]) -> tuple[float, float] | None:
        need = self.macd_slow + self.macd_signal + 1
        if len(values) < need:
            return None
        fast_ema = self._ema_series(values, self.macd_fast)
        slow_ema = self._ema_series(values, self.macd_slow)
        macd_line_series = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_series = self._ema_series(macd_line_series, self.macd_signal)
        return macd_line_series[-1], signal_series[-1]

    def _atr(self, highs: list[float], lows: list[float], closes: list[float], period: int) -> float | None:
        if len(closes) < period + 1:
            return None
        trs: list[float] = []
        start = len(closes) - period
        for idx in range(start, len(closes)):
            prev_close = closes[idx - 1]
            tr = max(highs[idx] - lows[idx], abs(highs[idx] - prev_close), abs(lows[idx] - prev_close))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None

    def _rolling_zscore(self, values: list[float], window: int) -> float | None:
        if len(values) < window + 1:
            return None
        sample = values[-window - 1 : -1]
        mean = sum(sample) / len(sample)
        variance = sum((v - mean) ** 2 for v in sample) / len(sample)
        std = sqrt(variance)
        if std == 0:
            return 0.0
        return (values[-1] - mean) / std

    def _infer_regime(self, ema_fast: float, ema_slow: float, atr: float, price: float) -> tuple[str, float]:
        if price <= 0:
            return "unknown", 0.0
        normalized_atr = max(atr / price, 1e-6)
        trend_strength = abs(ema_fast - ema_slow) / (price * normalized_atr)
        if trend_strength >= self.regime_trend_threshold:
            return "trend", trend_strength
        if trend_strength <= self.regime_chop_threshold:
            return "chop", trend_strength
        return "neutral", trend_strength

    def _adaptive_size(self, base_size: float, signal_score: float, regime: str, atr_pct: float) -> tuple[float, float]:
        confidence = signal_score / self.min_signal_score
        confidence = self._clamp(0.5, 3.0, confidence)
        vol_scale = self.target_volatility_pct / max(atr_pct, 0.05)
        vol_scale = self._clamp(0.35, self.max_size_multiplier, vol_scale)
        regime_scale = 1.15 if regime == "trend" else 0.65 if regime == "chop" else 0.9
        raw_multiplier = vol_scale * regime_scale * self._clamp(0.6, 1.8, confidence)
        multiplier = self._clamp(0.2, self.max_size_multiplier, raw_multiplier)
        return max(base_size * multiplier, base_size * 0.2), confidence

    def _on_bar_classic(self, bar: MarketBar) -> Signal | None:
        values = list(self.close_history)
        if len(values) < self.long_window:
            return None

        short_ma = self._sma(values, self.short_window)
        long_ma = self._sma(values, self.long_window)
        above = short_ma > long_ma

        if self.prev_above is None:
            self.prev_above = above
            return None

        crossed_up = above and not self.prev_above
        crossed_down = (not above) and self.prev_above
        self.prev_above = above
        if not (crossed_up or crossed_down):
            return None

        buy_confirms: list[str] = []
        sell_confirms: list[str] = []

        if self.use_rsi:
            rsi = self._rsi(values)
            if rsi is not None:
                if rsi <= self.rsi_oversold:
                    buy_confirms.append("rsi_oversold")
                if rsi >= self.rsi_overbought:
                    sell_confirms.append("rsi_overbought")

        if self.use_bollinger:
            bands = self._bollinger(values)
            if bands is not None:
                lower, upper = bands
                if bar.close <= lower:
                    buy_confirms.append("bollinger_lower")
                if bar.close >= upper:
                    sell_confirms.append("bollinger_upper")

        if self.use_macd:
            macd = self._macd(values)
            if macd is not None:
                macd_line, signal_line = macd
                if macd_line > signal_line:
                    buy_confirms.append("macd_bull")
                if macd_line < signal_line:
                    sell_confirms.append("macd_bear")

        active_indicators = int(self.use_rsi) + int(self.use_bollinger) + int(self.use_macd)
        needed = min(self.min_confirmations, active_indicators) if active_indicators > 0 else 0

        if crossed_up and len(buy_confirms) >= needed:
            reason = "classic_ma_cross_up" if not buy_confirms else "classic_ma_cross_up+" + "+".join(buy_confirms)
            return Signal(symbol=bar.symbol, side=Side.BUY, size=self.order_size_units, reason=reason, score=1.0, confidence=1.0, regime="classic")

        if crossed_down and len(sell_confirms) >= needed:
            reason = "classic_ma_cross_down" if not sell_confirms else "classic_ma_cross_down+" + "+".join(sell_confirms)
            return Signal(symbol=bar.symbol, side=Side.SELL, size=self.order_size_units, reason=reason, score=1.0, confidence=1.0, regime="classic")

        return None

    def _on_bar_advanced(self, bar: MarketBar) -> Signal | None:
        closes = list(self.close_history)
        highs = list(self.high_history)
        lows = list(self.low_history)
        volumes = list(self.volume_history)

        min_bars = max(
            self.long_window,
            self.trend_ema_slow + 2,
            self.atr_period + 2,
            self.breakout_window + 2,
            self.volume_window + 2,
            self.momentum_window + 2,
            self.macd_slow + self.macd_signal + 2,
        )
        if len(closes) < min_bars:
            return None

        ema_fast_series = self._ema_series(closes, self.trend_ema_fast)
        ema_slow_series = self._ema_series(closes, self.trend_ema_slow)
        ema_fast = ema_fast_series[-1]
        ema_slow = ema_slow_series[-1]
        ema_slow_prev = ema_slow_series[-2]

        atr = self._atr(highs, lows, closes, self.atr_period)
        if atr is None or closes[-1] <= 0:
            return None
        atr_pct = (atr / closes[-1]) * 100.0

        rsi = self._rsi(closes) if self.use_rsi else None
        macd = self._macd(closes) if self.use_macd else None
        macd_hist = 0.0 if macd is None else macd[0] - macd[1]

        roc = 0.0
        if len(closes) > self.momentum_window:
            prev = closes[-1 - self.momentum_window]
            if prev > 0:
                roc = (closes[-1] / prev) - 1.0

        bollinger = self._bollinger(closes) if self.use_bollinger else None
        zscore = 0.0
        if bollinger is not None:
            lower, upper = bollinger
            width = upper - lower
            if width > 0:
                mid = (upper + lower) / 2.0
                zscore = (closes[-1] - mid) / (width / 2.0)

        prev_high_window = highs[-self.breakout_window - 1 : -1]
        prev_low_window = lows[-self.breakout_window - 1 : -1]
        breakout_up = bool(prev_high_window and closes[-1] > max(prev_high_window))
        breakout_down = bool(prev_low_window and closes[-1] < min(prev_low_window))

        volume_z = self._rolling_zscore(volumes, self.volume_window) if self.use_volume_confirmation else None
        regime, _trend_strength = self._infer_regime(ema_fast, ema_slow, atr, closes[-1])

        long_score = 0.0
        short_score = 0.0
        long_reasons: list[str] = []
        short_reasons: list[str] = []

        if ema_fast > ema_slow:
            long_score += 1.4
            long_reasons.append("ema_trend_up")
        else:
            short_score += 1.4
            short_reasons.append("ema_trend_down")

        if ema_slow > ema_slow_prev:
            long_score += 0.6
            long_reasons.append("slow_trend_rising")
        else:
            short_score += 0.6
            short_reasons.append("slow_trend_falling")

        if roc > 0:
            long_score += 0.8
            long_reasons.append("momentum_up")
        elif roc < 0:
            short_score += 0.8
            short_reasons.append("momentum_down")

        if rsi is not None:
            if rsi >= 55:
                long_score += 0.7
                long_reasons.append("rsi_bull_zone")
            if rsi <= 45:
                short_score += 0.7
                short_reasons.append("rsi_bear_zone")
            if rsi <= 30:
                long_score += 0.4
                long_reasons.append("rsi_oversold")
            if rsi >= 70:
                short_score += 0.4
                short_reasons.append("rsi_overbought")

        if macd_hist > 0:
            long_score += 0.8
            long_reasons.append("macd_positive")
        elif macd_hist < 0:
            short_score += 0.8
            short_reasons.append("macd_negative")

        if zscore <= -1.0:
            long_score += 0.7
            long_reasons.append("bollinger_rebound_zone")
        elif zscore >= 1.0:
            short_score += 0.7
            short_reasons.append("bollinger_fade_zone")

        if breakout_up:
            long_score += 1.0
            long_reasons.append("breakout_up")
        if breakout_down:
            short_score += 1.0
            short_reasons.append("breakout_down")

        if regime == "trend":
            if ema_fast > ema_slow and roc > 0:
                long_score += 0.4
                long_reasons.append("trend_regime_confirm")
            if ema_fast < ema_slow and roc < 0:
                short_score += 0.4
                short_reasons.append("trend_regime_confirm")
        elif regime == "chop":
            long_score *= 0.85
            short_score *= 0.85
            if abs(zscore) < 0.35:
                return None

        min_score = self.min_signal_score
        if self.use_volume_confirmation:
            if volume_z is not None and volume_z > 0.5:
                if long_score > short_score:
                    long_score += 0.35
                    long_reasons.append("volume_confirmation")
                elif short_score > long_score:
                    short_score += 0.35
                    short_reasons.append("volume_confirmation")
            else:
                min_score += 0.25

        score_gap = abs(long_score - short_score)
        if score_gap < self.score_hysteresis:
            return None

        if long_score > short_score:
            side = Side.BUY
            score = long_score
            reasons = long_reasons
        else:
            side = Side.SELL
            score = short_score
            reasons = short_reasons

        if score < min_score:
            return None

        if self.bars_since_signal < self.signal_cooldown_bars and side == self.last_signal_side:
            return None

        size, confidence = self._adaptive_size(self.order_size_units, score, regime, atr_pct)
        reason_tokens = reasons[:4] if reasons else ["signal"]
        reason = "advanced_" + "+".join(reason_tokens)

        self.last_signal_side = side
        self.bars_since_signal = 0
        return Signal(symbol=bar.symbol, side=side, size=size, reason=reason, score=score, confidence=confidence, regime=regime)

    def on_bar(self, bar: MarketBar) -> Signal | None:
        self.close_history.append(bar.close)
        self.high_history.append(bar.high)
        self.low_history.append(bar.low)
        self.volume_history.append(bar.volume)
        self.bars_since_signal += 1

        if self.mode == "classic":
            return self._on_bar_classic(bar)
        return self._on_bar_advanced(bar)
