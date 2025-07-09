# Download Tickers CLI Tool

## Overview

The `download_tickers.py` script is a command-line interface (CLI) tool for downloading historical stock ticker data using the yfinance library. It follows the project's structure rules and saves data in the format `tickers/data/<TICKER>/<YYYYMMdd>.csv`.

## Features

- Download data for multiple tickers at once
- Specify date ranges or periods
- Control data granularity with different intervals (5m, 1h, 1d, etc.)
- Preview downloaded data in the terminal
- Beautiful terminal output using the `rich` library
- Progress tracking during downloads

## Usage

```bash
python -m scripts.download_tickers [OPTIONS]
```

### Basic Examples

1. Download all tickers from tickers.json with default settings (20 days of 5-minute data):
   ```bash
   python -m scripts.download_tickers
   ```

2. Download specific tickers:
   ```bash
   python -m scripts.download_tickers --tickers AAPL MSFT GOOG
   ```

3. Download data for a specific date range:
   ```bash
   python -m scripts.download_tickers --start-date 2025-06-01 --end-date 2025-07-01
   ```

4. Download data with a specific interval:
   ```bash
   python -m scripts.download_tickers --interval 1h
   ```

5. Preview the downloaded data:
   ```bash
   python -m scripts.download_tickers --preview
   ```

6. Specify a custom date for the output file:
   ```bash
   python -m scripts.download_tickers --date 2025-07-08
   ```
   
   > **Note on File Naming**: By default, the tool will use the following logic for naming files:
   > - If `--date` is specified, that date will be used for the filename
   > - Otherwise, if `--end-date` is specified, that date will be used
   > - Otherwise, if `--start-date` is specified, that date will be used
   > - If none of the above are specified, today's date will be used

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--start-date` | Start date for data download (YYYY-MM-DD) | None |
| `--end-date` | End date for data download (YYYY-MM-DD) | None |
| `--period` | Period to download (e.g., 1d, 5d, 1mo, 3mo, 1y, max) | 20d |
| `--interval` | Data interval (e.g., 1d, 1h, 5m) | 5m |
| `--date` | Date to use for file naming (YYYY-MM-DD) | Today |
| `--tickers` | Specific tickers to download | All from tickers.json |
| `--preview` | Preview the downloaded data | False |

## Data Storage and Cleaning

Data is stored in CSV files with the following structure:

```
tickers/data/<TICKER>/<YYYYMMdd>.csv
```

For example, Apple stock data for July 8, 2025 would be stored at:

```
tickers/data/AAPL/20250708.csv
```

### Data Cleaning Process

Before saving, all data goes through a cleaning pipeline that ensures:

1. Unnecessary columns (`Dividends`, `Stock Splits`) are removed
2. The `timestamp` column is properly parsed as datetime
3. Rows are sorted by `timestamp`
4. Column names are consistent and lowercase
5. No null values exist in the data
6. Only the required columns are included: `timestamp`, `open`, `high`, `low`, `close`, `volume`

Each CSV file contains the following columns:
- timestamp: Date and time of the data point
- open: Opening price
- high: Highest price during the interval
- low: Lowest price during the interval
- close: Closing price
- volume: Trading volume

## Examples

### Download 1 Hour Data for Apple and Microsoft for the Last Month

```bash
python -m scripts.download_tickers --tickers AAPL MSFT --interval 1h --period 1mo
```

### Download 5-Minute Data for a Specific Date Range

```bash
python -m scripts.download_tickers --start-date 2025-06-15 --end-date 2025-07-01 --interval 5m
```

### Download Daily Data for All Tickers and Preview Results

```bash
python -m scripts.download_tickers --interval 1d --preview
```

## Troubleshooting

### Data Availability Limitations

Yahoo Finance has the following limitations for historical data:

| Interval | Maximum Historical Range |
|----------|-------------------------|
| 1m       | Last 7 days             |
| 5m       | Last 60 days            |
| 1h       | Last 730 days (2 years) |
| 1d       | ~50 years               |

If you're trying to download data outside these ranges, you'll receive an error message.

### Market Holidays and Weekends

Please note that stock market data is only available for trading days. The tool will not return data for:

- Weekends (Saturday and Sunday)
- Market holidays (e.g., New Year's Day, Independence Day, Christmas)
- Extended hours outside of regular trading hours (for some intervals)

If you request data for a date range that includes non-trading days, those days will simply be omitted from the results.

### Common Issues

1. **No data available for ticker**
   - Check if the ticker symbol is correct
   - Try a different date range
   - Verify that the ticker is still active
   - Ensure you're requesting data within the available range for your chosen interval

2. **Error downloading data**
   - Check your internet connection
   - Verify that Yahoo Finance is accessible
   - Try again later as Yahoo Finance may have rate limits
   - For 5m data, ensure you're only requesting data from the last 60 days

### Error Messages

If you see error messages related to missing data or API limits:
- Try reducing the number of tickers or the date range
- Wait a few minutes and try again (yfinance has API rate limits)
- Check that the ticker symbol is valid and actively traded
