import time
from datetime import datetime
from trading_system.data.feed import fetch_tradingview_quote

def main():
    print("=======================================")
    print("LIVE 1-MINUTE PRICE TRACKER : HCLTECH")
    print("=======================================")
    try:
        while True:
            # 1. Fetch exact latest quote from NSE
            bar = fetch_tradingview_quote(exchange='NSE', symbol='HCLTECH', screener='india', request_timeout_seconds=5)
            
            # 2. Print beautifully to terminal
            now = datetime.now().strftime("%I:%M:%S %p")
            print(f"[{now}] HCLTECH Close: Rs {bar.close:,.2f} | Volume: {bar.volume:,.0f} | Status: Live")
            
            # 3. Sleep exact 60 seconds
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nTracker stopped by user.")
    except Exception as e:
        print(f"\nTracker Error: {e}")

if __name__ == "__main__":
    main()
