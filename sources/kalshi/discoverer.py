"""Kalshi Discoverer — stubbed for future implementation."""

from typing import List

from interfaces import Discoverer
from models import Market


class KalshiDiscoverer(Discoverer):

    async def discover(self, since: int, min_volume_usd: float, limit: int) -> List[Market]:
        raise NotImplementedError("Kalshi discoverer not yet implemented")
