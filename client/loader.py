"""
Feedr client — helpers for loading and exploring pipeline output.

Usage:
    from client.loader import FeedrClient

    client = FeedrClient("/tmp/feedr_output")
    markets = client.search(min_volume_usd=100_000)
    df = client.load_prices(markets[0]["path"])
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pprint import pprint

import pandas as pd
import pyarrow.parquet as pq


class FeedrClient:
    """Read-only client for exploring feedr pipeline output."""

    def __init__(self, output_dir: str):
        self._output_dir = output_dir
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        path = os.path.join(self._output_dir, "manifest.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No manifest.json found at {path}. Run the pipeline first.")
        with open(path) as f:
            return json.load(f)

    @property
    def markets(self) -> List[Dict[str, Any]]:
        """All markets in the catalog."""
        return self._manifest.get("markets", [])

    @property
    def last_updated(self) -> str:
        return self._manifest.get("last_updated", "unknown")

    def search(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        min_volume_usd: Optional[float] = None,
        question_contains: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter markets from the manifest."""
        results = self.markets

        if source is not None:
            results = [m for m in results if m.get("source") == source]
        if category is not None:
            results = [m for m in results if m.get("category") == category]
        if min_volume_usd is not None:
            results = [m for m in results if m.get("volume_usd", 0) >= min_volume_usd]
        if question_contains is not None:
            q = question_contains.lower()
            results = [m for m in results if q in m.get("question", "").lower()]

        return sorted(results, key=lambda m: m.get("volume_usd", 0), reverse=True)

    def load_prices(self, market_path: str) -> pd.DataFrame:
        """Load price history for a market into a DataFrame."""
        parquet_path = os.path.join(self._output_dir, market_path, "prices.parquet")
        if not os.path.exists(parquet_path):
            raise FileNotFoundError(f"No prices.parquet at {parquet_path}")

        df = pq.read_table(parquet_path).to_pandas()
        df["date"] = pd.to_datetime(df["timestamp"], unit="s")
        return df.sort_values("timestamp")

    def load_metadata(self, market_path: str) -> Dict[str, Any]:
        """Load metadata.json for a market."""
        meta_path = os.path.join(self._output_dir, market_path, "metadata.json")
        with open(meta_path) as f:
            return json.load(f)

    def summary(self) -> pd.DataFrame:
        """Return a DataFrame summarizing all markets in the catalog."""
        if not self.markets:
            return pd.DataFrame()

        rows = []
        for m in self.markets:
            close_ts = m.get("close_timestamp", 0)
            close_date = (
                datetime.fromtimestamp(close_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                if close_ts
                else "unknown"
            )
            rows.append({
                "question": m.get("question", ""),
                "source": m.get("source", ""),
                "volume_usd": m.get("volume_usd", 0),
                "num_prices": m.get("num_prices", 0),
                "resolution": m.get("resolution", ""),
                "category": m.get("category", ""),
                "close_date": close_date,
                "path": m.get("path", ""),
            })

        df = pd.DataFrame(rows)
        return df.sort_values("volume_usd", ascending=False).reset_index(drop=True)

if __name__ == "__main__":
    client = FeedrClient("feedr_output")
    markets = client.search(min_volume_usd=100_000)
    df = client.load_prices(markets[0]["path"])

    client = FeedrClient("feedr_output")

    print("=== All markets matching min volume 100_000 USD ===")
    markets = client.search(min_volume_usd=100_000)
    pprint(markets)

    if markets:
        print("\n=== First market price history ===")
        df = client.load_prices(markets[0]["path"])
        print(df.head())