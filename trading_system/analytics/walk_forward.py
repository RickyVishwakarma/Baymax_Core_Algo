from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

from trading_system.analytics.backtest import BacktestReport, build_backtest_report, report_to_markdown
from trading_system.analytics.runner import (
    run_single_backtest,
    disable_noisy_logs
)
from trading_system.config import load_config
from trading_system.data.feed import CsvMarketDataFeed
from trading_system.analytics.optimizer import load_grid


def main() -> None:
    disable_noisy_logs()
    
    parser = argparse.ArgumentParser(description="Walk-Forward Analysis (WFA) Engine")
    parser.add_argument("--config", required=True, help="Base JSON config path")
    parser.add_argument("--data", required=True, help="Path to CSV dataset")
    parser.add_argument("--grid", required=True, help="Path to parameter grid JSON")
    parser.add_argument("--is-bars", type=int, default=1000, help="In-Sample window size (bars)")
    parser.add_argument("--oos-bars", type=int, default=200, help="Out-of-Sample window size (bars)")
    parser.add_argument("--step-bars", type=int, default=200, help="Step size for rolling windows (usually = oos-bars)")
    parser.add_argument("--workers", type=int, default=0, help="Max parallel workers (0 = auto)")
    parser.add_argument("--metric", default="sharpe_like", choices=["sharpe_like", "profit_factor", "total_return_pct"],
                        help="Metric to optimize in each IS period")
    args = parser.parse_args()

    # 1. Load context
    cfg = load_config(args.config)
    csv_feed = CsvMarketDataFeed(path=args.data, symbol=cfg.symbols[0] if cfg.symbols else "UNKNOWN")
    full_bars = list(csv_feed.stream())
    patches = load_grid(args.grid)
    workers = args.workers if args.workers > 0 else None
    
    print(f"Loaded {len(full_bars)} bars and {len(patches)} parameter combinations.")
    
    # 2. Iterate through windows
    start_idx = 0
    oos_fills = []
    oos_equities = [cfg.starting_cash]
    
    windows: list[dict[str, Any]] = []
    
    while start_idx + args.is_bars + args.oos_bars <= len(full_bars):
        is_end = start_idx + args.is_bars
        oos_end = is_end + args.oos_bars
        
        is_bars = full_bars[start_idx : is_end]
        oos_bars = full_bars[is_end : oos_end]
        
        print(f"\n--- Window {len(windows)+1}: IS[{start_idx}:{is_end}] OOS[{is_end}:{oos_end}] ---")
        
        # A. Optimize on IS window
        is_results = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(run_single_backtest, cfg, p, is_bars) for p in patches]
            for future in as_completed(futures):
                p, res = future.result()
                if res:
                    is_results.append((p, res["report"]))
        
        if not is_results:
            print("  [WARN] No valid IS results. Skipping window.")
            start_idx += args.step_bars
            continue
            
        # Pick winner
        winner_patch, winner_report = max(is_results, key=lambda x: getattr(x[1], args.metric))
        print(f"  Best Params: {winner_patch}")
        print(f"  IS {args.metric}: {getattr(winner_report, args.metric):.4f}")
        
        # B. Test on OOS window
        oos_p, oos_res = run_single_backtest(cfg, winner_patch, oos_bars)
        
        if oos_res:
            oos_report = oos_res["report"]
            print(f"  OOS Result: {oos_report.total_return_pct:.2f}% return | {oos_report.trade_count} trades")
            
            # Record results for consolidation
            for f in oos_res["fills"]:
                oos_fills.append(f)
            
            # For the equity curve stitching: 
            # We add normalized OOS returns to the last known equity
            last_eq = oos_equities[-1]
            for eq in oos_res["equities"][1:]: # Skip first bar to avoid overlap
                # This is a simplification: assuming 100% of equity used in each window back-to-back
                returns = eq / oos_res["equities"][0]
                oos_equities.append(last_eq * returns)
            
        start_idx += args.step_bars

    # 3. Summary Report
    if not oos_fills and len(oos_equities) <= 1:
        print("No windows completed with valid results.")
        return
        
    master_oos_report = build_backtest_report(oos_equities, oos_fills)
    
    print("\n" + "="*40)
    print("WALK-FORWARD ANALYSIS COMPLETE (MASTER OOS REPORT)")
    print("="*40)
    print(report_to_markdown(master_oos_report))
    
    # Calculate WFO Efficiency Ratio
    # Average IS return vs Average OOS return (annualized or per-bar)
    # For now, just show the totals
    print(f"Total Windows: {len(oos_fills) // max(1, len(oos_fills)) if oos_fills else 0} simulated segments.")
    print(f"Final OOS Equity: {master_oos_report.end_equity:.2f}")

if __name__ == "__main__":
    main()
