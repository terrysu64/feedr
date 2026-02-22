# Feedr — Prediction Market Data Feeder

## Overview

Feedr is a batch pipeline that ingests trade data from prediction markets (Polymarket, Kalshi, etc.), normalizes it into a common schema, and writes it to Parquet files that researchers can load in one line of Python.

## Goals

1. **Extensible** — adding a new prediction market source = implementing one interface
2. **Researcher-friendly** — output is Parquet files with a manifest for discovery
3. **Incremental** — runs periodically, only pulls newly-closed markets since last run
4. **Config-driven** — volume thresholds, market limits, source selection all configurable

## Non-Goals (for now)

- Live/streaming data (future phase)
- Hosted service or web UI
- Order book snapshots (just trades for v1)

---

## Data Model

### Hierarchy

Prediction markets are organized as:

```
Source (e.g., Polymarket)
  └── Event (e.g., "2024 US Presidential Election")
        └── Market (e.g., "Will Trump win?")
              └── Trade (individual buy/sell)
```

### Common Schema

```
Event:
  event_id: str              # source-specific unique ID
  source: str                # "polymarket", "kalshi"
  title: str                 # human-readable event name
  slug: str                  # URL/filesystem-safe identifier
  category: str              # e.g., "politics", "sports", "crypto"
  markets: list[Market]

Market:
  market_id: str             # source-specific unique ID
  event_id: str              # parent event reference
  source: str
  question: str              # "Will Trump win the 2024 election?"
  slug: str
  outcome_labels: list[str]  # ["Yes", "No"] or multi-outcome
  resolution: str            # the winning outcome, e.g., "Yes"
  volume_usd: float
  open_timestamp: int        # unix epoch
  close_timestamp: int       # unix epoch
  num_trades: int

Trade:
  trade_id: str
  market_id: str
  outcome_label: str         # "Yes" or "No" (not raw asset_id)
  side: str                  # "BUY" or "SELL"
  size: float                # quantity
  price: float               # 0.0 to 1.0 (probability)
  fee: float                 # if available, else 0.0
  timestamp: int             # unix epoch
```

---

## Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Controller                          │
│  (reads config, coordinates pipeline, manages state)         │
└──────┬───────────────┬───────────────┬───────────────┬───────┘
       │               │               │               │
       ▼               ▼               ▼               ▼
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ Discoverer │  │  Ingester  │  │   Writer   │  │  Catalog   │
│ (abstract) │  │ (abstract) │  │ (abstract) │  │ (abstract) │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │               │
  ┌───┴───┐       ┌───┴───┐       ┌───┴───┐       ┌───┴───┐
  │Poly   │       │Poly   │       │Parquet│       │JSON   │
  │Kalshi │       │Kalshi │       │       │       │       │
  └───────┘       └───────┘       └───────┘       └───────┘
```

### Discoverer (per source)

- Input: last run timestamp, config (min volume, max markets)
- Output: list of `Market` (with parent `Event`) that closed since last run
- Polymarket impl: hits gamma-api `/markets?closed=true`
- Kalshi impl: stubbed

### Ingester (per source)

- Input: a `Market` to ingest
- Output: list of `Trade` in common schema
- Handles pagination, rate limiting, retries
- Polymarket impl: hits CLOB API `/trades`
- Kalshi impl: stubbed

### Writer (swappable backend)

- Input: `Market` metadata + list of `Trade`
- Output: files on disk
- v1 impl: `ParquetWriter` — writes to local filesystem
- Interface exists so we can swap to S3 later without changing pipeline code

### Catalog (swappable backend)

- Maintains a manifest of all ingested markets for researcher discovery
- Provides search/filter (by source, category, volume, date range)
- v1 impl: `JsonCatalog` — reads/writes a `manifest.json` file
- Interface exists so we can swap to SQLite or a database later

### StateTracker (swappable backend)

- Tracks which markets have been ingested and when
- Prevents duplicate ingestion across runs
- v1 impl: `JsonStateTracker` — reads/writes a `state.json` file

---

## Output Directory Structure

```
feedr_output/
  manifest.json                             # catalog for researcher discovery
  state.json                                # pipeline state (last run, ingested IDs)
  polymarket/
    {event_slug}/
      {market_slug}/
        metadata.json                       # Market schema as JSON
        trades.parquet                      # all trades, sorted by timestamp
  kalshi/
    {event_slug}/
      {market_slug}/
        metadata.json
        trades.parquet
```

### Manifest Format (manifest.json)

```json
{
  "last_updated": "2026-02-16T00:00:00Z",
  "markets": [
    {
      "source": "polymarket",
      "event_title": "2024 US Presidential Election",
      "question": "Will Trump win?",
      "resolution": "Yes",
      "volume_usd": 1500000.0,
      "num_trades": 45023,
      "category": "politics",
      "close_timestamp": 1730000000,
      "path": "polymarket/2024-us-presidential-election/will-trump-win"
    }
  ]
}
```

### Researcher Usage

```python
import polars as pl

# Load a single market
trades = pl.read_parquet("feedr_output/polymarket/2024-us-presidential-election/will-trump-win/trades.parquet")

# Discover available markets
import json
manifest = json.load(open("feedr_output/manifest.json"))
high_vol = [m for m in manifest["markets"] if m["volume_usd"] > 100_000]
```

---

## Configuration

```yaml
# feedr_config.yaml
output_dir: "feedr_output"

# Pipeline settings
discovery:
  min_volume_usd: 10000        # ignore low-activity markets
  max_markets_per_run: 50      # cap per execution
  lookback_days: 7             # how far back to look for newly closed markets

# Source-specific settings
sources:
  polymarket:
    enabled: true
    rate_limit_rps: 5          # requests per second
    max_retries: 3
  kalshi:
    enabled: false             # stubbed for now
```

---

## Interfaces (Python)

```python
# --- Core Data Classes ---

@dataclass
class Event:
    event_id: str
    source: str
    title: str
    slug: str
    category: str

@dataclass
class Market:
    market_id: str
    event_id: str
    source: str
    question: str
    slug: str
    outcome_labels: list[str]
    resolution: str
    volume_usd: float
    open_timestamp: int
    close_timestamp: int
    num_trades: int
    event: Event                # parent reference

@dataclass
class Trade:
    trade_id: str
    market_id: str
    outcome_label: str
    side: str
    size: float
    price: float
    fee: float
    timestamp: int

# --- Abstract Interfaces ---

class Discoverer(ABC):
    async def discover(self, config: DiscoveryConfig, since: int) -> list[Market]:
        """Find markets closed since `since` timestamp."""

class Ingester(ABC):
    async def ingest(self, market: Market) -> list[Trade]:
        """Fetch all trades for a market."""

class Writer(ABC):
    def write_market(self, market: Market, trades: list[Trade]) -> str:
        """Write market data. Returns the output path."""

class Catalog(ABC):
    def add_market(self, market: Market, path: str) -> None:
        """Add a market entry to the catalog."""
    def search(self, **filters) -> list[dict]:
        """Search the catalog."""

class StateTracker(ABC):
    def is_ingested(self, market_id: str) -> bool:
    def mark_ingested(self, market_id: str) -> None:
    def last_run_timestamp(self) -> int:
    def update_last_run(self) -> None:
```

---

## Pipeline Flow (one execution)

```
1. Load config
2. Load state (last run timestamp, ingested market IDs)
3. For each enabled source:
   a. Discoverer.discover(config, since=last_run_timestamp)
      → list of Markets (filtered by volume, capped by max_markets_per_run)
   b. For each market (skip if already ingested):
      i.   Ingester.ingest(market) → list of Trades
      ii.  Writer.write_market(market, trades) → path
      iii. Catalog.add_market(market, path)
      iv.  StateTracker.mark_ingested(market.market_id)
4. StateTracker.update_last_run()
5. Done.
```

---

## POC Scope (what to build first)

### Phase 1: Core pipeline + Polymarket (demo-ready)
- [ ] Data model (Event, Market, Trade dataclasses)
- [ ] Abstract interfaces (Discoverer, Ingester, Writer, Catalog, StateTracker)
- [ ] Polymarket Discoverer (closed markets, sorted by volume)
- [ ] Polymarket Ingester (paginated trade fetch with rate limiting)
- [ ] ParquetWriter (local disk)
- [ ] JsonCatalog (manifest.json)
- [ ] JsonStateTracker (state.json)
- [ ] Controller (ties it all together)
- [ ] Config loading (YAML)
- [ ] Bazel BUILD targets
- [ ] Run on ~50 markets, produce real output

### Phase 2: Demo notebook
- [ ] Load trades from parquet, plot price timeseries
- [ ] Show manifest-based discovery
- [ ] Simple analysis: convergence speed to resolution outcome

### Phase 3: Extensibility proof
- [ ] Kalshi source (stubbed Discoverer + Ingester with NotImplementedError)
- [ ] Show that adding a source is just two classes

### Future (not now)
- [ ] Live market streaming
- [ ] S3 writer backend
- [ ] SQLite state tracker
- [ ] Richer data: order book snapshots, market depth
