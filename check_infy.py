from trading_system.data.feed import fetch_tradingview_quotes
try:
    bars = fetch_tradingview_quotes(exchange='NSE', symbols=['INFY'], screener='india', request_timeout_seconds=5)
    if not bars:
        print("Error: No data returned")
        exit(1)
    bar = bars[0]
    print("INFY_PRICE_OUTPUT_START")
    print(f"Open: Rs {bar.open}")
    print(f"High: Rs {bar.high}")
    print(f"Low: Rs {bar.low}")
    print(f"Close: Rs {bar.close}")
    print(f"Volume: {bar.volume:,.0f}")
    print("INFY_PRICE_OUTPUT_END")
except Exception as e:
    print(f"Error: {e}")
