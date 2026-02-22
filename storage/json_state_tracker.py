"""JsonStateTracker — tracks pipeline state in a state.json file."""

import json
import logging
import os
import time
from typing import Any, Dict, Set

from interfaces import StateTracker

logger = logging.getLogger(__name__)


class JsonStateTracker(StateTracker):

    def __init__(self, output_dir: str):
        self._path = os.path.join(output_dir, "state.json")
        self._ingested: Set[str] = set()
        self._last_run: int = 0

    def load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path) as f:
                data = json.load(f)
            self._ingested = set(data.get("ingested_market_ids", []))
            self._last_run = data.get("last_run_timestamp", 0)
        else:
            self._ingested = set()
            self._last_run = 0

    def save(self) -> None:
        data = {
            "last_run_timestamp": self._last_run,
            "ingested_market_ids": sorted(self._ingested),
        }
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def is_ingested(self, market_id: str) -> bool:
        return market_id in self._ingested

    def mark_ingested(self, market_id: str) -> None:
        self._ingested.add(market_id)

    def last_run_timestamp(self) -> int:
        return self._last_run

    def update_last_run(self) -> None:
        self._last_run = int(time.time())
