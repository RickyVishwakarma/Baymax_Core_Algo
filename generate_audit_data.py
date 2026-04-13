import csv
import math
import random
from datetime import datetime, timedelta

def generate_audit_data(filename, n_bars=500):
    start_ts = datetime(2026, 1, 1, 9, 15)
    data = []
    price = 2500.0
    
    for i in range(n_bars):
        ts = start_ts + timedelta(minutes=i)
        
        # Volatility regime shift every 100 bars
        vol = 5.0 if (i // 100) % 2 == 0 else 1.0 # High vol (Trend) vs Low vol (Choppy)
        
        change = random.gauss(0.1, vol) if (i // 100) % 2 == 0 else random.gauss(0, 0.5)
        price += change
        
        high = price + abs(random.gauss(2, 1))
        low = price - abs(random.gauss(2, 1))
        open_px = price - random.gauss(0.5, 0.5)
        close_px = price
        volume = random.randint(1000, 5000)
        
        data.append({
            "timestamp": ts.isoformat(),
            "open": round(open_px, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close_px, 2),
            "volume": volume
        })
        
    with open(filename, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(data)
    print(f"Generated {n_bars} bars in {filename}")

if __name__ == "__main__":
    generate_audit_data("sample_data/audit_data.csv")
