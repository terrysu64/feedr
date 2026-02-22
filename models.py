"""
Core data model for the feedr pipeline.

Hierarchy: Source → Event → Market → Trade
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Event:
    event_id: str
    source: str
    title: str
    slug: str
    category: str


@dataclass
class Market:
    market_id: str
    event_id: str
    source: str
    question: str
    slug: str
    outcome_labels: List[str]
    outcome_map: Dict[str, str]  # asset_id → outcome label
    resolution: str
    volume_usd: float
    open_timestamp: int
    close_timestamp: int
    num_trades: int
    event: Event


@dataclass
class Trade:
    trade_id: str
    market_id: str
    outcome_label: str
    side: str  # "BUY" or "SELL"
    size: float
    price: float
    fee: float
    timestamp: int


@dataclass
class PricePoint:
    """A single price observation from a timeseries."""
    market_id: str
    outcome_label: str
    price: float
    timestamp: int
