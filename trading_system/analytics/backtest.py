from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
import json


@dataclass(slots=True)
class BacktestReport:
    bars: int
    trade_count: int
    buy_count: int
    sell_count: int
    start_equity: float
    end_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    volatility_pct: float
    sharpe_like: float
    win_rate_pct: float
    avg_trade_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _safe_mean(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _safe_stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _safe_mean(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return sqrt(variance)


def _compute_max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * 100.0


def _compute_trade_pnls(fills: list[tuple[str, str, float, float, float]]) -> list[float]:
    # fills: (ts, side, size, fill_price, fee)
    position_units = 0.0
    avg_entry_price = 0.0
    trade_pnls: list[float] = []

    for _ts, side, size, price, fee in fills:
        signed = size if side == "BUY" else -size
        prior_units = position_units
        next_units = prior_units + signed

        realized = 0.0
        if prior_units == 0 or (prior_units > 0) == (signed > 0):
            gross_cost = (abs(prior_units) * avg_entry_price) + (abs(signed) * price)
            position_units = next_units
            avg_entry_price = (gross_cost / abs(next_units)) if next_units != 0 else 0.0
        else:
            closing_qty = min(abs(prior_units), abs(signed))
            if prior_units > 0:
                realized = (price - avg_entry_price) * closing_qty
            else:
                realized = (avg_entry_price - price) * closing_qty
            position_units = next_units
            if next_units == 0:
                avg_entry_price = 0.0
            elif (prior_units > 0) != (next_units > 0):
                avg_entry_price = price
            trade_pnls.append(realized - fee)

    return trade_pnls


def build_backtest_report(
    equities: list[float],
    fills: list[tuple[str, str, float, float, float]],
) -> BacktestReport:
    if not equities:
        return BacktestReport(
            bars=0,
            trade_count=0,
            buy_count=0,
            sell_count=0,
            start_equity=0.0,
            end_equity=0.0,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            volatility_pct=0.0,
            sharpe_like=0.0,
            win_rate_pct=0.0,
            avg_trade_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
        )

    returns: list[float] = []
    for i in range(1, len(equities)):
        prev = equities[i - 1]
        if prev > 0:
            returns.append((equities[i] / prev) - 1.0)

    mean_ret = _safe_mean(returns)
    std_ret = _safe_stdev(returns)
    sharpe_like = (mean_ret / std_ret * sqrt(len(returns))) if std_ret > 0 else 0.0
    volatility_pct = std_ret * 100.0

    start_equity = equities[0]
    end_equity = equities[-1]
    total_return_pct = ((end_equity / start_equity) - 1.0) * 100.0 if start_equity > 0 else 0.0
    max_drawdown_pct = _compute_max_drawdown_pct(equities)

    trade_pnls = _compute_trade_pnls(fills)
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    win_rate = (len(wins) / len(trade_pnls) * 100.0) if trade_pnls else 0.0
    avg_trade_pnl = _safe_mean(trade_pnls)

    buy_count = sum(1 for _ts, side, _size, _px, _fee in fills if side == "BUY")
    sell_count = sum(1 for _ts, side, _size, _px, _fee in fills if side == "SELL")

    return BacktestReport(
        bars=len(equities),
        trade_count=len(fills),
        buy_count=buy_count,
        sell_count=sell_count,
        start_equity=start_equity,
        end_equity=end_equity,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        volatility_pct=volatility_pct,
        sharpe_like=sharpe_like,
        win_rate_pct=win_rate,
        avg_trade_pnl=avg_trade_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
    )


def report_to_markdown(report: BacktestReport) -> str:
    return "\n".join(
        [
            "# Backtest Report",
            "",
            f"- Bars: {report.bars}",
            f"- Trades: {report.trade_count} (BUY: {report.buy_count}, SELL: {report.sell_count})",
            f"- Start equity: {report.start_equity:.2f}",
            f"- End equity: {report.end_equity:.2f}",
            f"- Total return (%): {report.total_return_pct:.4f}",
            f"- Max drawdown (%): {report.max_drawdown_pct:.4f}",
            f"- Volatility (%): {report.volatility_pct:.4f}",
            f"- Sharpe-like: {report.sharpe_like:.4f}",
            f"- Win rate (%): {report.win_rate_pct:.2f}",
            f"- Avg trade PnL: {report.avg_trade_pnl:.4f}",
            f"- Gross profit: {report.gross_profit:.4f}",
            f"- Gross loss: {report.gross_loss:.4f}",
            f"- Profit factor: {report.profit_factor:.4f}",
            "",
        ]
    )
