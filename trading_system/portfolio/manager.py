from __future__ import annotations

from trading_system.models import Fill, MarketBar, PortfolioState, Position, Side


class PortfolioManager:
    def __init__(self, starting_cash: float):
        self.state = PortfolioState(cash=starting_cash, equity=starting_cash, peak_equity=starting_cash)
        self.position = Position(symbol="", units=0.0, avg_entry_price=0.0)

    def mark_to_market(self, bar: MarketBar) -> None:
        if not self.position.symbol:
            self.position.symbol = bar.symbol
        pos_value = self.position.units * bar.close
        self.state.equity = self.state.cash + pos_value
        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity

    def apply_fill(self, fill: Fill) -> None:
        signed_units = fill.size if fill.side == Side.BUY else -fill.size
        cash_change = -(signed_units * fill.fill_price) - fill.fee_paid
        self.state.cash += cash_change

        prior_units = self.position.units
        next_units = prior_units + signed_units
        self.position.symbol = fill.symbol

        if prior_units == 0 or (prior_units > 0) == (signed_units > 0):
            gross_cost = (abs(prior_units) * self.position.avg_entry_price) + (abs(signed_units) * fill.fill_price)
            self.position.units = next_units
            if next_units != 0:
                self.position.avg_entry_price = gross_cost / abs(next_units)
            else:
                self.position.avg_entry_price = 0.0
        else:
            self.position.units = next_units
            if next_units == 0:
                self.position.avg_entry_price = 0.0
            elif (prior_units > 0) != (next_units > 0):
                self.position.avg_entry_price = fill.fill_price
