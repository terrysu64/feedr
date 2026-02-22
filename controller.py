"""
Controller — ties the feedr pipeline together.

Pipeline flow per execution:
  1. Load state (last run timestamp, ingested market IDs)
  2. For each enabled source: discover → ingest → write → catalog
  3. Update state
"""

import logging
import time
from typing import Dict, Tuple

from config import FeedrConfig
from interfaces import Catalog, Discoverer, Ingester, StateTracker, Writer
from sources.polymarket.ingester import PolymarketIngester

logger = logging.getLogger(__name__)


SourcePair = Tuple[Discoverer, Ingester]


class Controller:

    NO_RUN = 0

    def __init__(
        self,
        config: FeedrConfig,
        sources: Dict[str, SourcePair],
        writer: Writer,
        catalog: Catalog,
        state: StateTracker,
    ):
        self._config = config
        self._sources = sources
        self._writer = writer
        self._catalog = catalog
        self._state = state

    @property
    def since(self) -> int:
        since = self._state.last_run_timestamp()
        # On first run (since=0), use lookback_days to avoid pulling ancient markets
        if since == Controller.NO_RUN:
            lookback_seconds = self._config.discovery.lookback_days * 86400
            since = int(time.time()) - lookback_seconds
        return since

    async def _discover(self, discoverer: Discoverer, source_name: str) -> list:
        since = self.since
        logger.info("Discovering markets since %d", since)

        markets = []
        try:
            markets = await discoverer.discover(
                since=since,
                min_volume_usd=self._config.discovery.min_volume_usd,
                limit=self._config.discovery.max_markets_per_run,
            )
            logger.info("Found %d candidate markets from %s", len(markets), source_name)
        except Exception:
            logger.exception("Discovery failed for %s", source_name)

        return markets

    async def _ingest(self, ingester: Ingester, market) -> bool:
        """Ingest a single market. Returns True if successful."""

        async def fetch_trades():
            trades = []
            try:
                trades = await ingester.ingest(market)
            except Exception:
                logger.exception("Trade ingestion failed for market %s", market.market_id)
            return trades

        async def fetch_prices():
            prices = []
            if not isinstance(ingester, PolymarketIngester):
                return prices
            try:
                prices = await ingester.ingest_prices(market)
            except Exception:
                logger.exception("Price ingestion failed for market %s", market.market_id)
            return prices

        if self._state.is_ingested(market.market_id):
            logger.debug("Skipping already-ingested market %s", market.market_id)
            return False

        logger.info(
            "Ingesting: %s (vol=$%.0f)",
            market.question,
            market.volume_usd,
        )

        trades = await fetch_trades()
        prices = await fetch_prices()

        if not trades and not prices:
            logger.warning("No data found for market %s", market.market_id)

        try:
            path = self._writer.write_market(market, trades, prices)
        except Exception:
            logger.exception("Write failed for market %s, skipping", market.market_id)
            return False

        self._catalog.add_market(
            market, path, num_trades=len(trades), num_prices=len(prices)
        )
        self._state.mark_ingested(market.market_id)

        logger.info(
            "Ingested %s: %d trades, %d price points → %s",
            market.market_id,
            len(trades),
            len(prices),
            path,
        )

        # Save incrementally so we don't lose progress on crash
        self._state.save()
        self._catalog.save()
        return True

    async def run(self) -> None:
        self._state.load()
        self._catalog.load()

        total_ingested = 0

        for source_name, (discoverer, ingester) in self._sources.items():
            src_config = self._config.sources.get(source_name)
            if src_config is None or not src_config.enabled:
                logger.info("Skipping disabled source: %s", source_name)
                continue

            logger.info("Discovering markets from %s", source_name)

            markets = await self._discover(discoverer, source_name)
            for market in markets:
                if await self._ingest(ingester, market):
                    total_ingested += 1

        self._state.update_last_run()
        self._state.save()
        self._catalog.save()

        logger.info("Pipeline complete. Ingested %d new markets.", total_ingested)
