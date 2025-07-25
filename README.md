# Trader-V1

A stock trading prediction system that analyzes ticker data and generates trading signals in real-time.

## Features

- Real-time scheduler that runs during market hours (NYSE calendar-aware)
- Structured JSON logging for analytics and monitoring
- Smart data downloads:
  - Full 20-day history for new tickers
  - Incremental 5-minute updates for existing tickers
  - Visual progress tracking with rich library
  - Database integration for efficient data storage
- Downloads historical OHLCV data for stock tickers using yfinance
- Organized data storage in PostgreSQL database
- Clean terminal UI using rich library with real-time progress updates
- Generates trading signals based on technical indicators (separate pipeline step)
- Retry logic for network failures

## Usage

### Data Download

```bash
# Run the download pipeline through the dashboard
poetry run python dashboard.py
# Then select option 2 (Run Complete Pipeline)

# Or run directly
poetry run python -m scripts.dashboard run-pipeline

# Available options:
# --date: Specify date (YYYY-MM-DD format)
# --interval: Data interval (default: 5m)
# --period: Period to download (default: 20d)
```

### Real-time Scheduler

```bash
# Run the real-time scheduler (runs every 5 minutes during market hours)
python -m scripts.run_scheduler

# Using Poetry
poetry run python scripts/run_scheduler.py
```

### Logs

Structured JSON logs are stored in the `logs/` directory with filename pattern `log_<YYYYMMDD>.jsonl`.
Each log entry contains:
- timestamp (ISO 8601)
- level (INFO, WARNING, ERROR)
- event (keyword)
- message (human-readable)
- ticker (optional)
- additional context data

## Project Structure

- `core/`: Core business logic
  - `data/`: Data handling modules
  - `logger.py`: Structured JSON logging module
  - `signals/`: Signal generation modules
- `ui/`: Terminal UI components
  - `scheduler_display.py`: Rich UI for scheduler
- `scripts/`: Entry point scripts
  - `scheduler.py`: Real-time scheduler implementation
  - `run_scheduler.py`: Scheduler entry point
- `tickers/`: Ticker data storage
  - `data/`: Per-ticker folders with daily OHLCV files
    - `AAPL/`: Data for AAPL ticker
      - `YYYYMMDD_HHMM.csv`: Snapshot data files
  - `signals/`: Generated trading signals
    - `AAPL/`: Signals for AAPL ticker
      - `YYYYMMDD_HHMM_signals.csv`: Signal files
- `logs/`: Structured JSON logs
  - `log_YYYYMMDD.jsonl`: Daily log files
- `config/`: Configuration files
- `docs/`: Documentation
  - `download_tickers_cli.md`: Detailed CLI documentation
  - `quick_reference.md`: Quick reference guide

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Download Tickers CLI Tool](docs/download_tickers_cli.md) - How to use the data downloader
- [Quick Reference](docs/quick_reference.md) - Command reference sheet
