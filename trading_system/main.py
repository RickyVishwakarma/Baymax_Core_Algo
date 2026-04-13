from __future__ import annotations

import argparse
import json
import logging
import os
import queue
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from trading_system.analytics import build_backtest_report, report_to_markdown
from trading_system.config import load_config
from trading_system.data.feed import CsvMarketDataFeed, TradingViewPollingFeed, DhanWebSocketFeed, fetch_tradingview_quotes
from trading_system.data.dhan_manager import DhanInstrumentManager
from trading_system.engine import TradingEngine
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.execution.dhan import DhanExecutionHandler
from trading_system.execution.groww import GrowwExecutionHandler
from trading_system.ml.regime import MultiSymbolRegimeClassifier
from trading_system.portfolio.manager import PortfolioManager
from trading_system.predict import predict_next_open
from trading_system.risk.basic import BasicRiskManager
from trading_system.storage import SQLiteRunStore
from trading_system.strategy.registry import StrategyRegistry


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated trading system runner")
    parser.add_argument("--config", required=False, help="Path to JSON config")
    parser.add_argument("--source", choices=["csv", "tradingview", "dhan_v2"], required=False, help="Override data source")
    parser.add_argument("--data", required=False, help="CSV path when source=csv")
    parser.add_argument("--max-bars", type=int, required=False, help="Stop after N bars (useful for testing)")
    parser.add_argument(
        "--predict-next-open",
        action="store_true",
        help="Estimate the next trading session open using historical daily gaps",
    )
    parser.add_argument("--lookback-days", type=int, default=120, help="History window for prediction fetch")
    parser.add_argument("--gap-window", type=int, default=20, help="Recent gap samples used for prediction")
    parser.add_argument("--quote-only", action="store_true", help="Fetch latest OHLC quote only (no prediction/trading)")
    parser.add_argument("--db-path", default="trading_runs.db", help="SQLite database path for persistent run storage")
    parser.add_argument("--disable-storage", action="store_true", help="Disable persistent run storage")
    parser.add_argument("--report-path", required=False, help="Write analytics report (.md or .json)")
    parser.add_argument("--run-name", required=False, help="Optional run label stored in DB")
    parser.add_argument("--execution", choices=["paper", "dhan", "groww"], required=False, help="Execution mode")
    return parser


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    cfg = load_config(args.config)

    if args.predict_next_open:
        for symbol in cfg.data.tradingview_symbols:
            try:
                pred = predict_next_open(
                    screener=cfg.data.tradingview_screener,
                    exchange=cfg.data.tradingview_exchange,
                    symbol=symbol,
                    lookback_days=args.lookback_days,
                    gap_window=args.gap_window,
                )
                print(f"--- Prediction: {pred.symbol} ---")
                print("Reference close:", round(pred.reference_close, 2))
                print("Predicted next open:", round(pred.predicted_open, 2))
                print("Range (1-sigma):", round(pred.lower_bound, 2), "to", round(pred.upper_bound, 2))
                print("Avg overnight gap (%):", round(pred.avg_gap_pct, 4))
                print("Gap volatility (%):", round(pred.stdev_gap_pct, 4))
                print("Observations:", pred.observations)
                print("")
            except Exception as e:
                print(f"Error predicting {symbol}: {e}")
        return

    source = (args.source or cfg.data.source).lower()
    if args.quote_only:
        if source == "tradingview":
            quotes = fetch_tradingview_quotes(
                screener=cfg.data.tradingview_screener,
                exchange=cfg.data.tradingview_exchange,
                symbols=cfg.data.tradingview_symbols,
                request_timeout_seconds=cfg.data.request_timeout_seconds,
            )
        elif source == "dhan_v2":
            # For Dhan WebSocket, we connect, wait for one bar/packet, and exit
            client_id = os.getenv("DHAN_CLIENT_ID")
            access_token = os.getenv("DHAN_ACCESS_TOKEN")
            if not client_id or not access_token:
                raise ValueError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set for dhan_v2")
            
            inst_mgr = DhanInstrumentManager()
            feed = DhanWebSocketFeed(
                client_id=client_id,
                access_token=access_token,
                exchange=cfg.data.dhan_exchange,
                symbols=cfg.data.dhan_symbols or cfg.symbols,
                instrument_manager=inst_mgr
            )
            print("Connecting to Dhan WebSocket for quote check (waiting up to 15s)...")
            
            # Start the background thread (usually done by feed.stream())
            import threading
            feed_thread = threading.Thread(target=feed._run_socket_loop, daemon=True)
            feed_thread.start()
            
            quotes = []
            try:
                # We wait for the aggregator to emit bars into the queue
                while len(quotes) < len(cfg.symbols):
                    try:
                        bar = feed._queue.get(timeout=15)
                        quotes.append(bar)
                    except queue.Empty:
                        print("Timeout: No market data received within 15s. (Market might be closed)")
                        break
            except Exception as e:
                print(f"Error during quote fetch: {e}")
            finally:
                feed._socket_client.stop()
                feed_thread.join(timeout=1)
        else:
            raise ValueError(f"Quote only not supported for source: {source}")

        for quote in quotes:
            print("Symbol:", quote.symbol)
            print("Timestamp (UTC):", quote.ts.isoformat())
            print("Close:", round(quote.close, 6))
            print("---")
        return

    source = (args.source or cfg.data.source).lower()
    if source == "csv":
        csv_path = args.data or cfg.data.csv_path
        if not csv_path:
            raise ValueError("CSV source selected but no path provided. Use --data or data.csv_path in config.")
        data_feed = CsvMarketDataFeed(path=csv_path, symbol=cfg.symbols[0])
    elif source == "tradingview":
        max_bars = args.max_bars if args.max_bars is not None else cfg.data.max_bars
        data_feed = TradingViewPollingFeed(
            screener=cfg.data.tradingview_screener,
            exchange=cfg.data.tradingview_exchange,
            symbols=cfg.data.tradingview_symbols,
            poll_seconds=cfg.data.poll_seconds,
            max_bars=max_bars,
            emit_on_same_timestamp=cfg.data.emit_on_same_timestamp,
            request_timeout_seconds=cfg.data.request_timeout_seconds,
            retry_delay_seconds=cfg.data.retry_delay_seconds,
        )
    elif source == "dhan_v2":
        client_id = os.getenv("DHAN_CLIENT_ID")
        access_token = os.getenv("DHAN_ACCESS_TOKEN")
        if not client_id or not access_token:
            raise ValueError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env for dhan_v2 source.")
            
        inst_mgr = DhanInstrumentManager()
        data_feed = DhanWebSocketFeed(
            client_id=client_id,
            access_token=access_token,
            exchange=cfg.data.dhan_exchange,
            symbols=cfg.data.dhan_symbols or cfg.symbols,
            instrument_manager=inst_mgr
        )
    else:
        raise ValueError(f"Unsupported source: {source}")

    strategy_name = cfg.strategy.get("name", "moving_average")
    strategy_params = cfg.strategy.get("params", {})
    strategy_factory = lambda: StrategyRegistry.build(strategy_name, **strategy_params)
    risk = BasicRiskManager(
        max_position_units=cfg.max_position_units,
        max_notional_per_order=cfg.max_notional_per_order,
        max_drawdown_pct=cfg.max_drawdown_pct,
        allow_short=cfg.allow_short,
        max_exposure_pct=cfg.max_exposure_pct,
        max_bar_range_pct=cfg.max_bar_range_pct,
        min_cash_buffer_pct=cfg.min_cash_buffer_pct,
    )
    execution_type = (args.execution or cfg.execution.get("type", "paper")).lower()
    if execution_type == "groww":
        api_key = os.getenv("GROWW_API_KEY")
        api_secret = os.getenv("GROWW_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("GROWW_API_KEY and GROWW_API_SECRET must be set in .env for groww execution.")
        execution = GrowwExecutionHandler(api_key=api_key, api_secret=api_secret)
    elif execution_type == "dhan":
        client_id = os.getenv("DHAN_CLIENT_ID")
        access_token = os.getenv("DHAN_ACCESS_TOKEN")
        if not client_id or not access_token:
            raise ValueError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env for dhan execution.")
        inst_mgr = DhanInstrumentManager()
        execution = DhanExecutionHandler(
            client_id=client_id,
            access_token=access_token,
            instrument_manager=inst_mgr,
            product_type=cfg.execution.get("product_type", "INTRADAY"),
            exchange=cfg.data.dhan_exchange
        )
    else:
        execution = PaperExecutionHandler(fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps)
    portfolio = PortfolioManager(starting_cash=cfg.starting_cash)

    # ── AI Regime Classifier (optional) ──────────────────────────────
    regime_classifier: MultiSymbolRegimeClassifier | None = None
    ml_cfg = cfg.ml_regime
    if ml_cfg.get("enabled", False):
        regime_classifier = MultiSymbolRegimeClassifier(
            window=int(ml_cfg.get("window", 14)),
            block_threshold=float(ml_cfg.get("block_threshold", 0.35)),
            pass_threshold=float(ml_cfg.get("pass_threshold", 0.55)),
            ci_weight=float(ml_cfg.get("ci_weight", 0.5)),
        )
        logging.getLogger(__name__).info(
            "ml_regime enabled window=%d block=%.2f pass=%.2f",
            int(ml_cfg.get("window", 14)),
            float(ml_cfg.get("block_threshold", 0.35)),
            float(ml_cfg.get("pass_threshold", 0.55)),
        )
    # ─────────────────────────────────────────────────────────────────

    store: SQLiteRunStore | None = None
    run_id: int | None = None
    equity_points: list[float] = []
    fills_for_report: list[tuple[str, str, float, float, float]] = []

    def on_bar(bar, pf) -> None:
        equity_points.append(pf.state.equity)
        if store is not None and run_id is not None:
            store.record_bar(
                run_id=run_id,
                ts=bar.ts,
                symbol=bar.symbol,
                close=bar.close,
                equity=pf.state.equity,
                cash=pf.state.cash,
                units=pf.get_position(bar.symbol).units,
            )

    def on_fill(bar, fill, signal, pf) -> None:
        fills_for_report.append((bar.ts.isoformat(), fill.side.value, fill.size, fill.fill_price, fill.fee_paid))
        if store is not None and run_id is not None:
            store.record_fill(run_id=run_id, ts=bar.ts, fill=fill, signal=signal, equity_after=pf.state.equity)

    if not args.disable_storage:
        store = SQLiteRunStore(args.db_path)
        config_obj = None
        if args.config and Path(args.config).exists():
            config_obj = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
        run_id = store.start_run(
            symbol=",".join(cfg.symbols),
            source=source,
            strategy_mode=strategy_name,
            run_name=args.run_name,
            config_obj=config_obj,
        )

    engine = TradingEngine(
        data_feed=data_feed,
        strategy_factory=strategy_factory,
        risk_manager=risk,
        execution=execution,
        portfolio=portfolio,
        trailing_stop_pct=cfg.trailing_stop_pct,
        regime_classifier=regime_classifier,
        on_bar_callback=on_bar,
        on_fill_callback=on_fill,
    )

    status = "completed"
    try:
        engine.run()
    except Exception:
        status = "failed"
        raise

    print("Final cash:", round(portfolio.state.cash, 2))
    print("Final equity:", round(portfolio.state.equity, 2))
    for sym, pos in portfolio.positions.items():
        if pos.units != 0:
            print(f"Final units [{sym}]:", round(pos.units, 6))

    report = build_backtest_report(equity_points, fills_for_report)
    print("Trades:", report.trade_count, "Win rate (%):", round(report.win_rate_pct, 2), "Max DD (%):", round(report.max_drawdown_pct, 4))
    print("Return (%):", round(report.total_return_pct, 4), "Sharpe-like:", round(report.sharpe_like, 4), "Profit factor:", round(report.profit_factor, 4))

    if args.report_path:
        report_path = Path(args.report_path)
        report_text = report.to_json() if report_path.suffix.lower() == ".json" else report_to_markdown(report)
        report_path.write_text(report_text, encoding="utf-8")

    if store is not None and run_id is not None:
        store.end_run(
            run_id=run_id,
            final_cash=portfolio.state.cash,
            final_equity=portfolio.state.equity,
            final_units=sum(p.units for p in portfolio.positions.values()),
            status=status,
        )


if __name__ == "__main__":
    main()
