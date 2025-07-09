# Structured JSON Logging

The Trader-V1 system implements structured JSON logging for improved analytics, monitoring, and traceability. This document explains the logging system and how to use it effectively.

## Log File Format

Logs are stored in the `logs/` directory with filenames following the pattern `log_YYYYMMDD.jsonl`. Each file contains newline-delimited JSON objects (JSONL format), with one log entry per line.

### Log Entry Structure

Each log entry is a JSON object with the following fields:

| Field | Type | Description | Always Present |
|-------|------|-------------|----------------|
| timestamp | string | ISO 8601 formatted timestamp | Yes |
| level | string | Log level (INFO, WARNING, ERROR) | Yes |
| event | string | Event keyword identifier | Yes |
| message | string | Human-readable message | Yes |
| ticker | string | Ticker symbol (if applicable) | No |
| exception | object | Exception details (if applicable) | No |
| additional | object | Additional context data | No |

Example log entry:
```json
{
  "timestamp": "2025-07-09T00:38:55",
  "level": "INFO",
  "event": "download_start",
  "message": "Downloading data for AAPL",
  "ticker": "AAPL",
  "interval": "5m",
  "period": "20d"
}
```

## Common Event Types

The system uses consistent event keywords to categorize log entries:

### System Events
- `system_init` - System initialization
- `scheduler_startup` - Scheduler starting
- `scheduler_shutdown` - Scheduler shutting down
- `scheduler_error` - Error in scheduler operation

### Job Events
- `scheduler_job_start` - Scheduled job starting
- `scheduler_job_complete` - Scheduled job completed
- `market_closed` - Market closed detection
- `processing_tickers` - Processing ticker list

### Ticker Processing Events
- `process_ticker_start` - Starting to process a ticker
- `process_ticker_retry` - Retrying ticker processing
- `process_ticker_success` - Successfully processed ticker
- `process_ticker_failed` - Failed to process ticker

### Data Download Events
- `download_start` - Starting data download
- `download_complete` - Download completed
- `download_empty` - No data available
- `download_failed` - Download failed

### Signal Generation Events
- `signal_generation_start` - Starting signal generation
- `signal_generation_complete` - Signal generation completed
- `signal_generation_empty` - No signals generated
- `signal_generation_failed` - Signal generation failed

## Working with Log Files

### Basic Analysis

You can use standard command-line tools to analyze log files:

```bash
# Count log entries by level
cat logs/log_20250709.jsonl | grep -c "\"level\": \"INFO\""
cat logs/log_20250709.jsonl | grep -c "\"level\": \"WARNING\""
cat logs/log_20250709.jsonl | grep -c "\"level\": \"ERROR\""

# Find all errors
cat logs/log_20250709.jsonl | grep "\"level\": \"ERROR\""

# Find events for a specific ticker
cat logs/log_20250709.jsonl | grep "\"ticker\": \"AAPL\""
```

### Using jq

For more advanced analysis, you can use `jq`, a command-line JSON processor:

```bash
# Install jq
# On Windows: choco install jq
# On macOS: brew install jq
# On Linux: apt-get install jq

# Count events by type
cat logs/log_20250709.jsonl | jq -r '.event' | sort | uniq -c

# Get all download failures
cat logs/log_20250709.jsonl | jq -c 'select(.event == "download_failed")'

# Calculate average processing time for tickers
cat logs/log_20250709.jsonl | jq -c 'select(.event == "process_ticker_success" and .additional.processing_time != null) | .additional.processing_time' | jq -s 'add/length'
```

## Programmatic Log Analysis

You can also analyze logs programmatically using Python:

```python
import json
import pandas as pd
from pathlib import Path

# Load log file into pandas DataFrame
log_file = Path("logs/log_20250709.jsonl")
logs = []

with open(log_file, "r") as f:
    for line in f:
        logs.append(json.loads(line))

df = pd.DataFrame(logs)

# Basic analysis
print(f"Total log entries: {len(df)}")
print(df['level'].value_counts())
print(df['event'].value_counts())

# Filter for specific events
errors = df[df['level'] == 'ERROR']
download_events = df[df['event'].str.startswith('download_')]

# Time series analysis
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)
hourly_events = df.resample('H').count()['event']
```

## Log Rotation and Management

Currently, the system creates one log file per day. For long-running deployments, consider implementing log rotation and archival strategies:

1. Archive old logs to compressed storage
2. Set up log retention policies
3. Consider using a log aggregation system for production deployments

## Adding New Log Events

When adding new code that should be logged:

1. Import the logging functions:
   ```python
   from core.logger import log_info, log_warning, log_error
   ```

2. Call the appropriate function with:
   - A consistent event keyword (use snake_case)
   - A human-readable message
   - Optional ticker parameter if relevant
   - Optional additional dictionary with context data

3. For errors, include the exception:
   ```python
   try:
       # Code that might fail
   except Exception as e:
       log_error("event_name", "Human readable message", exception=e)
   ```
