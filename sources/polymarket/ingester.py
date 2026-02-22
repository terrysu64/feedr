"""
Polymarket Ingester — fetches price history for a market via the CLOB API.

Uses the public /prices-history endpoint (no auth required) to get
timestamped price observations for each outcome token.
"""

import asyncio
import json
import logging
from typing import List, Optional

import aiohttp

from interfaces import Ingester
from models import Market, PricePoint, Trade
from sources.polymarket.endpoints import CLOB_API

logger = logging.getLogger(__name__)

class PolymarketIngester(Ingester):

    def __init__(
        self,
        rate_limit_rps: float = 5.0,
        max_retries: int = 3,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self._rate_limit_delay = 1.0 / rate_limit_rps
        self._max_retries = max_retries
        self._session = session
        self._owned_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._owned_session and self._session:
            await self._session.close()
            self._session = None

    async def ingest(self, market: Market) -> List[Trade]:
        # Trade-level data requires L2 auth which we don't have yet.
        return []

    async def ingest_prices(self, market: Market) -> List[PricePoint]:
        """Fetch price history for all outcome tokens of a market."""
        session = await self._get_session()
        all_points: List[PricePoint] = []

        for token_id, outcome_label in market.outcome_map.items():
            points = await self._fetch_price_history(
                session, token_id, outcome_label, market.market_id
            )
            all_points.extend(points)
            await asyncio.sleep(self._rate_limit_delay)

        all_points.sort(key=lambda p: (p.timestamp, p.outcome_label))
        return all_points

    async def _fetch_price_history(
        self,
        session: aiohttp.ClientSession,
        token_id: str,
        outcome_label: str,
        market_id: str,
    ) -> List[PricePoint]:
        """Fetch price history for a single outcome token."""
        params = {
            "market": token_id,
            "interval": "max",
            "fidelity": "1440",  # daily resolution
        }

        for attempt in range(self._max_retries):
            try:
                async with session.get(
                    f"{CLOB_API}/prices-history", params=params
                ) as resp:
                    if resp.status == 429:
                        wait = 2 ** attempt
                        logger.warning("Rate limited, waiting %ds", wait)
                        await asyncio.sleep(wait)
                        continue

                    if resp.status != 200:
                        logger.error(
                            "prices-history returned %d for token %s",
                            resp.status,
                            token_id[:20],
                        )
                        return []

                    data = json.loads(await resp.text())
                    history = data.get("history", [])

                    return [
                        PricePoint(
                            market_id=market_id,
                            outcome_label=outcome_label,
                            price=float(point["p"]),
                            timestamp=int(point["t"]),
                        )
                        for point in history
                    ]

            except aiohttp.ClientError:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.exception("Failed after %d retries", self._max_retries)
                    return []

        return []
