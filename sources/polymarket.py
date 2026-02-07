import aiohttp
import asyncio
from typing import List, Optional
from interfaces import (
    DataSource, MarketMetadata, 
)

class PolymarketSource(DataSource):
    BASE_URL = "https://gamma-api.polymarket.com"
    CLOB_API = "https://clob.polymarket.com"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._owned_session = session is None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._owned_session and self._session:
            await self._session.close()
    
    async def discover_hot_markets(self, limit: int = 10) -> List[MarketMetadata]:
        session = await self._get_session()
        
        try:
            async with session.get(
                f"{self.BASE_URL}/markets",
                params={
                    "closed": "true",
                    "limit": limit * 2,  
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"API error: {response.status}")
                
                data = await response.json()
                markets = []
                
                for market in data[:limit]:
                    try:
                        metadata = self._parse_market_metadata(market)
                        markets.append(metadata)
                    except Exception as e:
                        print(f"Error parsing market {market.get('id')}: {e}")
                        continue
                
                markets.sort(key=lambda m: m.volume_usd, reverse=True)
                return markets[:limit]
                
        except Exception as e:
            print(f"Error fetching hot markets: {e}")
            return []
    
    def _parse_market_metadata(self, market_data: dict) -> MarketMetadata:
        return MarketMetadata(
            market_id=market_data["id"],
            question=market_data.get("question", "Unknown"),
            volume_usd=float(market_data["volume"])
        )
    
async def demo():
    source = PolymarketSource()
    
    try:
        print("Discovering hot markets on Polymarket...\n")
        markets = await source.discover_hot_markets(limit=5)
        for i, market in enumerate(markets, 1):
            print(f"{i}. {market.question}")
            print(f"   ID: {market.market_id}")
            print()
            
    finally:
        await source.close()

if __name__ == "__main__":
    asyncio.run(demo())
