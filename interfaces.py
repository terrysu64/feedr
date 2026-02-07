"""
Base interfaces for extensible prediction market data collection.
Following the open-closed principle for easy extension.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class MarketMetadata:
    question: str
    market_id: str
    volume_usd: float

    def __repr__(self):
        return (
            f"{self.question}\n"
            f"💰 Volume: ${self.volume_usd:,.0f}\n"
            f"🔑 ID: {self.market_id}\n"
        )

class DataSource(ABC):
    """Abstract base class for prediction market data sources"""
    
    @abstractmethod
    async def discover_hot_markets(self, limit: int = 10) -> List[MarketMetadata]:
        """
        Discover currently hot/active markets.
        
        Args:
            limit: Maximum number of markets to return
            
        Returns:
            List of market metadata sorted by relevance/volume
        """
        pass

