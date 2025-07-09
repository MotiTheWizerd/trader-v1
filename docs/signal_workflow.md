# Trading Signal Workflow Documentation

## Overview

The trading signal workflow is a key component of the stock trading prediction system. It processes OHLCV (Open, High, Low, Close, Volume) data for various tickers and generates BUY/SELL/STAY signals based on configurable technical indicators and filters.

## Signal Generation Process

### 1. Data Flow

```
Raw OHLCV Data → Technical Indicators → Signal Logic → Confidence Filtering → Peak Detection → Final Signals
```

### 2. Signal Types

- **BUY**: Indicates a potential entry point for a long position
- **SELL**: Indicates a potential exit point or short entry
- **STAY**: Indicates no action recommended (hold current position or stay out)

### 3. Core Components

#### Moving Average Signals

The system currently implements a moving average crossover strategy with the following features:

- **Moving Average Calculation**:
  - Short-term MA (default: 5-period)
  - Long-term MA (default: 20-period)

- **Base Signal Logic**:
  - BUY when short-term MA crosses above long-term MA
  - SELL when short-term MA crosses below long-term MA
  - STAY when there's insufficient data for calculation

- **Confidence Filtering**:
  - Calculates confidence as `abs(ma_short - ma_long) / ma_long`
  - Filters out low-confidence signals (default threshold: 0.005 or 0.5%)
  - Prevents false signals from small, insignificant crossovers

- **Peak Detection for SELL Signals**:
  - Calculates recent price maximum over a rolling window (default: 12 periods)
  - Identifies "peak zones" where price is within a threshold of recent maximum (default: 99%)
  - Only allows SELL signals when price is in a peak zone
  - Prevents premature SELL signals when price is still rising

## Usage Guide

### Command Line Interface

#### Running the Complete Pipeline

The `run_pipeline.py` script executes the entire workflow from data download to signal generation:

```bash
python scripts/run_pipeline.py [options]
```

Options:
- `--date YYYY-MM-DD`: Process data for a specific date (default: today)
- `--interval 5m`: Data interval (default: 5-minute bars)
- `--period 20d`: Period to download (default: 20 days)
- `--short-window 5`: Short-term moving average window (default: 5)
- `--long-window 20`: Long-term moving average window (default: 20)
- `--confidence-threshold 0.005`: Minimum confidence for signals (default: 0.005)
- `--peak-window 12`: Window for peak detection (default: 12)
- `--peak-threshold 0.99`: Threshold for peak zone detection (default: 0.99)
- `--no-reasoning`: Exclude reasoning text from signals

#### Running Individual Components

**Data Download Only**:
```bash
python scripts/download_tickers.py [options]
```

**Signal Generation Only**:
```bash
python scripts/generate_ma_signals.py [options]
```

Additional options:
- `--ticker SYMBOL`: Process a specific ticker only (e.g., AAPL)
- `--data-dir PATH`: Custom data directory

### Output Files

For each ticker and date, the system produces:

1. **OHLCV Data File**: `tickers/data/<TICKER>/<YYYYMMDD>.csv`
2. **Signal File**: `tickers/data/<TICKER>/<YYYYMMDD>_signals.csv`

### Signal File Format

The signal file contains the following columns:

- `timestamp`: Date and time of the bar
- `close`: Closing price
- `ma_short`: Short-term moving average
- `ma_long`: Long-term moving average
- `confidence`: Signal confidence value
- `recent_max`: Recent maximum price (for peak detection)
- `is_peak_zone`: Boolean indicating if price is in a peak zone
- `signal`: BUY, SELL, or STAY
- `reasoning`: Text explanation of the signal (if enabled)

## Configuration

### Tickers

Ticker symbols are defined in `tickers.json` at the project root:

```json
{
    "tickers": [
        "AAPL",
        "MSFT",
        "NVDA",
        "TSLA"
    ]
}
```

### Signal Parameters

Key parameters that affect signal generation:

1. **Moving Average Windows**:
   - `short_window`: Shorter-term MA period (default: 5)
   - `long_window`: Longer-term MA period (default: 20)
   - Smaller windows are more responsive but may generate more false signals

2. **Confidence Threshold**:
   - `confidence_threshold`: Minimum normalized distance between MAs (default: 0.005)
   - Higher values reduce false signals but may miss some opportunities
   - Range: 0.001 (0.1%) to 0.02 (2%) is typical

3. **Peak Detection**:
   - `peak_window`: Lookback window for peak detection (default: 12)
   - `peak_threshold`: How close price must be to recent max (default: 0.99 or 99%)
   - Smaller peak windows are more responsive to local peaks
   - Lower threshold values (e.g., 0.95) allow SELL signals further from peaks

## Advanced Usage

### Programmatic API

You can import and use the signal generation modules in your own Python code:

```python
from core.signals.moving_average import generate_ma_signals

# Generate signals for a specific ticker
signals_file = generate_ma_signals(
    ticker="AAPL",
    date="2025-07-08",
    short_window=5,
    long_window=20,
    confidence_threshold=0.005,
    peak_window=12,
    peak_threshold=0.99,
    include_reasoning=True
)

# Process the signals
import pandas as pd
signals = pd.read_csv(signals_file)
buy_signals = signals[signals["signal"] == "BUY"]
```

### Adding New Signal Types

The system is designed to be extensible. To add new signal types:

1. Create a new module in `core/signals/`
2. Implement a signal generation function similar to `generate_ma_signals`
3. Create a CLI script in `scripts/` to expose the new functionality

## Best Practices

1. **Parameter Tuning**:
   - Backtest different parameter combinations to find optimal settings for your trading style
   - Consider different parameters for different market conditions or ticker volatility

2. **Signal Validation**:
   - Always validate signals with additional indicators or analysis
   - The system provides signals as points of interest, not definitive trade instructions

3. **Data Freshness**:
   - Run the pipeline daily to ensure signals are based on the latest data
   - Consider intraday updates for more active trading

4. **Signal Interpretation**:
   - BUY signals work best in uptrends
   - SELL signals work best at local tops or in downtrends
   - Consider market context and overall trend

## Troubleshooting

### Common Issues

1. **Missing Data**:
   - Error: "OHLCV data file not found"
   - Solution: Run the data download script first or check ticker symbol

2. **No Signals Generated**:
   - Cause: Confidence threshold may be too high
   - Solution: Try lowering the confidence threshold

3. **Too Many Signals**:
   - Cause: Confidence threshold may be too low
   - Solution: Increase the confidence threshold

4. **Few SELL Signals**:
   - Cause: Peak detection may be too restrictive
   - Solution: Adjust peak_threshold to a lower value (e.g., 0.95)

### Logging and Debugging

The system uses the `rich` library for console output with color-coded information:
- Green: Success messages and BUY signals
- Red: Error messages and SELL signals
- Yellow: Warning messages and STAY signals
- Blue: Informational messages

## Future Enhancements

Planned improvements to the signal workflow:

1. **Additional Indicators**:
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - Volume-based signals

2. **Machine Learning Models**:
   - Signal validation using ML
   - Pattern recognition for improved entry/exit points

3. **Performance Metrics**:
   - Signal accuracy tracking
   - Backtest reporting
