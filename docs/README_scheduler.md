# Real-Time Stock Signal Scheduler

## Overview

The real-time scheduler module (`scheduler.py`) is responsible for automatically downloading ticker data and generating trading signals at regular intervals throughout the trading day. It uses APScheduler to run jobs every 5 minutes during market hours.

## Features

- **Automated Data Collection**: Downloads 5-minute OHLCV data for all tickers in `tickers.json`
- **Real-Time Signal Generation**: Generates BUY/SELL/STAY signals based on moving average crossovers
- **Timestamped Snapshots**: Saves data with timestamps in format `YYYYMMdd_HHmm`
- **Market Hours Awareness**: Only runs during US stock market trading hours
- **Rich Console Output**: Uses the `rich` library for formatted terminal output
- **Error Handling**: Gracefully handles exceptions per ticker and continues with others

## Directory Structure

```
tickers/
├── data/
│   ├── AAPL/
│   │   ├── 20250708_0930.csv         # OHLCV data snapshot
│   │   ├── 20250708_0935.csv
│   │   └── ...
│   └── ...
└── signals/
    ├── AAPL/
    │   ├── 20250708_0930_signals.csv # Signal snapshot
    │   ├── 20250708_0935_signals.csv
    │   └── ...
    └── ...
```

## Usage

### Running the Scheduler

```bash
python scripts/scheduler.py
```

This will:
1. Start the scheduler
2. Run the job immediately once
3. Schedule future jobs to run every 5 minutes
4. Continue running until interrupted with Ctrl+C

### Job Execution Flow

For each scheduled execution:

1. Check if the market is open (weekday and trading hours)
2. Load tickers from `tickers.json`
3. For each ticker:
   - Download latest OHLCV data (5-minute interval, 20-day window)
   - Save data snapshot with timestamp
   - Generate signals based on moving average crossovers
   - Save signals with timestamp
4. Display results table with success/failure status

## Configuration

The scheduler uses the following default parameters:

- **Interval**: 5 minutes (`DEFAULT_INTERVAL = "5m"`)
- **Period**: 20 days (`DEFAULT_PERIOD = "20d"`)
- **Market Hours**: 9:30 AM - 4:00 PM ET
- **Signal Parameters**:
  - Short-term MA window: 5
  - Long-term MA window: 20
  - Confidence threshold: 0.005 (0.5%)
  - Peak window: 12
  - Peak threshold: 0.99 (99%)

## Dependencies

- `apscheduler`: For scheduling jobs
- `pandas`: For data manipulation
- `yfinance`: For downloading stock data
- `rich`: For console output formatting

## Notes

- The scheduler skips execution when the market is closed (weekends, holidays, outside trading hours)
- Empty ticker entries in `tickers.json` are automatically skipped
- Each ticker is processed independently, so failures in one ticker don't affect others
- All timestamps are based on the local system time (production systems should use timezone-aware timestamps)
