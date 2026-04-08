from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(slots=True)
class MarketBar:
    ts: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class Signal:
    symbol: str
    side: Side
    size: float
    reason: str
    score: float = 0.0
    confidence: float = 0.0
    regime: str = "unknown"


@dataclass(slots=True)
class Order:
    symbol: str
    side: Side
    size: float


@dataclass(slots=True)
class Fill:
    symbol: str
    side: Side
    size: float
    fill_price: float
    fee_paid: float


@dataclass(slots=True)
class Position:
    symbol: str
    units: float = 0.0
    avg_entry_price: float = 0.0
    peak_price: float = 0.0


@dataclass(slots=True)
class PortfolioState:
    cash: float
    equity: float
    peak_equity: float
