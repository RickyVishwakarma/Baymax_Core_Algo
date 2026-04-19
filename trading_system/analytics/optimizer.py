import argparse
import itertools
import json
import logging
import time
from copy import deepcopy
from pathlib import Path

from trading_system.data.feed import CsvMarketDataFeed
from trading_system.engine import TradingEngine
from trading_system.strategy.registry import StrategyRegistry
from trading_system.risk.basic import BasicRiskManager
from trading_system.portfolio.manager import PortfolioManager
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.config import load_config
from trading_system.ml.regime import MultiSymbolRegimeClassifier

def get_permutations(param_grid: dict) -> list[dict]:
    """Converts a dict of lists into a list of permutation dicts."""
    keys, values = zip(*param_grid.items())
    return [dict(zip(keys, v)) for v in itertools.product(*values)]

class MockFeed:
    def __init__(self, bars):
        self.bars = bars
    def stream(self):
        for bar in self.bars:
            yield bar

def run_optimization():
    parser = argparse.ArgumentParser(description="Walk-Forward Analysis Optimizer")
    parser.add_argument("--symbol", required=True, help="Symbol to optimize (e.g., TCS)")
    parser.add_argument("--data", required=True, help="Path to historical CSV data")
    parser.add_argument("--config", default="config_multi.json", help="Path to base config")
    parser.add_argument("--grid", default="param_grid.json", help="Path to parameter grid definition")
    parser.add_argument("--out", default="optimized_params.json", help="Output file for best params")
    args = parser.parse_args()

    # Suppress heavy logging during optimization
    logging.getLogger("trading_system.engine").setLevel(logging.CRITICAL)
    logging.getLogger("trading_system.strategy").setLevel(logging.CRITICAL)
    
    print(f"--- Walk-Forward Optimizer ---")
    print(f"Target: {args.symbol}")
    print(f"Loading data from: {args.data}")

    # Load bars into memory for ultra-fast looping
    feed = CsvMarketDataFeed(path=args.data, symbol=args.symbol)
    bars = list(feed.stream())
    print(f"Loaded {len(bars)} 1-minute candles.")

    if not bars:
        print("Error: No data found in CSV.")
        return

    # Load Base Config & Grid
    cfg = load_config(args.config)
    grid_path = Path(args.grid)
    if not grid_path.exists():
        print(f"Error: Parameter grid {args.grid} not found.")
        return
        
    grid_data = json.loads(grid_path.read_text(encoding="utf-8"))
    strategy_name = cfg.strategy.get("name", "supertrend")
    
    if strategy_name not in grid_data:
        print(f"Error: Strategy '{strategy_name}' not found in param grid.")
        return
        
    permutations = get_permutations(grid_data[strategy_name])
    print(f"Generated {len(permutations)} parameter permutations to test.")

    best_score = -float('inf')
    best_params = None
    best_stats = {}

    start_time = time.time()
    
    for i, params in enumerate(permutations):
        # 1. Setup fresh components
        portfolio = PortfolioManager(starting_cash=cfg.starting_cash)
        
        # 2. Re-create strategy factory with current permutations
        def factory(symbol: str = None):
            return StrategyRegistry.build(strategy_name, **params)
            
        risk = BasicRiskManager(
            max_position_units=cfg.max_position_units,
            max_notional_per_order=cfg.max_notional_per_order,
            max_drawdown_pct=cfg.max_drawdown_pct,
            allow_short=cfg.allow_short,
            max_exposure_pct=cfg.max_exposure_pct,
            max_bar_range_pct=cfg.max_bar_range_pct,
            min_cash_buffer_pct=cfg.min_cash_buffer_pct,
        )
        
        regime_classifier = None
        if cfg.ml_regime.get("enabled", False):
            regime_classifier = MultiSymbolRegimeClassifier(
                window=int(cfg.ml_regime.get("window", 14)),
                block_threshold=float(cfg.ml_regime.get("block_threshold", 0.35)),
                pass_threshold=float(cfg.ml_regime.get("pass_threshold", 0.55)),
                ci_weight=float(cfg.ml_regime.get("ci_weight", 0.5)),
                breakout_atr_multiplier=float(cfg.ml_regime.get("breakout_atr_multiplier", 2.0))
            )
            
        engine = TradingEngine(
            data_feed=MockFeed(bars), # Run entirely in-memory
            strategy_factory=factory,
            risk_manager=risk,
            execution=PaperExecutionHandler(fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps),
            portfolio=portfolio,
            trailing_stop_pct=cfg.trailing_stop_pct,
            min_velocity_threshold=cfg.min_velocity_threshold,
            regime_classifier=regime_classifier,
            atr_trailing_stop=cfg.atr_trailing_stop,
            position_sizing=cfg.position_sizing,
            mtf_alignment=cfg.mtf_alignment,
        )

        try:
            engine.run()
        except Exception as e:
            print(f"Run failed for params {params}: {e}")
            continue

        # 3. Evaluate Fitness
        net_profit = portfolio.state.equity - cfg.starting_cash
        
        if net_profit > best_score:
            best_score = net_profit
            best_params = params
            best_stats = {"equity": portfolio.state.equity, "net_profit": net_profit}
            
        if (i + 1) % 10 == 0 or (i + 1) == len(permutations):
            print(f"[{i+1}/{len(permutations)}] Tested. Best PnL: {round(best_score, 2)}")

    elapsed = time.time() - start_time
    print(f"\n--- Optimization Complete in {round(elapsed, 2)}s ---")
    
    if best_params is None:
        print("No profitable permutations found.")
        return
        
    print(f"Best Parameters: {best_params}")
    print(f"Net Profit: +{round(best_stats['net_profit'], 2)}")

    # 4. Save to Override File
    out_path = Path(args.out)
    overrides = {}
    if out_path.exists():
        overrides = json.loads(out_path.read_text(encoding="utf-8"))
        
    overrides[args.symbol] = {
        "strategy": {
            "name": strategy_name,
            "params": best_params
        }
    }
    
    out_path.write_text(json.dumps(overrides, indent=2), encoding="utf-8")
    print(f"Saved optimized parameters to {args.out}")

if __name__ == "__main__":
    run_optimization()
