from __future__ import annotations

from trading_system.models import Fill, MarketBar, PortfolioState, Position, Side


class PortfolioManager:
    def __init__(self, starting_cash: float):
        self.state = PortfolioState(cash=starting_cash, equity=starting_cash, peak_equity=starting_cash)
        self.positions: dict[str, Position] = {}
        self.current_prices: dict[str, float] = {}

    def get_position(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, units=0.0, avg_entry_price=0.0)
        return self.positions[symbol]

    def mark_to_market(self, bar: MarketBar) -> None:
        self.current_prices[bar.symbol] = bar.close
        
        pos_value = 0.0
        for sym, pos in self.positions.items():
            if sym == bar.symbol:
                if pos.units > 0:
                    pos.peak_price = max(pos.peak_price, bar.high)
                elif pos.units < 0:
                    pos.peak_price = min(pos.peak_price, bar.low)
                    
            price = self.current_prices.get(sym, 0.0)
            pos_value += pos.units * price
            
        self.state.equity = self.state.cash + pos_value
        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity

    def apply_fill(self, fill: Fill, ts: datetime) -> None:
        signed_units = fill.size if fill.side == Side.BUY else -fill.size
        cash_change = -(signed_units * fill.fill_price) - fill.fee_paid
        self.state.cash += cash_change

        position = self.get_position(fill.symbol)
        prior_units = position.units
        next_units = prior_units + signed_units

        if prior_units == 0 or (prior_units > 0) == (signed_units > 0):
            gross_cost = (abs(prior_units) * position.avg_entry_price) + (abs(signed_units) * fill.fill_price)
            position.units = next_units
            if next_units != 0:
                position.avg_entry_price = gross_cost / abs(next_units)
                if prior_units == 0:
                    position.peak_price = fill.fill_price
                    position.entry_time = ts
            else:
                position.avg_entry_price = 0.0
                position.peak_price = 0.0
                position.entry_time = None
                position.last_velocity = 0.0
        else:
            position.units = next_units
            if next_units == 0:
                position.avg_entry_price = 0.0
                position.peak_price = 0.0
                position.entry_time = None
                position.last_velocity = 0.0
            elif (prior_units > 0) != (next_units > 0):
                position.avg_entry_price = fill.fill_price
                position.peak_price = fill.fill_price
                position.entry_time = ts
