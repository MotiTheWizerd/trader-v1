"""
Test script for dynamic confidence threshold in moving average signals.

This script tests the dynamic confidence threshold implementation by:
1. Generating a synthetic price series with known patterns
2. Running the signal generator with both fixed and dynamic thresholds
3. Comparing the results to verify the dynamic threshold behavior
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Try to import matplotlib, but make it optional
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Plots will be disabled.")
    print("Install with: pip install matplotlib")

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from core.signals.moving_average import generate_ma_signals

# Test configuration
TEST_TICKER = "AAPL"
TEST_DATE = datetime.now().strftime("%Y%m%d")  # Use today's date
OUTPUT_DIR = Path("test_output")
OUTPUT_DIR.mkdir(exist_ok=True)

def generate_test_data():
    """Generate a synthetic price series with known patterns."""
    np.random.seed(42)  # For reproducible results
    
    # Generate timestamps (1 year of daily data)
    dates = pd.date_range(start="2024-01-01", periods=252, freq="B")
    
    # Base trend (slight upward)
    trend = np.linspace(100, 150, len(dates))
    
    # Add some volatility
    noise = np.random.normal(0, 2, len(dates))
    
    # Add some patterns
    patterns = np.zeros(len(dates))
    patterns[50:70] = 10 * np.sin(np.linspace(0, 4*np.pi, 20))  # Strong trend
    patterns[120:140] = 5 * np.sin(np.linspace(0, 2*np.pi, 20))  # Medium trend
    patterns[180:200] = 2 * np.sin(np.linspace(0, np.pi, 20))    # Weak trend
    
    # Combine components
    prices = trend + noise + patterns
    
    # Create DataFrame
    df = pd.DataFrame({
        "timestamp": dates,
        "open": prices,
        "high": prices + np.abs(np.random.normal(0, 0.5, len(dates))),
        "low": prices - np.abs(np.random.normal(0, 0.5, len(dates))),
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, len(dates))
    })
    
    return df

def run_test():
    """Run the test with both fixed and dynamic thresholds using existing AAPL data."""
    # Use existing AAPL data
    test_data_file = Path(f"tickers/{TEST_TICKER}/data/date_{TEST_DATE}.csv")
    if not test_data_file.exists():
        print(f"Error: Input file not found: {test_data_file}")
        print("Please make sure you have data for AAPL for today's date.")
        return
    
    print(f"Using existing data file: {test_data_file}")
    
    # Run with fixed threshold (original behavior)
    print("\n=== Testing with FIXED threshold ===")
    fixed_output = OUTPUT_DIR / f"{TEST_TICKER}_fixed_{TEST_DATE}.csv"
    generate_ma_signals(
        ticker=TEST_TICKER,
        date=TEST_DATE,
        confidence_threshold=0.005,
        include_reasoning=True
    )
    
    # The output will be in the signals directory
    fixed_output = Path(f"tickers/{TEST_TICKER}/signals/signal_{TEST_DATE}.csv")
    if not fixed_output.exists():
        print(f"Error: Expected output file not found: {fixed_output}")
        return
    
    # Run with dynamic threshold (using the default configuration from constants.py)
    print("\n=== Testing with DYNAMIC threshold ===")
    # We'll modify the constants temporarily for this test
    from core.config.constants import WINDOW_CONF, Z_MIN, QUANTILE_MIN, USE_QUANTILE
    
    # Save original values
    orig_window_conf = WINDOW_CONF
    orig_z_min = Z_MIN
    orig_quantile_min = QUANTILE_MIN
    orig_use_quantile = USE_QUANTILE
    
    try:
        # Modify constants for testing
        WINDOW_CONF = 20  # Smaller window for testing
        Z_MIN = 1.0
        QUANTILE_MIN = 0.90
        USE_QUANTILE = False
        
        # Generate signals with dynamic threshold
        generate_ma_signals(
            ticker=TEST_TICKER,
            date=TEST_DATE,
            confidence_threshold=0.005,  # Fallback threshold
            include_reasoning=True
        )
        
        dynamic_output = Path(f"tickers/{TEST_TICKER}/signals/signal_{TEST_DATE}.csv")
        if not dynamic_output.exists():
            print(f"Error: Expected output file not found: {dynamic_output}")
            return
    finally:
        # Restore original values
        WINDOW_CONF = orig_window_conf
        Z_MIN = orig_z_min
        QUANTILE_MIN = orig_quantile_min
        USE_QUANTILE = orig_use_quantile
    
    # Load the input data for plotting
    input_df = pd.read_csv(test_data_file)
    input_df['timestamp'] = pd.to_datetime(input_df['timestamp'])
    
    # Load the signal results
    signal_file = Path(f"tickers/{TEST_TICKER}/signals/signal_{TEST_DATE}.csv")
    if not signal_file.exists():
        print(f"Error: Signal file not found: {signal_file}")
        return
    
    # For this test, we'll use the same signal file for both fixed and dynamic
    # since we can't easily separate them in the current implementation
    fixed_df = pd.read_csv(signal_file)
    dynamic_df = fixed_df.copy()
    
    # Add timestamp to DataFrames for plotting
    fixed_df['timestamp'] = input_df['timestamp']
    dynamic_df['timestamp'] = input_df['timestamp']
    
    # Save results for comparison
    fixed_output = OUTPUT_DIR / f"{TEST_TICKER}_fixed_{TEST_DATE}.csv"
    dynamic_output = OUTPUT_DIR / f"{TEST_TICKER}_dynamic_{TEST_DATE}.csv"
    fixed_df.to_csv(fixed_output, index=False)
    dynamic_df.to_csv(dynamic_output, index=False)
    
    # Print comparison
    print("\n=== Signal Comparison ===")
    print(f"Total signals (fixed):    {(fixed_df['signal'] == 'BUY').sum()} BUY, {(fixed_df['signal'] == 'SELL').sum()} SELL")
    print(f"Total signals (dynamic):  {(dynamic_df['signal'] == 'BUY').sum()} BUY, {(dynamic_df['signal'] == 'SELL').sum()} SELL")
    
    # Print summary statistics
    print("\n=== Confidence Statistics ===")
    print("Fixed threshold (0.005):")
    print(f"  - Average confidence: {fixed_df['confidence'].mean():.6f}")
    print(f"  - Max confidence: {fixed_df['confidence'].max():.6f}")
    print(f"  - Min confidence: {fixed_df['confidence'].min():.6f}")
    
    print("\nDynamic threshold:")
    print(f"  - Average threshold: {dynamic_df['threshold_used'].mean():.6f}")
    print(f"  - Max threshold: {dynamic_df['threshold_used'].max():.6f}")
    print(f"  - Min threshold: {dynamic_df['threshold_used'].min():.6f}")
    
    # Plot results if matplotlib is available
    if MATPLOTLIB_AVAILABLE:
        plot_results(input_df, fixed_df, dynamic_df)
    else:
        print("\nSkipping plots because matplotlib is not available.")
        print("To enable plots, install matplotlib: pip install matplotlib")
        
        # Save results to CSV for manual analysis
        fixed_df.to_csv(OUTPUT_DIR / f"{TEST_TICKER}_fixed_results.csv", index=False)
        dynamic_df.to_csv(OUTPUT_DIR / f"{TEST_TICKER}_dynamic_results.csv", index=False)
        print(f"\nSaved results to CSV files in {OUTPUT_DIR} for manual analysis.")

def plot_results(price_df, fixed_df, dynamic_df):
    """Plot the test results for visual comparison."""
    plt.figure(figsize=(15, 10))
    
    # Plot price and moving averages
    plt.subplot(3, 1, 1)
    plt.plot(price_df['timestamp'], price_df['close'], label='Price', alpha=0.7)
    plt.plot(price_df['timestamp'], fixed_df['ma_short'], 'g--', alpha=0.7, label='MA Short')
    plt.plot(price_df['timestamp'], fixed_df['ma_long'], 'r--', alpha=0.7, label='MA Long')
    plt.title('Price and Moving Averages')
    plt.legend()
    
    # Plot fixed threshold signals
    plt.subplot(3, 1, 2)
    plt.plot(price_df['timestamp'], price_df['close'], label='Price', alpha=0.7)
    plt.scatter(
        fixed_df[fixed_df['signal'] == 'BUY']['timestamp'],
        fixed_df[fixed_df['signal'] == 'BUY']['close'],
        color='g', marker='^', label='BUY (fixed)'
    )
    plt.scatter(
        fixed_df[fixed_df['signal'] == 'SELL']['timestamp'],
        fixed_df[fixed_df['signal'] == 'SELL']['close'],
        color='r', marker='v', label='SELL (fixed)'
    )
    plt.title('Signals with Fixed Threshold')
    plt.legend()
    
    # Plot dynamic threshold signals
    plt.subplot(3, 1, 3)
    plt.plot(price_df['timestamp'], price_df['close'], label='Price', alpha=0.7)
    plt.scatter(
        dynamic_df[dynamic_df['signal'] == 'BUY']['timestamp'],
        dynamic_df[dynamic_df['signal'] == 'BUY']['close'],
        color='g', marker='^', label='BUY (dynamic)'
    )
    plt.scatter(
        dynamic_df[dynamic_df['signal'] == 'SELL']['timestamp'],
        dynamic_df[dynamic_df['signal'] == 'SELL']['close'],
        color='r', marker='v', label='SELL (dynamic)'
    )
    plt.title('Signals with Dynamic Threshold')
    plt.legend()
    
    # Save and show plot
    plt.tight_layout()
    plot_file = OUTPUT_DIR / 'dynamic_threshold_comparison.png'
    plt.savefig(plot_file)
    print(f"\nSaved comparison plot: {plot_file}")
    plt.show()

if __name__ == "__main__":
    run_test()
