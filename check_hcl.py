import time
from trading_system.data.feed import fetch_tradingview_quotes

def main():
    try:
        bars = fetch_tradingview_quotes(exchange='NSE', symbols=['HCLTECH'], screener='india', request_timeout_seconds=5)
        if not bars:
            print("Error: No data returned")
            return
        bar = bars[0]
        print("HCLTECH LIVE DATA:")
        print(f"Symbol: {bar.symbol}")
        print(f"Timestamp: {bar.ts}")
        print(f"Open: Rs {bar.open}")
        print(f"High: Rs {bar.high}")
        print(f"Low: Rs {bar.low}")
        print(f"Close: Rs {bar.close}")
        print(f"Volume: {bar.volume:,.0f}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
