import os
import requests
from dotenv import load_dotenv

load_dotenv()

def diagnose():
    token = os.getenv("DHAN_ACCESS_TOKEN")
    client_id = os.getenv("DHAN_CLIENT_ID")
    url = "https://api.dhan.co/v2/orders"
    
    variations = [
        {"access-token": token},
        {"access-token": token, "client-id": client_id},
        {"access-token": token, "dhan-client-id": client_id},
        {"access-token": token, "dhanClientId": client_id},
        {"access-token": token, "Content-Type": "application/json"},
        {"access-token": token, "client-id": client_id, "Accept": "application/json"}
    ]
    
    for i, headers in enumerate(variations):
        print(f"\n--- Strategy {i+1}: Headers {list(headers.keys())} ---")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {resp.status_code}")
            print(f"Body:   {resp.text}")
        except Exception as e:
            print(f"Error:  {e}")

if __name__ == "__main__":
    diagnose()
