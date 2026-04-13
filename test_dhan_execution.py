import os
import logging
import uuid
import requests
from dotenv import load_dotenv
from trading_system.data.dhan_manager import DhanInstrumentManager
from trading_system.models import Order, Side, MarketBar
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def test_handler_mapping():
    print("--- Testing Dhan Execution Mapping ---")
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not (client_id and access_token):
        print("Error: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be in .env")
        return

    mgr = DhanInstrumentManager()
    
    # Test mapping for TCS
    try:
        meta = mgr.get_instrument_metadata("NSE", "TCS")
        print(f"SUCCESS: TCS Mapping -> ID: {meta['security_id']}, Segment: {meta['segment']}")
    except Exception as e:
        print(f"FAILED: TCS Mapping: {e}")

def test_api_connectivity():
    print("\n--- Testing Dhan API Connectivity (Order List) ---")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    client_id = os.getenv("DHAN_CLIENT_ID")
    
    url = "https://api.dhan.co/v2/orders"
    # Some Dhan v2 endpoints require client-id in headers
    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if not resp.ok:
            print(f"FAILED: API Status {resp.status_code}")
            print(f"Error Body: {resp.text}")
            return
            
        orders = resp.json()
        print(f"SUCCESS: Connected to Dhan API. Found {len(orders)} recent orders.")
    except Exception as e:
        print(f"FAILED: Connection Error: {e}")

if __name__ == "__main__":
    test_handler_mapping()
    test_api_connectivity()
