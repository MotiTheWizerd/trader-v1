# Trading Pipeline Workflow Documentation

## Overview

The trading pipeline is the central orchestration system that coordinates data downloading, signal generation, and result reporting. It provides a streamlined way to run the entire trading prediction workflow with a single command.

## Pipeline Architecture

```
                         ┌─────────────────┐
                         │   Dashboard UI   │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  Data Pipeline  │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼───────┐  ┌───────▼────────┐  ┌───────▼────────┐
    │  Data Download  │  │  Signal Gen    │  │  Data Cleanup  │
    │  (Option 2)     │  │  (Option 3)    │  │  (Option 1)    │
    └─────────────────┘  └────────────────┘  └────────────────┘
```

### Key Changes in v1.1:
- **Separated Data Download and Signal Generation**: These are now distinct operations
- **Improved Progress Tracking**: Real-time progress bars with detailed status
- **Database Integration**: All data is now stored in PostgreSQL
- **Cleaner UI**: Better organized dashboard with clear options

## Pipeline Components

### 1. Dashboard Interface (`dashboard.py`)

The main entry point that provides a user-friendly interface:

- Presents a menu of options:
  1. Clear Database: Remove all data from tickers_data and tickers_signals tables
  2. Run Complete Pipeline: Download data for all tickers
  3. Regenerate Signals: Generate trading signals from existing data
  4. Exit: Close the application
- Handles user input and error cases
- Displays progress and results in a clean, formatted way

### 2. Data Downloader (`core/data/downloader.py`)

Responsible for acquiring and storing historical price data:

- Downloads OHLCV data from Yahoo Finance
- Supports various intervals (1m, 5m, 1h, 1d)
- Stores data in PostgreSQL database with the following schema:
  - `tickers_data` table: Contains OHLCV data with timestamps
  - `tickers_signals` table: Stores generated trading signals
- Features:
  - Progress tracking with rich library
  - Batch processing of tickers
  - Error handling and retries
  - Duplicate detection

### 3. Signal Generator (`core/signals/moving_average.py`)

Processes OHLCV data to produce trading signals. The signal generator:

- Reads input files from: `tickers/data/<TICKER>/`
- Saves output signals to: `tickers/signals/<TICKER>/`
- Uses file naming convention: `<YYYYMMDD>_<TICKER>_signals.csv`
- Maintains separation between raw data and generated signals

- Calculates technical indicators (moving averages)
- Applies signal logic (crossovers)
- Implements confidence filtering
- Performs peak detection for SELL signals
- Saves signals to CSV files

### 4. Results Reporting

Provides visual feedback on pipeline execution:

- Uses Rich library for formatted console output
- Displays progress bars during processing
- Shows summary tables of results
- Highlights errors and warnings

## Pipeline Execution Flow

### 1. Data Download (Option 2)
1. **Initialization**:
   - Load ticker list from `tickers.json`
   - Set up database connection
   - Initialize progress tracking

2. **Data Acquisition**:
   - For each ticker:
     - Download OHLCV data from Yahoo Finance
     - Process and clean the data
     - Store in PostgreSQL database
     - Update progress bar
   - Display summary of downloaded data

### 2. Signal Generation (Option 3)
1. **Initialization**:
   - Load configuration parameters
   - Set up database connection
   - Initialize progress tracking

2. **Signal Processing**:
   - For each ticker with available data:
     - Load OHLCV data from database
     - Calculate technical indicators
     - Generate trading signals
     - Store signals in database
     - Update progress bar
   - Display summary of generated signals

### 3. Database Management (Option 1)
1. **Verification**:
   - Confirm user wants to proceed with data deletion
   - Verify database connection

2. **Cleanup**:
   - Truncate tickers_data table
   - Truncate tickers_signals table
   - Verify tables are empty
   - Display confirmation message

## Running the Pipeline

### Basic Usage

```bash
python scripts/run_pipeline.py
```

This runs the pipeline with default settings:
- Uses today's date
- Processes all tickers in `tickers.json`
- Uses 5-minute data intervals
- Downloads 20 days of historical data
- Applies default signal parameters

### Advanced Usage

```bash
python scripts/run_pipeline.py --date 2025-07-08 --interval 5m --period 20d --short-window 5 --long-window 20 --confidence-threshold 0.005 --peak-window 12 --peak-threshold 0.99
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--date` | Date to process (YYYY-MM-DD) | Today |
| `--interval` | Data interval (1m, 5m, 15m, 1h, 1d) | 5m |
| `--period` | Period to download (e.g., 20d, 60d) | 20d |
| `--short-window` | Short-term moving average window | 5 |
| `--long-window` | Long-term moving average window | 20 |
| `--confidence-threshold` | Minimum signal confidence | 0.005 |
| `--peak-window` | Window for peak detection | 12 |
| `--peak-threshold` | Threshold for peak zone detection | 0.99 |
| `--no-reasoning` | Exclude reasoning text from signals | False |

## Pipeline Output

### Console Output

The pipeline provides rich console output with:

- Color-coded progress bars
- Status messages for each step
- Error notifications for failed operations
- Summary tables of results

Example:
```
╭───────────────────────────────────────────────────────╮
│ Starting Trading Signal Pipeline for 2025-07-08       │
╰───────────────────────────────────────────────────────╯

Step 1: Downloading ticker data...
Downloading AAPL data... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
Downloading MSFT data... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Ticker ┃ File Path                                  ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ AAPL   │ tickers/data/AAPL/20250708.csv            │
│ MSFT   │ tickers/data/MSFT/20250708.csv            │
└────────┴──────────────────────────────────────────────┘

Step 2: Generating moving average signals...
Generating signals for 2 tickers... ━━━━━━━━━━━━━━━━━ 100%

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Ticker ┃ Signal File                                ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ AAPL   │ tickers/data/AAPL/20250708_signals.csv    │
│ MSFT   │ tickers/data/MSFT/20250708_signals.csv    │
└────────┴──────────────────────────────────────────────┘

╭───────────────────────────────────────────────────────────────╮
│ Trading Signal Pipeline Completed Successfully for 2025-07-08 │
╰───────────────────────────────────────────────────────────────╯
```

### File Output

The pipeline generates two types of files for each ticker:

1. **OHLCV Data Files**: `tickers/data/<TICKER>/<YYYYMMDD>.csv`
   - Contains raw price and volume data
   - Used as input for signal generation

2. **Signal Files**: `tickers/data/<TICKER>/<YYYYMMDD>_signals.csv`
   - Contains generated signals and technical indicators
   - Includes reasoning for each signal (if enabled)

## Pipeline Configuration

### Ticker Configuration

Tickers are defined in `tickers.json`:

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

To add new tickers, simply add them to this file.

### Data Directory Structure

The pipeline expects and maintains the following directory structure:

```
tickers/
├── data/
│   ├── AAPL/
│   │   ├── 20250708.csv
│   │   └── 20250708_signals.csv
│   ├── MSFT/
│   │   ├── 20250708.csv
│   │   └── 20250708_signals.csv
│   └── ...
└── ...
```

## Extending the Pipeline

### Adding New Data Sources

To add a new data source:

1. Create a new module in `core/data/`
2. Implement a download function similar to `download_ticker_data`
3. Update the pipeline to use the new data source

### Adding New Signal Types

To add a new signal generation method:

1. Create a new module in `core/signals/`
2. Implement a signal generation function
3. Update the pipeline to include the new signal type

### Custom Pipeline Steps

To add custom processing steps:

1. Modify `run_pipeline.py` to include the new step
2. Ensure proper error handling and reporting
3. Update the pipeline documentation

## Troubleshooting

### Common Pipeline Issues

1. **Data Download Failures**:
   - Error: "Failed to download data for ticker"
   - Possible causes: Network issues, invalid ticker symbol, API limits
   - Solution: Check internet connection, verify ticker symbols

2. **Signal Generation Errors**:
   - Error: "Error generating signals for ticker"
   - Possible causes: Missing data, file permission issues
   - Solution: Ensure data files exist and are readable

3. **Progress Bar Conflicts**:
   - Error: "Only one live display may be active at once"
   - Cause: Multiple Rich progress bars running simultaneously
   - Solution: Use the `use_single_progress=True` parameter

### Logging and Debugging

The pipeline uses Rich for console output with different colors for:
- Green: Success messages
- Red: Error messages
- Yellow: Warning messages
- Blue: Informational messages

For detailed debugging, you can modify the console verbosity in the pipeline scripts.

## Best Practices

1. **Regular Execution**:
   - Run the pipeline daily to maintain up-to-date signals
   - Consider automating with a scheduled task or cron job

2. **Parameter Tuning**:
   - Experiment with different signal parameters
   - Create separate configuration files for different strategies

3. **Data Management**:
   - Periodically archive old data files
   - Consider implementing a data retention policy

4. **Error Handling**:
   - Monitor pipeline execution for errors
   - Implement notification system for critical failures

## Future Enhancements

Planned improvements to the pipeline:

1. **Parallel Processing**:
   - Process multiple tickers simultaneously
   - Improve performance for large ticker lists

2. **Advanced Scheduling**:
   - Time-based execution during market hours
   - Event-driven pipeline triggers

3. **Results Database**:
   - Store signals in a database for easier querying
   - Track signal performance over time

4. **Web Dashboard**:
   - Visual interface for pipeline monitoring
   - Interactive signal exploration
