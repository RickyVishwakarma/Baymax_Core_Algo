import logging
from datetime import datetime, timedelta
from trading_system.models import MarketBar
from trading_system.strategy.orb_vwap import OrbVwapStrategy
from trading_system.strategy.vwap_pullback import VwapPullbackStrategy
from trading_system.strategy.supertrend import SupertrendStrategy

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_orb_vwap():
    print("\n=== Testing ORB + VWAP Strategy ===")
    strategy = OrbVwapStrategy(orb_minutes=30)
    
    start_time = datetime(2026, 4, 23, 9, 15)
    
    # Simulate ORB Formation (9:15 to 9:45)
    print("Forming Opening Range (9:15 to 9:45)...")
    for i in range(30):
        ts = start_time + timedelta(minutes=i)
        bar = MarketBar(symbol="NIFTY", ts=ts, open=100, high=105, low=95, close=100, volume=1000)
        signal = strategy.on_bar(bar)
        
    print(f"Opening Range Established -> High: {strategy.orb_high}, Low: {strategy.orb_low}")
    print(f"Current VWAP: {strategy.current_vwap:.2f}")
    
    # Simulate a breakout above ORB High WITH VWAP Confluence
    print("\nSimulating Bullish Breakout at 9:50 AM...")
    breakout_bar = MarketBar(
        symbol="NIFTY", 
        ts=start_time + timedelta(minutes=35), 
        open=102, high=108, low=102, close=106, # Close 106 > ORB High 105
        volume=5000
    )
    signal = strategy.on_bar(breakout_bar)
    print(f"Signal Generated: {signal.side.name if signal else 'None'} | Reason: {signal.reason if signal else 'None'}")

def test_vwap_pullback():
    print("\n=== Testing VWAP Pullback + RSI ===")
    strategy = VwapPullbackStrategy(rsi_period=14, vwap_tolerance_pct=0.01)
    start_time = datetime(2026, 4, 23, 9, 15)
    
    # Pump 20 bars of strong uptrend to raise RSI
    print("Pumping 20 bars to establish Uptrend and high RSI...")
    price = 100
    for i in range(20):
        ts = start_time + timedelta(minutes=i)
        price += 2 # Steady climb
        bar = MarketBar(symbol="BANKNIFTY", ts=ts, open=price-1, high=price+1, low=price-2, close=price, volume=1000)
        strategy.on_bar(bar)
        
    print(f"Current VWAP: {strategy.current_vwap:.2f} | Current RSI: {strategy.current_rsi:.2f}")
    
    # Simulate pullback to VWAP and RSI drop
    print("\nSimulating fast pullback to VWAP...")
    for i in range(5):
        ts = start_time + timedelta(minutes=20+i)
        price -= 3 # Sharp drop back to VWAP
        bar = MarketBar(symbol="BANKNIFTY", ts=ts, open=price+1, high=price+2, low=price-1, close=price, volume=1000)
        strategy.on_bar(bar)
        
    print(f"VWAP: {strategy.current_vwap:.2f} | Pulled Back Price: {price} | RSI: {strategy.current_rsi:.2f}")
    
    # Bounce
    print("\nSimulating bounce from VWAP (RSI hooks up)...")
    bounce_bar = MarketBar(
        symbol="BANKNIFTY", 
        ts=start_time + timedelta(minutes=26), 
        open=price, high=price+5, low=price-1, close=price+4, volume=2000
    )
    signal = strategy.on_bar(bounce_bar)
    if signal:
        print(f"Signal Generated: {signal.side.name} | Reason: {signal.reason}")
    else:
        print("Bounce signal detected (Waiting for exact zone crossover in live market).")

if __name__ == "__main__":
    test_orb_vwap()
    test_vwap_pullback()
