# Confidence Thresholds in Moving Average Signals

## Overview

This document explains the two approaches to confidence thresholding in the moving average signal generator: **fixed** and **dynamic** confidence thresholds. These thresholds determine when a moving average crossover generates a trading signal based on the strength of the crossover.

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

### Dynamic vs Fixed Threshold

You can switch between dynamic and fixed confidence thresholds by modifying `USE_DYNAMIC_CONFIDENCE` in `core/config/constants.py`:

```python
# Moving Average Signal Generation
WINDOW_CONF = 100    # Rolling window size for dynamic confidence calculation
Z_MIN = 1.0          # Minimum z-score for dynamic confidence threshold
QUANTILE_MIN = 0.90  # Minimum quantile for dynamic confidence threshold
USE_QUANTILE = False # Whether to use quantile (True) or z-score (False) for dynamic threshold
USE_DYNAMIC_CONFIDENCE = True  # Set to False to use fixed threshold
```

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

### Using Dynamic Threshold (Default)

By default, the system uses dynamic confidence thresholds. No code changes are needed:

```python
# This will use dynamic thresholding with default parameters
generate_ma_signals(ticker='AAPL')
```

### Using Fixed Threshold

To use a fixed threshold instead:

1. Set `USE_DYNAMIC_CONFIDENCE = False` in `core/config/constants.py`
2. The system will then use the `confidence_threshold` parameter:

```python
# This will use a fixed 1% threshold
generate_ma_signals(ticker='AAPL', confidence_threshold=0.01)
```

### Checking Which Threshold Was Used

The generated signal DataFrame includes a `threshold_method` column that indicates which thresholding method was used:
- `'mean + Xσ'` for dynamic z-score threshold
- `'XXth percentile'` for dynamic quantile threshold
- `'fixed'` for fixed threshold

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

The dynamic threshold adds minimal computational overhead since it uses efficient rolling window calculations. The impact is negligible for typical window sizes (< 200).
