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
from trading_system.analytics.runner import (
    InMemoryMarketDataFeed,
    run_single_backtest,
    disable_noisy_logs
)
from trading_system.config import TradingConfig, load_config
from trading_system.data.feed import CsvMarketDataFeed
from trading_system.models import MarketBar


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
    csv_feed = CsvMarketDataFeed(path=args.data, symbol=cfg.symbols[0] if cfg.symbols else "UNKNOWN")
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
            patch, result = future.result()
            progress += 1
            if result is not None:
                report = result["report"]
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
