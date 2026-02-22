"""
Abstract interfaces for the feedr pipeline.

Each interface has a swappable backend:
  - Discoverer/Ingester: one impl per prediction market source
  - Writer: ParquetWriter (local disk) now, S3 later
  - Catalog: JsonCatalog now, SQLite later
  - StateTracker: JsonStateTracker now, SQLite later
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from models import Market, PricePoint, Trade


class Discoverer(ABC):
    """Finds newly-closed markets from a prediction market source."""

    @abstractmethod
    async def discover(self, since: int, min_volume_usd: float, limit: int) -> List[Market]:
        """
        Find markets that closed since the given timestamp.

        Args:
            since: unix epoch — only return markets closed after this time
            min_volume_usd: minimum trading volume to include
            limit: max number of markets to return

        Returns:
            List of Markets with their parent Event populated
        """


class Ingester(ABC):
    """Fetches all trades for a given market."""

    @abstractmethod
    async def ingest(self, market: Market) -> List[Trade]:
        """
        Fetch all trades for a market.

        Args:
            market: the Market to ingest trades for

        Returns:
            List of Trades in common schema, sorted by timestamp
        """


class Writer(ABC):
    """Writes market data to storage."""

    @abstractmethod
    def write_market(
        self,
        market: Market,
        trades: List[Trade],
        prices: List[PricePoint],
    ) -> str:
        """
        Write market metadata, trades, and price history to storage.

        Args:
            market: Market metadata
            trades: list of trades sorted by timestamp (may be empty)
            prices: list of price observations sorted by timestamp (may be empty)

        Returns:
            Relative path to the written market directory
        """


class Catalog(ABC):
    """Maintains a searchable index of ingested markets."""

    @abstractmethod
    def add_market(self, market: Market, path: str, num_trades: int, num_prices: int = 0) -> None:
        """Add a market entry to the catalog."""

    @abstractmethod
    def search(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        min_volume_usd: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search the catalog with optional filters."""

    @abstractmethod
    def load(self) -> None:
        """Load catalog from storage."""

    @abstractmethod
    def save(self) -> None:
        """Persist catalog to storage."""


class StateTracker(ABC):
    """Tracks pipeline state to enable incremental ingestion."""

    @abstractmethod
    def is_ingested(self, market_id: str) -> bool:
        """Check if a market has already been ingested."""

    @abstractmethod
    def mark_ingested(self, market_id: str) -> None:
        """Record that a market has been ingested."""

    @abstractmethod
    def last_run_timestamp(self) -> int:
        """Return the timestamp of the last successful pipeline run. 0 if never run."""

    @abstractmethod
    def update_last_run(self) -> None:
        """Update the last run timestamp to now."""

    @abstractmethod
    def load(self) -> None:
        """Load state from storage."""

    @abstractmethod
    def save(self) -> None:
        """Persist state to storage."""
