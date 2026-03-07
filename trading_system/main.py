from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from trading_system.analytics import build_backtest_report, report_to_markdown
from trading_system.config import load_config
from trading_system.data.feed import CsvMarketDataFeed, TradingViewPollingFeed
from trading_system.engine import TradingEngine
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.portfolio.manager import PortfolioManager
from trading_system.predict import predict_next_open
from trading_system.risk.basic import BasicRiskManager
from trading_system.storage import SQLiteRunStore
from trading_system.strategy.moving_average import MovingAverageCrossStrategy


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated trading system runner")
    parser.add_argument("--config", required=False, help="Path to JSON config")
    parser.add_argument("--source", choices=["csv", "tradingview"], required=False, help="Override data source")
    parser.add_argument("--data", required=False, help="CSV path when source=csv")
    parser.add_argument("--max-bars", type=int, required=False, help="Stop after N bars (useful for testing)")
    parser.add_argument(
        "--predict-next-open",
        action="store_true",
        help="Estimate the next trading session open using historical daily gaps",
    )
    parser.add_argument("--lookback-days", type=int, default=120, help="History window for prediction fetch")
    parser.add_argument("--gap-window", type=int, default=20, help="Recent gap samples used for prediction")
    parser.add_argument("--db-path", default="trading_runs.db", help="SQLite database path for persistent run storage")
    parser.add_argument("--disable-storage", action="store_true", help="Disable persistent run storage")
    parser.add_argument("--report-path", required=False, help="Write analytics report (.md or .json)")
    parser.add_argument("--run-name", required=False, help="Optional run label stored in DB")
    return parser


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    cfg = load_config(args.config)

    if args.predict_next_open:
        pred = predict_next_open(
            screener=cfg.data.tradingview_screener,
            exchange=cfg.data.tradingview_exchange,
            symbol=cfg.data.tradingview_symbol,
            lookback_days=args.lookback_days,
            gap_window=args.gap_window,
        )
        print("Symbol:", pred.symbol)
        print("Reference close:", round(pred.reference_close, 2))
        print("Predicted next open:", round(pred.predicted_open, 2))
        print("Range (1-sigma):", round(pred.lower_bound, 2), "to", round(pred.upper_bound, 2))
        print("Avg overnight gap (%):", round(pred.avg_gap_pct, 4))
        print("Gap volatility (%):", round(pred.stdev_gap_pct, 4))
        print("Observations:", pred.observations)
        return

    source = (args.source or cfg.data.source).lower()
    if source == "csv":
        csv_path = args.data or cfg.data.csv_path
        if not csv_path:
            raise ValueError("CSV source selected but no path provided. Use --data or data.csv_path in config.")
        data_feed = CsvMarketDataFeed(path=csv_path, symbol=cfg.symbol)
    elif source == "tradingview":
        max_bars = args.max_bars if args.max_bars is not None else cfg.data.max_bars
        data_feed = TradingViewPollingFeed(
            screener=cfg.data.tradingview_screener,
            exchange=cfg.data.tradingview_exchange,
            symbol=cfg.data.tradingview_symbol,
            poll_seconds=cfg.data.poll_seconds,
            max_bars=max_bars,
            emit_on_same_timestamp=cfg.data.emit_on_same_timestamp,
            request_timeout_seconds=cfg.data.request_timeout_seconds,
            retry_delay_seconds=cfg.data.retry_delay_seconds,
        )
    else:
        raise ValueError(f"Unsupported source: {source}")

    strategy = MovingAverageCrossStrategy(
        mode=cfg.strategy.mode,
        short_window=cfg.strategy.short_window,
        long_window=cfg.strategy.long_window,
        order_size_units=cfg.strategy.order_size_units,
        use_rsi=cfg.strategy.use_rsi,
        rsi_period=cfg.strategy.rsi_period,
        rsi_oversold=cfg.strategy.rsi_oversold,
        rsi_overbought=cfg.strategy.rsi_overbought,
        use_bollinger=cfg.strategy.use_bollinger,
        bollinger_window=cfg.strategy.bollinger_window,
        bollinger_stddev=cfg.strategy.bollinger_stddev,
        use_macd=cfg.strategy.use_macd,
        macd_fast=cfg.strategy.macd_fast,
        macd_slow=cfg.strategy.macd_slow,
        macd_signal=cfg.strategy.macd_signal,
        min_confirmations=cfg.strategy.min_confirmations,
        trend_ema_fast=cfg.strategy.trend_ema_fast,
        trend_ema_slow=cfg.strategy.trend_ema_slow,
        momentum_window=cfg.strategy.momentum_window,
        breakout_window=cfg.strategy.breakout_window,
        volatility_window=cfg.strategy.volatility_window,
        atr_period=cfg.strategy.atr_period,
        target_volatility_pct=cfg.strategy.target_volatility_pct,
        min_signal_score=cfg.strategy.min_signal_score,
        max_size_multiplier=cfg.strategy.max_size_multiplier,
        use_volume_confirmation=cfg.strategy.use_volume_confirmation,
        volume_window=cfg.strategy.volume_window,
        regime_trend_threshold=cfg.strategy.regime_trend_threshold,
        regime_chop_threshold=cfg.strategy.regime_chop_threshold,
        signal_cooldown_bars=cfg.strategy.signal_cooldown_bars,
        score_hysteresis=cfg.strategy.score_hysteresis,
    )
    risk = BasicRiskManager(
        max_position_units=cfg.max_position_units,
        max_notional_per_order=cfg.max_notional_per_order,
        max_drawdown_pct=cfg.max_drawdown_pct,
        allow_short=cfg.allow_short,
        max_exposure_pct=cfg.max_exposure_pct,
        max_bar_range_pct=cfg.max_bar_range_pct,
        min_cash_buffer_pct=cfg.min_cash_buffer_pct,
    )
    execution = PaperExecutionHandler(fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps)
    portfolio = PortfolioManager(starting_cash=cfg.starting_cash)

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
                units=pf.position.units,
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
            symbol=cfg.symbol,
            source=source,
            strategy_mode=cfg.strategy.mode,
            run_name=args.run_name,
            config_obj=config_obj,
        )

    engine = TradingEngine(
        data_feed=data_feed,
        strategy=strategy,
        risk_manager=risk,
        execution=execution,
        portfolio=portfolio,
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
    print("Final units:", round(portfolio.position.units, 6))

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
            final_units=portfolio.position.units,
            status=status,
        )


if __name__ == "__main__":
    main()
