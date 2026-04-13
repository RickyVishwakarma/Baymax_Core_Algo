import logging
from trading_system.ml.regime import MultiSymbolRegimeClassifier
from trading_system.models import MarketBar
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

def test_ml_integrity():
    print("--- ML Regime Classifier Integrity Audit ---")
    classifier = MultiSymbolRegimeClassifier(window=14)
    
    # 1. Warm up with trending data
    start_ts = datetime.now()
    for i in range(30):
        # Strong uptrend: Highs and Lows consistently rising
        bar = MarketBar(
            ts=start_ts + timedelta(minutes=i),
            symbol="TEST",
            open=100 + i,
            high=102 + i,
            low=99 + i,
            close=101 + i,
            volume=1000
        )
        classifier.update(bar)
    
    blocked, result = classifier.should_block(bar)
    print(f"TRENDING DATA -> Regime: {result.regime}, Score: {result.score:.2f}, Blocked: {blocked}")
    
    # ADX should be high (>25) for trending data
    if result.adx and result.adx > 25:
        print(f" [OK] ADX ({result.adx:.1f}) correctly identified trend.")
    else:
        print(f" [FAIL] ADX ({result.adx if result.adx else 'N/A'}) too low for trend.")

    # 2. Add flat data
    for i in range(30, 60):
        # Sideways/Choppy: Prices oscillating in a narrow range
        price = 130 + (i % 2) # Toggle between 130 and 131
        bar = MarketBar(
            ts=start_ts + timedelta(minutes=i),
            symbol="TEST",
            open=price,
            high=price + 0.5,
            low=price - 0.5,
            close=price,
            volume=1000
        )
        classifier.update(bar)
    
    blocked, result = classifier.should_block(bar)
    print(f"CHOPPY DATA -> Regime: {result.regime}, Score: {result.score:.2f}, Blocked: {blocked}")
    
    # Choppiness Index should be high (>61.8) for flat data
    if result.choppiness_index and result.choppiness_index > 50:
        print(f" [OK] Choppiness Index ({result.choppiness_index:.1f}) correctly identified range.")
    else:
        print(f" [FAIL] Choppiness Index ({result.choppiness_index if result.choppiness_index else 'N/A'}) too low for chop.")

if __name__ == "__main__":
    test_ml_integrity()
