import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_balance():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not client_id or not access_token:
        print("ERROR: Dhan credentials not found in .env")
        return

    url = "https://api.dhan.co/fundlimit"
    headers = {
        "access-token": access_token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Dhan fundlimit response usually contains:
        # { "dhanClientId": "...", "availabelBalance": 100.25, "sodLimit": 100.25, ... }
        balance = data.get("availabelBalance", 0.0) # Note the typo 'availabel' in Dhan docs
        if "availabelBalance" not in data and "availableBalance" in data:
             balance = data.get("availableBalance")
             
        print("\n" + "="*40)
        print(" DHAN ACCOUNT BALANCE")
        print("="*40)
        print(f"Client ID:    {client_id}")
        print(f"Available:    Rs {balance:,.2f}")
        print(f"Full Data:    {data}")
        print("="*40)
        
    except Exception as e:
        print(f"FAILED to fetch balance: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")

if __name__ == "__main__":
    check_balance()
