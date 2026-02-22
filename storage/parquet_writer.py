"""ParquetWriter — writes market data to local disk as Parquet + JSON."""

import json
import logging
import os
from typing import List

import pyarrow as pa
import pyarrow.parquet as pq

from interfaces import Writer
from models import Market, PricePoint, Trade

logger = logging.getLogger(__name__)

TRADE_SCHEMA = pa.schema([
    ("trade_id", pa.string()),
    ("market_id", pa.string()),
    ("outcome_label", pa.string()),
    ("side", pa.string()),
    ("size", pa.float64()),
    ("price", pa.float64()),
    ("fee", pa.float64()),
    ("timestamp", pa.int64()),
])

PRICE_SCHEMA = pa.schema([
    ("market_id", pa.string()),
    ("outcome_label", pa.string()),
    ("price", pa.float64()),
    ("timestamp", pa.int64()),
])


class ParquetWriter(Writer):

    def __init__(self, output_dir: str):
        self._output_dir = output_dir

    def write_market(
        self,
        market: Market,
        trades: List[Trade],
        prices: List[PricePoint],
    ) -> str:
        rel_path = os.path.join(
            market.source,
            market.event.slug,
            market.slug,
        )
        abs_path = os.path.join(self._output_dir, rel_path)
        os.makedirs(abs_path, exist_ok=True)

        if trades:
            self._write_trades_parquet(abs_path, trades)
        if prices:
            self._write_prices_parquet(abs_path, prices)
        self._write_metadata_json(abs_path, market, len(trades), len(prices))

        logger.info(
            "Wrote %d trades, %d prices to %s",
            len(trades),
            len(prices),
            rel_path,
        )
        return rel_path

    def _write_trades_parquet(self, dir_path: str, trades: List[Trade]) -> None:
        arrays = {
            "trade_id": [t.trade_id for t in trades],
            "market_id": [t.market_id for t in trades],
            "outcome_label": [t.outcome_label for t in trades],
            "side": [t.side for t in trades],
            "size": [t.size for t in trades],
            "price": [t.price for t in trades],
            "fee": [t.fee for t in trades],
            "timestamp": [t.timestamp for t in trades],
        }
        table = pa.table(arrays, schema=TRADE_SCHEMA)
        pq.write_table(table, os.path.join(dir_path, "trades.parquet"))

    def _write_prices_parquet(self, dir_path: str, prices: List[PricePoint]) -> None:
        arrays = {
            "market_id": [p.market_id for p in prices],
            "outcome_label": [p.outcome_label for p in prices],
            "price": [p.price for p in prices],
            "timestamp": [p.timestamp for p in prices],
        }
        table = pa.table(arrays, schema=PRICE_SCHEMA)
        pq.write_table(table, os.path.join(dir_path, "prices.parquet"))

    def _write_metadata_json(
        self, dir_path: str, market: Market, num_trades: int, num_prices: int
    ) -> None:
        metadata = {
            "market_id": market.market_id,
            "event_id": market.event_id,
            "source": market.source,
            "question": market.question,
            "slug": market.slug,
            "outcome_labels": market.outcome_labels,
            "resolution": market.resolution,
            "volume_usd": market.volume_usd,
            "open_timestamp": market.open_timestamp,
            "close_timestamp": market.close_timestamp,
            "num_trades": num_trades,
            "num_prices": num_prices,
            "event": {
                "event_id": market.event.event_id,
                "title": market.event.title,
                "slug": market.event.slug,
                "category": market.event.category,
            },
        }

        path = os.path.join(dir_path, "metadata.json")
        with open(path, "w") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")
