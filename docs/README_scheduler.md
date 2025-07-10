# Real-Time Stock Data Scheduler

## Overview

The real-time scheduler module (`scheduler.py`) is responsible for automatically downloading ticker data at regular intervals throughout the trading day. It uses APScheduler to run jobs every minute during market hours, with the first execution happening immediately on startup.

## Features

- **Automated Data Collection**: Downloads 1-minute OHLCV data for all tickers in `tickers.json`
- **Immediate First Run**: Starts processing data immediately upon launch
- **Efficient Scheduling**: Runs every minute during market hours
- **Graceful Shutdown**: Properly handles Ctrl+C and system termination signals
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
poetry run python scripts/scheduler.py
```

This will:
1. Start the scheduler
2. Run the job immediately (with a 2-second initialization delay)
3. Schedule future jobs to run every minute during market hours
4. Continue running until interrupted with Ctrl+C

### Stopping the Scheduler

- Press `Ctrl+C` once to initiate a graceful shutdown
- The scheduler will complete the current job before exiting
- Press `Ctrl+C` again to force immediate shutdown if needed

### Job Execution Flow

For each scheduled execution:

1. Check if the market is open (weekday and trading hours)
2. Load tickers from `tickers.json`
3. For each ticker:
   - Check the last recorded timestamp in the database
   - Download only new OHLCV data since the last record (1-minute interval)
   - For first run, fetches the last day of data
   - Save new data to the database
   - Display progress with a progress bar
4. Show summary table with results including rows fetched and records saved

## Configuration

The scheduler uses the following default parameters:

- **Interval**: 1 minute (`DEFAULT_INTERVAL = "1m"`)
- **Period**: 20 days (`DEFAULT_PERIOD = "20d"`)
- **Market Hours**: 9:30 AM - 4:00 PM ET
- **Initial Delay**: 2 seconds (to ensure proper initialization)
- **Graceful Shutdown**: 5 minutes (allows current job to complete)

## Recent Changes

- Changed execution interval from 5 minutes to 1 minute
- Added immediate first run on startup
- Improved graceful shutdown handling
- Removed signal generation from scheduler (now handled separately)
- Enhanced progress and status display
- Added proper signal handling for Ctrl+C and system termination
- Improved error handling and logging

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
