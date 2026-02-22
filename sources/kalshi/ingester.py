"""Kalshi Ingester — stubbed for future implementation."""

from typing import List

from interfaces import Ingester
from models import Market, Trade


class KalshiIngester(Ingester):

    async def ingest(self, market: Market) -> List[Trade]:
        raise NotImplementedError("Kalshi ingester not yet implemented")
