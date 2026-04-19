import unittest
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from trading_system.analytics.optimizer import run_optimization

class TestOptimizer(unittest.TestCase):
    def setUp(self):
        # Create a synthetic CSV file
        self.csv_path = "test_data.csv"
        self.grid_path = "test_grid.json"
        self.out_path = "test_out.json"
        
        with open(self.csv_path, "w") as f:
            f.write("timestamp,open,high,low,close,volume\n")
            # Generate a simple trending dataset
            start_ts = datetime(2026, 1, 1, 10, 0, 0)
            base_price = 100.0
            for i in range(100):
                # Price moves up steadily
                p = base_price + (i * 0.5)
                ts_str = (start_ts + timedelta(minutes=i)).isoformat()
                f.write(f"{ts_str},{p-0.1},{p+0.5},{p-0.5},{p},1000\n")
                
        # Create a simple param grid
        grid = {
            "supertrend": {
                "atr_period": [5, 10],
                "multiplier": [2.0, 3.0]
            }
        }
        with open(self.grid_path, "w") as f:
            json.dump(grid, f)
            
    def tearDown(self):
        # Cleanup
        for path in [self.csv_path, self.grid_path, self.out_path]:
            if os.path.exists(path):
                os.remove(path)

    @patch("sys.argv", ["optimizer.py", "--symbol", "TEST", "--data", "test_data.csv", "--config", "config_multi.json", "--grid", "test_grid.json", "--out", "test_out.json"])
    def test_optimization_run(self):
        # Ensure config_multi.json exists (which it does in the project root)
        
        # Run the optimizer
        run_optimization()
        
        # Verify it wrote the output
        self.assertTrue(os.path.exists(self.out_path), "Optimizer should create the output file")
        
        with open(self.out_path, "r") as f:
            data = json.load(f)
            
        self.assertIn("TEST", data, "Output should contain the TEST symbol")
        self.assertIn("strategy", data["TEST"])
        self.assertIn("params", data["TEST"]["strategy"])
        
        params = data["TEST"]["strategy"]["params"]
        self.assertIn("atr_period", params)
        self.assertIn("multiplier", params)
        
        print(f"Test Passed: Best params found -> {params}")

if __name__ == "__main__":
    unittest.main()
