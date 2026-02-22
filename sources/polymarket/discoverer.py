"""Polymarket Discoverer — finds recently closed markets via the gamma API."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp

from interfaces import Discoverer
from models import Event, Market
from slug import slugify

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"


class PolymarketDiscoverer(Discoverer):

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
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

    async def discover(self, since: int, min_volume_usd: float, limit: int) -> List[Market]:
        session = await self._get_session()
        markets: List[Market] = []
        offset = 0
        page_size = 100
        # Cap total pages to avoid infinite loops on the API
        max_pages = 10

        for _ in range(max_pages):
            if len(markets) >= limit:
                break

            params = {
                "closed": "true",
                "limit": page_size,
                "offset": offset,
            }

            # Filter by end date if we have a since timestamp
            if since > 0:
                since_iso = datetime.fromtimestamp(since, tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                params["end_date_min"] = since_iso

            try:
                async with session.get(f"{GAMMA_API}/markets", params=params) as resp:
                    if resp.status != 200:
                        logger.error("Gamma API returned %d", resp.status)
                        break

                    data = await resp.json()
                    if not data:
                        break

                    for raw in data:
                        market = self._parse_market(raw)
                        if market is None:
                            continue
                        if market.volume_usd < min_volume_usd:
                            continue
                        # Skip markets with no outcome tokens (can't fetch price data)
                        if not market.outcome_map:
                            continue
                        markets.append(market)

                    offset += page_size

            except Exception:
                logger.exception("Error discovering Polymarket markets")
                break

        markets.sort(key=lambda m: m.volume_usd, reverse=True)
        return markets[:limit]

    def _parse_market(self, raw: dict) -> Optional[Market]:
        try:
            # Build outcome map from clobTokenIds + outcomes
            # The gamma API returns these as JSON strings
            clob_token_ids = json.loads(raw.get("clobTokenIds", "[]"))
            outcome_labels = json.loads(raw.get("outcomes", "[]"))

            outcome_map = {}
            for i, token_id in enumerate(clob_token_ids):
                label = outcome_labels[i] if i < len(outcome_labels) else f"Outcome {i}"
                outcome_map[token_id] = label

            # Also try the tokens array as fallback
            if not outcome_map:
                for token in raw.get("tokens", []):
                    token_id = token.get("token_id", "")
                    outcome = token.get("outcome", "Unknown")
                    if token_id:
                        outcome_map[token_id] = outcome
                        if outcome not in outcome_labels:
                            outcome_labels.append(outcome)

            # Build parent Event
            event_title = raw.get("groupItemTitle", "") or raw.get("question", "")
            event = Event(
                event_id=raw.get("groupItemTitle", raw.get("id", "")),
                source="polymarket",
                title=event_title,
                slug=slugify(event_title),
                category=raw.get("category", "unknown"),
            )

            end_date = raw.get("endDate", "")
            close_ts = 0
            if end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    close_ts = int(dt.timestamp())
                except ValueError:
                    pass

            creation_date = raw.get("createdAt", "")
            open_ts = 0
            if creation_date:
                try:
                    dt = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
                    open_ts = int(dt.timestamp())
                except ValueError:
                    pass

            return Market(
                market_id=raw["id"],
                event_id=event.event_id,
                source="polymarket",
                question=raw.get("question", "Unknown"),
                slug=slugify(raw.get("question", "unknown")),
                outcome_labels=outcome_labels,
                outcome_map=outcome_map,
                resolution=raw.get("outcome", ""),
                volume_usd=float(raw.get("volume", 0)),
                open_timestamp=open_ts,
                close_timestamp=close_ts,
                num_trades=0,
                event=event,
            )
        except Exception:
            logger.exception("Failed to parse market %s", raw.get("id"))
            return None
