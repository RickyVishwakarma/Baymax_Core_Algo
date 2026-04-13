import logging
from trading_system.data.dhan_manager import DhanInstrumentManager

logging.basicConfig(level=logging.INFO)

def test_instrument_manager():
    print("Testing DhanInstrumentManager...")
    mgr = DhanInstrumentManager(cache_dir="sample_data")
    try:
        mgr.ensure_ready()
        # Test lookup for a popular stock
        sec_id = mgr.get_security_id("NSE", "TCS")
        print(f"SUCCESS: TCS Security ID is {sec_id}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_instrument_manager()
