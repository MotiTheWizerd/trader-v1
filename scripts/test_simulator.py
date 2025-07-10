"""
Test script for the data simulator.
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.data.simulator import DataSimulator, simulate_ticker_data

def test_simulator():
    """Test the data simulator with various configurations."""
    print("Testing Data Simulator...")
    
    # Test 1: Basic simulation with default parameters
    print("\nTest 1: Basic simulation with default parameters")
    simulator = DataSimulator()
    data = simulator.generate_candles(5)
    print("Generated data (first 5 rows):")
    print(data.head())
    
    # Test 2: Save simulated data to file
    print("\nTest 2: Save simulated data to file")
    file_path = simulator.save_simulated_data("TEST", 10)
    print(f"Data saved to: {file_path}")
    
    # Test 3: Use convenience function
    print("\nTest 3: Using convenience function")
    file_path = simulate_ticker_data("AAPL", num_candles=3, base_price=150.0, volatility=0.02)
    print(f"Apple data saved to: {file_path}")
    
    # Test 4: Generate data for a specific time period
    print("\nTest 4: Generate data for a specific time period")
    test_time = datetime.now() - timedelta(hours=1)
    data = simulator.generate_candles(3, timestamp=test_time)
    print("Data with specific timestamps:")
    print(data)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_simulator()
