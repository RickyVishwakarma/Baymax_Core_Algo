from __future__ import annotations

import argparse
import copy
import itertools
import json
import logging
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from typing import Any

from trading_system.analytics.backtest import BacktestReport, build_backtest_report
from trading_system.config import TradingConfig, load_config
from trading_system.data.feed import CsvMarketDataFeed, MarketDataFeed
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
        return strategy_patch, report
    except Exception as e:
        return strategy_patch, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Grid Search Optimizer for Trading Strategy")
    parser.add_argument("--config", required=True, help="Base JSON config path")
    parser.add_argument("--data", required=True, help="Path to CSV dataset")
    parser.add_argument("--grid", required=True, help="Path to param_grid.json")
    parser.add_argument("--workers", type=int, default=0, help="Max parallel workers (0 = auto)")
    parser.add_argument("--top-n", type=int, default=10, help="Show top N results")
    return parser


def load_grid(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        grid_def = json.load(f)
    keys = list(grid_def.keys())
    values = list(grid_def.values())
    combinations = list(itertools.product(*values))
    return [dict(zip(keys, combo)) for combo in combinations]


def main() -> None:
    disable_noisy_logs()
    args = build_parser().parse_args()

    print(f"Loading config from: {args.config}")
    cfg = load_config(args.config)
    
    print(f"Loading data from: {args.data}")
    csv_feed = CsvMarketDataFeed(path=args.data, symbol=cfg.symbol)
    bars = list(csv_feed.stream())
    print(f"Loaded {len(bars)} bars into memory.")

    print(f"Loading grid from: {args.grid}")
    patches = load_grid(args.grid)
    print(f"Generated {len(patches)} parameter combinations.")
    
    if len(bars) < 10:
        print("Not enough bars to run meaningful backtest. Exiting.")
        sys.exit(1)

    workers = args.workers if args.workers > 0 else None
    results: list[tuple[dict[str, Any], BacktestReport]] = []
    
    print(f"Starting parallel optimization (workers={workers or 'auto'})...")
    start_time = time.time()
    
    progress = 0
    total = len(patches)
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = []
        for patch in patches:
            futures.append(executor.submit(run_single_backtest, cfg, patch, bars))
            
        for future in as_completed(futures):
            patch, report = future.result()
            progress += 1
            if report is not None:
                results.append((patch, report))
            
            if progress % 10 == 0 or progress == total:
                print(f"Progress: {progress}/{total} ({(progress/total)*100:.1f}%)", end="\r")

    elapsed = time.time() - start_time
    print(f"\nOptimization complete in {elapsed:.2f}s")
    
    if not results:
        print("No valid results were generated.")
        sys.exit(0)
    
    # Sort results by Profit Factor or Sharpe Ratio
    sorted_results = sorted(results, key=lambda x: x[1].sharpe_like, reverse=True)
    
    print(f"\n--- Top {args.top_n} Results (Sorted by Sharpe Ratio) ---")
    for i, (patch, report) in enumerate(sorted_results[:args.top_n], start=1):
        print(f"#{i}")
        print(f"  Params: {patch}")
        print(f"  Sharpe: {report.sharpe_like:.3f} | Profit Factor: {report.profit_factor:.3f}")
        print(f"  Return: {report.total_return_pct:.2f}% | Max DD: {report.max_drawdown_pct:.2f}%")
        print(f"  Trades: {report.trade_count} | Win Rate: {report.win_rate_pct:.1f}%")
        print()

if __name__ == "__main__":
    main()
