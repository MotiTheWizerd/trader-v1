# Trader-V1 Documentation

This directory contains documentation for the Trader-V1 stock trading prediction system.

## Contents

- [Download Tickers CLI Tool](download_tickers_cli.md): Documentation for the ticker data download CLI tool

## Project Structure

The project follows a clean, modular structure:

```
trader-v1/
├── core/               # Core business logic
│   └── data/           # Data handling modules
├── ui/                 # Terminal UI components using rich
├── scripts/            # Entry point scripts
├── tickers/            # Ticker data storage
│   └── data/           # Per-ticker folders with daily OHLCV files
│       ├── AAPL/       # Data for AAPL ticker
│       │   └── YYYYMMDD.csv
│       └── ...
├── config/             # Configuration files
└── docs/               # Documentation
```

## Getting Started

1. Make sure all dependencies are installed:
   ```
   poetry install --no-root
   ```

2. Download ticker data:
   ```
   python -m scripts.download_tickers
   ```

3. See specific tool documentation for more details on usage.

## Data Format

Each ticker's data is stored in CSV format with the following structure:
- Path: `tickers/data/<TICKER>/<YYYYMMdd>.csv`
- Format: CSV with headers (timestamp, open, high, low, close, volume)
- Default interval: 5-minute data
- Default window: 20 days
