"""
Configuration loading for the feedr pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict

import yaml


@dataclass
class SourceConfig:
    enabled: bool = True
    rate_limit_rps: float = 5.0
    max_retries: int = 3


@dataclass
class DiscoveryConfig:
    min_volume_usd: float = 10000.0
    max_markets_per_run: int = 50
    lookback_days: int = 7


@dataclass
class FeedrConfig:
    output_dir: str = "feedr_output"
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    sources: Dict[str, SourceConfig] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str) -> "FeedrConfig":
        with open(path) as f:
            raw = yaml.safe_load(f)

        discovery_raw = raw.get("discovery", {})
        discovery = DiscoveryConfig(
            min_volume_usd=discovery_raw.get("min_volume_usd", 10000.0),
            max_markets_per_run=discovery_raw.get("max_markets_per_run", 50),
            lookback_days=discovery_raw.get("lookback_days", 7),
        )

        sources = {}
        for name, src_raw in raw.get("sources", {}).items():
            sources[name] = SourceConfig(
                enabled=src_raw.get("enabled", True),
                rate_limit_rps=src_raw.get("rate_limit_rps", 5.0),
                max_retries=src_raw.get("max_retries", 3),
            )

        return FeedrConfig(
            output_dir=raw.get("output_dir", "feedr_output"),
            discovery=discovery,
            sources=sources,
        )
