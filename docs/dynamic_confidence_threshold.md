# Confidence Thresholds in Moving Average Signals

## Overview

This document explains the dual-approach confidence thresholding system in the moving average signal generator, which now supports generating both **fixed** and **dynamic** confidence signals simultaneously. These thresholds determine when a moving average crossover generates a trading signal based on the strength of the crossover.

## Key Changes

- **Dual Signal Generation**: The system now generates both fixed and dynamic confidence signals in a single run
- **Separate Output Files**: Signals are saved in separate CSV files with `_fixed` and `_dynamic` suffixes
- **Improved Error Handling**: More robust handling of edge cases and error conditions
- **Enhanced Logging**: Better visibility into which threshold method was used for each signal

## Signal Generation Modes

The system now supports three modes of operation:

1. **Fixed Confidence Only**: Uses only the fixed threshold approach
2. **Dynamic Confidence Only**: Uses only the dynamic threshold approach (default)
3. **Dual Mode**: Generates both fixed and dynamic signals simultaneously

## Fixed vs. Dynamic Confidence

### Fixed Confidence Threshold

The fixed confidence approach uses a constant threshold value for all market conditions:

- **How it works**:
  - A single threshold value is applied uniformly across all market conditions
  - Signals are generated when the confidence value exceeds this fixed threshold
  - Formula: `signal = 1 if conf_t > FIXED_THRESHOLD else 0`

- **Advantages**:
  - Simple to understand and implement
  - Consistent behavior across different market conditions
  - Fewer parameters to tune

- **Limitations**:
  - May generate too many signals in low-volatility markets
  - May miss opportunities in high-volatility markets where crossovers are more significant
  - Requires manual adjustment for different assets or market conditions

### Dynamic Confidence Threshold

The dynamic confidence approach adapts to changing market volatility:

- **How it works**:
  1. Calculates the raw confidence value:
     ```
     conf_t = |MA_short_t – MA_long_t| / MA_long_t
     ```
  2. Computes statistics from the previous `WINDOW_CONF` bars (default: 100):
     - Mean (μ) and standard deviation (σ) for z-score calculation
     - 90th percentile for quantile-based threshold
  3. Applies one of two thresholding methods (configurable):
     - **Z-score (default)**: `threshold = μ + Z_MIN * σ`
     - **Quantile**: `threshold = QUANTILE_MIN percentile`
  4. Falls back to the fixed `confidence_threshold` during the initial window or when volatility is too low (σ = 0)

- **Advantages**:
  - Automatically adapts to changing market volatility
  - Reduces false signals in choppy markets
  - Captures stronger trends more effectively
  - More robust across different market conditions

- **Limitations**:
  - More complex to implement and understand
  - Requires tuning of additional parameters
  - May be slower to compute due to rolling statistics

## When to Use Each Approach

### Use Fixed Confidence When:
- You need a simple, predictable strategy
- Backtesting shows consistent performance with a fixed threshold
- Trading lower-volatility assets with stable price action
- Computational resources are limited

### Use Dynamic Confidence When:
- Trading across different market conditions
- Dealing with assets that have varying volatility
- You want to reduce false signals in ranging markets
- You have the resources to backtest and tune the parameters

## Configuration

### Signal Generation Modes

You can control the signal generation mode by modifying `GENERATE_BOTH_SIGNAL_TYPES` in `core/config/constants.py`:

```python
# Signal Generation Modes
GENERATE_BOTH_SIGNAL_TYPES = True  # Set to False to generate only one type
USE_DYNAMIC_CONFIDENCE = True     # Which type to generate if not both

# Dynamic Threshold Parameters (when enabled)
WINDOW_CONF = 100    # Rolling window size for dynamic confidence calculation
Z_MIN = 1.0          # Minimum z-score for dynamic confidence threshold
QUANTILE_MIN = 0.90  # Minimum quantile for dynamic confidence threshold
USE_QUANTILE = False # Whether to use quantile (True) or z-score (False) for dynamic threshold
```

### Output Files

The system generates the following output files for each ticker:

- `{date}_{ticker}_signal_fixed.csv`: Signals using fixed confidence threshold
- `{date}_{ticker}_signal_dynamic.csv`: Signals using dynamic confidence threshold

Each file contains the following columns:
- `timestamp`: The time of the signal
- `open`, `high`, `low`, `close`, `volume`: Price and volume data
- `ma_short`, `ma_long`: Moving average values
- `signal`: The generated signal (BUY/SELL/STAY)
- `confidence`: The confidence value of the signal
- `threshold_used`: The threshold value that was applied
- `threshold_method`: The method used to determine the threshold

### Dynamic Threshold Parameters

When `USE_DYNAMIC_CONFIDENCE = True` (default), these parameters control the behavior:

- `WINDOW_CONF`: Number of lookback periods for calculating statistics (default: 100)
- `Z_MIN`: Multiplier for standard deviation in z-score method (default: 1.0)
- `QUANTILE_MIN`: Percentile for quantile-based threshold (default: 0.90)
- `USE_QUANTILE`: Whether to use quantile (True) or z-score (False) method

### Fixed Threshold Parameters

When `USE_DYNAMIC_CONFIDENCE = False`, the system uses a fixed threshold:
- The threshold is controlled by the `confidence_threshold` parameter in signal generation functions
- Default value is 0.005 (0.5%) if not specified

## Usage

### Generating Both Signal Types (Default)

By default, the system generates both fixed and dynamic confidence signals:

```python
# This will generate both fixed and dynamic signals
generate_ma_signals(ticker='AAPL')
```

### Generating a Single Signal Type

To generate only one type of signal:

1. Set `GENERATE_BOTH_SIGNAL_TYPES = False` in `core/config/constants.py`
2. Set `USE_DYNAMIC_CONFIDENCE` to choose which type to generate

```python
# To generate only dynamic signals with custom parameters
generate_ma_signals(
    ticker='AAPL',
    confidence_threshold=0.0075,  # Used if dynamic threshold falls back
    short_window=5,
    long_window=20
)
```

### Accessing the Generated Signals

```python
import pandas as pd

# Load the generated signals
date_str = "20250709"  # Replace with your date
ticker = "AAPL"

# Load both signal types
fixed_signals = pd.read_csv(f"tickers/{ticker}/signals/{date_str}_{ticker}_signal_fixed.csv")
dynamic_signals = pd.read_csv(f"tickers/{ticker}/signals/{date_str}_{ticker}_signal_dynamic.csv")

# Compare signals
print(f"Fixed threshold signals (first 5):")
print(fixed_signals[['timestamp', 'signal', 'confidence', 'threshold_used']].head())

print("\nDynamic threshold signals (first 5):")
print(dynamic_signals[['timestamp', 'signal', 'confidence', 'threshold_used', 'threshold_method']].head())
```

### Signal Analysis

#### Threshold Methods

Each signal includes metadata about how it was generated:

- **Fixed Threshold Signals**:
  - `threshold_method`: `'fixed (0.005000)'` (shows the fixed value used)
  - `threshold_used`: The fixed threshold value

- **Dynamic Threshold Signals**:
  - `threshold_method`: `'mean + 1.0σ'` or `'90th percentile'`
  - `threshold_used`: The calculated threshold value for each timestamp

#### Comparing Signals

To compare signals from both methods:

```python
# Count signals by type
def summarize_signals(signals, name):
    counts = signals['signal'].value_counts()
    print(f"\n{name} Signals:")
    print(f"  BUY: {counts.get('BUY', 0)}")
    print(f"  SELL: {counts.get('SELL', 0)}")
    print(f"  STAY: {counts.get('STAY', 0)}")
    print(f"  Threshold: {signals['threshold_used'].iloc[0]:.6f} ({signals['threshold_method'].iloc[0]})")

summarize_signals(fixed_signals, "Fixed")
summarize_signals(dynamic_signals, "Dynamic")
```

### Comparing Strategies

To compare fixed vs. dynamic threshold strategies:

```bash
python scripts/compare_signal_strategies.py
```

This will generate a comparison report in the `comparison_results` directory.

## Expected Results

- **Reduced false signals** in low-volatility periods
- **More sensitive detection** of meaningful crossovers in high-volatility periods
- **Balanced BUY/SELL signals** (SELL count should not exceed BUY count by > 30%)

## Testing

Run the test script to verify the implementation:

```bash
python tests/test_dynamic_confidence.py
```

This will generate test data and create visualizations comparing the two strategies.

## Troubleshooting

1. **Too many/few signals**: Adjust `Z_MIN` or `QUANTILE_MIN` in `constants.py`
2. **Slow performance**: Reduce `WINDOW_CONF` (but keep it large enough for meaningful statistics)
3. **Insufficient data**: Ensure you have at least `WINDOW_CONF` bars of historical data

## Performance Considerations

- **Dual Signal Generation**: Generating both signal types adds about 30-40% overhead compared to generating a single signal type
- **Memory Usage**: Each signal type is processed independently, so memory usage is approximately doubled when generating both
- **I/O Operations**: Two output files are written instead of one, but this has minimal impact on performance

For most use cases, the performance impact is negligible. However, if processing a large number of tickers or working with limited resources, you may want to generate only one signal type at a time.

## Best Practices

1. **Start with Both Types**: Initially generate both signal types to compare their performance
2. **Backtest Thoroughly**: Test both signal types across different market conditions
3. **Monitor Performance**: Keep track of which signal type performs better for each asset
4. **Adjust Parameters**: Fine-tune the parameters for each signal type based on backtesting results
5. **Consider Hybrid Approaches**: You might find that fixed thresholds work better for some assets while dynamic thresholds work better for others
