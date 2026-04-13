from __future__ import annotations

import copy
import logging
from collections.abc import Iterator
from typing import Any

from trading_system.analytics.backtest import BacktestReport, build_backtest_report
from trading_system.config import TradingConfig
from trading_system.data.feed import MarketDataFeed
from trading_system.engine import TradingEngine
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.models import MarketBar
from trading_system.portfolio.manager import PortfolioManager
from trading_system.risk.basic import BasicRiskManager
from trading_system.strategy.registry import StrategyRegistry

def disable_noisy_logs() -> None:
    logging.getLogger("trading_system.engine").setLevel(logging.WARNING)
    logging.getLogger("trading_system.data.feed").setLevel(logging.WARNING)


class InMemoryMarketDataFeed(MarketDataFeed):
    def __init__(self, bars: list[MarketBar]):
        self.bars = bars

    def stream(self) -> Iterator[MarketBar]:
        yield from self.bars


def run_single_backtest(cfg: TradingConfig, strategy_patch: dict[str, Any], bars: list[MarketBar]) -> tuple[dict[str, Any], BacktestReport | None]:
    """Runs a single backtest for the provided config overrides, returning the metrics."""
    # Apply strategy patch
    local_cfg = copy.deepcopy(cfg)
    
    strategy_name = local_cfg.strategy.get("name", "moving_average")
    strategy_params = local_cfg.strategy.get("params", {})
    
    for k, v in strategy_patch.items():
        strategy_params[k] = v
        
    local_cfg.strategy["name"] = strategy_name
    local_cfg.strategy["params"] = strategy_params
    
    # Initialize components
    def strategy_factory():
        return StrategyRegistry.build(strategy_name, **strategy_params)

    risk = BasicRiskManager(
        max_position_units=local_cfg.max_position_units,
        max_notional_per_order=local_cfg.max_notional_per_order,
        max_drawdown_pct=local_cfg.max_drawdown_pct,
        allow_short=local_cfg.allow_short,
        max_exposure_pct=local_cfg.max_exposure_pct,
        max_bar_range_pct=local_cfg.max_bar_range_pct,
        min_cash_buffer_pct=local_cfg.min_cash_buffer_pct,
    )
    
    execution = PaperExecutionHandler(fee_bps=local_cfg.fee_bps, slippage_bps=local_cfg.slippage_bps)
    portfolio = PortfolioManager(starting_cash=local_cfg.starting_cash)
    data_feed = InMemoryMarketDataFeed(bars)
    
    equity_points: list[float] = []
    fills: list[tuple[str, str, float, float, float]] = []
    
    def on_bar(bar: MarketBar, pf: PortfolioManager) -> None:
        equity_points.append(pf.state.equity)
        
    def on_fill(bar: MarketBar, fill, signal, pf: PortfolioManager) -> None:
        fills.append((bar.ts.isoformat(), fill.side.value, fill.size, fill.fill_price, fill.fee_paid))
        
    engine = TradingEngine(
        data_feed=data_feed,
        strategy_factory=strategy_factory,
        risk_manager=risk,
        execution=execution,
        portfolio=portfolio,
        trailing_stop_pct=local_cfg.trailing_stop_pct,
        on_bar_callback=on_bar,
        on_fill_callback=on_fill
    )
    
    try:
        engine.run()
        report = build_backtest_report(equity_points, fills)
        return strategy_patch, {
            "report": report,
            "fills": fills,
            "equities": equity_points
        }
    except Exception:
        return strategy_patch, None
