# Quick Reference: download_tickers CLI

## Basic Usage

```bash
python -m scripts.download_tickers [OPTIONS]
```

## Common Commands

| Command | Description |
|---------|-------------|
| `python -m scripts.download_tickers` | Download all tickers with default settings (20d of 5m data) |
| `python -m scripts.download_tickers --tickers AAPL MSFT` | Download specific tickers |
| `python -m scripts.download_tickers --interval 1h` | Download hourly data |
| `python -m scripts.download_tickers --preview` | Preview data after download |
| `python -m scripts.download_tickers --period 5d` | Download last 5 days of data |

## Data Availability Limitations

⚠️ **Important**: Yahoo Finance has the following limitations:

| Interval | Maximum Historical Range |
|----------|-------------------------|
| 1m       | Last 7 days             |
| **5m**   | **Last 60 days**        |
| 1h       | Last 730 days (2 years) |
| 1d       | ~50 years               |

⚠️ **Note**: Data is only available for trading days (no weekends or market holidays)

## All Options

| Option | Description | Default |
|--------|-------------|---------|
| `--start-date` | Start date (YYYY-MM-DD) | None |
| `--end-date` | End date (YYYY-MM-DD) | None |
| `--period` | Period to download | 20d |
| `--interval` | Data interval | 5m |
| `--date` | File naming date | Today |
| `--tickers` | Specific tickers | All from tickers.json |
| `--preview` | Preview data | False |

## Output Location

Data is saved to: `tickers/data/<TICKER>/<YYYYMMdd>.csv`

## Output Format

Data is saved as CSV files with columns:
- timestamp
- open
- high
- low
- close
- volume

### Data Cleaning

All data is automatically cleaned before saving:
- Unnecessary columns removed (Dividends, Stock Splits)
- Timestamp properly formatted
- Rows sorted by timestamp
- No null values
- Consistent column naming

### File Naming Logic

The date in the filename is determined by:
1. `--date` parameter if provided
2. Otherwise, `--end-date` if provided
3. Otherwise, `--start-date` if provided
4. Otherwise, today's date

## Examples

```bash
# Download 1h data for Apple for the last week
python -m scripts.download_tickers --tickers AAPL --interval 1h --period 7d

# Download data for a specific date range
python -m scripts.download_tickers --start-date 2025-06-01 --end-date 2025-07-01
```

For full documentation, see: `docs/download_tickers_cli.md`
