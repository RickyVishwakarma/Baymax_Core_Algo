import os
import asyncio
from dotenv import load_dotenv
from dhanhq.marketfeed import DhanFeed

load_dotenv()

client_id = os.environ.get("DHAN_CLIENT_ID")
access_token = os.environ.get("DHAN_ACCESS_TOKEN")

# (Exchange, SecurityId, RequestCode)
# 1 = NSE, 2885 = RELIANCE, 17 = Quote
instruments = [(1, "2885", 17)] 

def on_connect():
    print("DhanHQ Official Library Connected.")

def on_tick(message):
    print("TICK:", message)

async def test_official_dhan():
    print("Testing official DhanHQ WebSocket v2...")
    feed = DhanFeed(
        client_id=client_id,
        access_token=access_token,
        instruments=instruments,
        version='v2'
    )
    
    # Run the loop manually to see what happens
    await feed.connect()
    try:
        while True:
            data = await feed.get_instrument_data()
            print("Received:", data)
    except Exception as e:
        print("Disconnected or error:", e)

if __name__ == "__main__":
    asyncio.run(test_official_dhan())
