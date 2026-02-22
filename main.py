"""
Feedr — prediction market data feeder.

Usage:
    bazel run //experimental/terry-su_data/feedr:feedr -- --config feedr_config.yaml
"""

import argparse
import asyncio
import logging
import os
import sys

from config import FeedrConfig
from controller import Controller
from sources.polymarket.discoverer import PolymarketDiscoverer
from sources.polymarket.ingester import PolymarketIngester
from storage.json_catalog import JsonCatalog
from storage.json_state_tracker import JsonStateTracker
from storage.parquet_writer import ParquetWriter


def build_sources(config: FeedrConfig):
    """Construct source pairs for each enabled source."""
    sources = {}

    poly_cfg = config.sources.get("polymarket")
    if poly_cfg and poly_cfg.enabled:
        sources["polymarket"] = (
            PolymarketDiscoverer(),
            PolymarketIngester(
                rate_limit_rps=poly_cfg.rate_limit_rps,
                max_retries=poly_cfg.max_retries,
            ),
        )

    return sources


async def run(config: FeedrConfig) -> None:
    sources = build_sources(config)

    writer = ParquetWriter(config.output_dir)
    catalog = JsonCatalog(config.output_dir)
    state = JsonStateTracker(config.output_dir)

    controller = Controller(
        config=config,
        sources=sources,
        writer=writer,
        catalog=catalog,
        state=state,
    )

    try:
        await controller.run()
    finally:
        for discoverer, ingester in sources.values():
            await discoverer.close()
            await ingester.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Feedr — prediction market data feeder")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "feedr_config.yaml"),
        help="Path to config YAML file",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory from config",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = FeedrConfig.from_yaml(args.config)
    if args.output_dir:
        config.output_dir = args.output_dir

    asyncio.run(run(config))


if __name__ == "__main__":
    main()
