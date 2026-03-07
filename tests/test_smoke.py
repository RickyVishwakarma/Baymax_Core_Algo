from __future__ import annotations

from trading_system.config import TradingConfig
from trading_system.data.feed import CsvMarketDataFeed
from trading_system.engine import TradingEngine
from trading_system.execution.paper import PaperExecutionHandler
from trading_system.portfolio.manager import PortfolioManager
from trading_system.risk.basic import BasicRiskManager
from trading_system.strategy.moving_average import MovingAverageCrossStrategy


def test_smoke_run() -> None:
    cfg = TradingConfig()
    feed = CsvMarketDataFeed(path="sample_data/bars.csv", symbol=cfg.symbol)
    strategy = MovingAverageCrossStrategy(
        short_window=cfg.strategy.short_window,
        long_window=cfg.strategy.long_window,
        order_size_units=cfg.strategy.order_size_units,
    )
    risk = BasicRiskManager(cfg.max_position_units, cfg.max_notional_per_order, cfg.max_drawdown_pct)
    execution = PaperExecutionHandler(cfg.fee_bps, cfg.slippage_bps)
    portfolio = PortfolioManager(cfg.starting_cash)

    engine = TradingEngine(feed, strategy, risk, execution, portfolio)
    engine.run()

    assert portfolio.state.equity > 0
