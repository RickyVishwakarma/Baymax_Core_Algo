import subprocess
import sys

def run_test(cmd, name):
    print(f"\n" + "="*40)
    print(f" RUNNING: {name}")
    print("="*40)
    try:
        # Use full path to python from current venv if possible
        python_exe = sys.executable
        result = subprocess.run([python_exe] + cmd.split(), capture_output=False, text=True)
        if result.returncode == 0:
            print(f" [OK] {name} passed.")
            return True
        else:
            print(f" [FAIL] {name} failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print(f" [ERROR] Could not run {name}: {e}")
        return False

def main():
    tests = [
        ("test_regime_classifier.py", "AI Regime Classifier Unit Test"),
        ("test_multi_stock.py", "Multi-Stock Engine Stress Test"),
        ("trading_system/main.py --config config_multi.json --quote-only", "Network Health Check"),
        ("-m trading_system.analytics.optimizer --config test_config.json --data dummy_data.csv --grid test_grid.json --top-n 1", "Analytics Optimizer Test"),
        ("-m trading_system.analytics.walk_forward --config test_config.json --data dummy_data.csv --grid test_grid.json --is-bars 5 --oos-bars 3 --step-bars 3", "Walk-Forward Analysis Test")
    ]
    
    success_count = 0
    for cmd, name in tests:
        if run_test(cmd, name):
            success_count += 1
            
    print(f"\n\nFinal Result: {success_count}/{len(tests)} tests passed.")
    if success_count == len(tests):
        print("SYSTEM IS 100% HEALTHY.")
        sys.exit(0)
    else:
        print("SYSTEM HAS ISSUES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
