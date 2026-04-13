import asyncio
import os
import logging
import websockets
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

async def test_dhan_ws():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    # URL format from Dhan docs
    url = f"wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType=2"
    
    logger.info(f"Connecting to: {url.split('token=')[0]}token=REDACTED...")
    
    try:
        async with websockets.connect(url) as ws:
            logger.info("Handshake Successful!")
            # Wait for a potential message from server or just a few seconds
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                logger.info(f"Received message: {msg}")
            except asyncio.TimeoutError:
                logger.info("No message received within 5s, but connection is OPEN.")
    except Exception as e:
        logger.error(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_dhan_ws())
