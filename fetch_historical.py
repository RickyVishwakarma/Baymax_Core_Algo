import os
import logging
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from trading_system.data.dhan_manager import DhanInstrumentManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def fetch_reliance_historical():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not access_token:
        logger.error("DHAN_ACCESS_TOKEN not found in .env")
        return

    mgr = DhanInstrumentManager()
    try:
        # 1. Look up RELIANCE metadata
        meta = mgr.get_instrument_metadata("NSE", "RELIANCE")
        sec_id = meta["security_id"]
        segment = meta["segment"]
        logger.info(f"Metadata found: RELIANCE -> ID: {sec_id}, Segment: {segment}")
    except Exception as e:
        logger.error(f"Failed to find RELIANCE metadata: {e}")
        return

    # 2. Prepare API Call (Intraday 1-minute chart)
    url = "https://api.dhan.co/v2/charts/intraday"
    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }
    
    # We'll fetch the last 30 days of data (Dhan limit is 90)
    # Today is April 12, 2026. Let's go back to March 1st.
    payload = {
        "securityId": sec_id,
        "exchangeSegment": segment,
        "instrument": "EQUITY",
        "interval": "1",
        "fromDate": "2026-03-01 09:15:00",
        "toDate": "2026-04-10 15:30:00" # Last trading day was likely April 10
    }
    
    logger.info(f"Fetching intraday data from {payload['fromDate']} to {payload['toDate']}...")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        if not data or "timestamp" not in data or not data["timestamp"]:
            logger.warning(f"No historical data returned. Response: {data}")
            return

        # 3. Convert to DataFrame
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(data["timestamp"], unit='s'),
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"]
        })
        
        output_file = "sample_data/RELIANCE_historical.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"SUCCESS: Saved {len(df)} bars to {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to fetch historical data: {e}")
        if 'resp' in locals():
            logger.error(f"Response: {resp.text}")

if __name__ == "__main__":
    fetch_reliance_historical()
