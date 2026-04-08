from trading_system.data.feed import fetch_tradingview_quote
try:
    bar = fetch_tradingview_quote(exchange='NSE', symbol='INFY', screener='india', request_timeout_seconds=5)
    print("INFY_PRICE_OUTPUT_START")
    print(f"Open: Rs {bar.open}")
    print(f"High: Rs {bar.high}")
    print(f"Low: Rs {bar.low}")
    print(f"Close: Rs {bar.close}")
    print(f"Volume: {bar.volume:,.0f}")
    print("INFY_PRICE_OUTPUT_END")
except Exception as e:
    print(f"Error: {e}")
