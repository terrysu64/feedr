"""JsonCatalog — maintains a manifest.json for researcher discovery."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from interfaces import Catalog
from models import Market

logger = logging.getLogger(__name__)


class JsonCatalog(Catalog):

    def __init__(self, output_dir: str):
        self._path = os.path.join(output_dir, "manifest.json")
        self._data: Dict[str, Any] = {"last_updated": None, "markets": []}

    def load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path) as f:
                self._data = json.load(f)
        else:
            self._data = {"last_updated": None, "markets": []}

    def save(self) -> None:
        self._data["last_updated"] = datetime.now(timezone.utc).isoformat()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)
            f.write("\n")

    def add_market(self, market: Market, path: str, num_trades: int, num_prices: int = 0) -> None:
        entry = {
            "source": market.source,
            "event_title": market.event.title,
            "question": market.question,
            "resolution": market.resolution,
            "volume_usd": market.volume_usd,
            "num_trades": num_trades,
            "num_prices": num_prices,
            "category": market.event.category,
            "close_timestamp": market.close_timestamp,
            "path": path,
        }
        self._data["markets"].append(entry)

    def search(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        min_volume_usd: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        results = self._data.get("markets", [])

        if source is not None:
            results = [m for m in results if m.get("source") == source]
        if category is not None:
            results = [m for m in results if m.get("category") == category]
        if min_volume_usd is not None:
            results = [m for m in results if m.get("volume_usd", 0) >= min_volume_usd]

        return results
