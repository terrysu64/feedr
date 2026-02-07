import asyncio
from sources.polymarket import PolymarketSource
import traceback

async def run():
    
    source = PolymarketSource()
    
    try:
        markets = await source.discover_hot_markets(limit=2)
        
        if not markets:
            print("No markets found!")
            return
        
        print(f"Found {len(markets)} hot markets:\n")
        for i, market in enumerate(markets, 1):
           print(f"{i}.")
           print(repr(market)) 
       
    except: 
        traceback.print_exc()
    
    finally:
        await source.close()

if __name__ == "__main__":
    asyncio.run(run())
