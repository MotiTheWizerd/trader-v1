# Trading System Dashboard Guide

## Overview

The Trading System Dashboard is the primary interface for interacting with the trading system. It provides a user-friendly command-line interface built with the Rich library, offering real-time feedback, progress tracking, and a clean, organized way to manage your trading data and signals.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Main Menu](#main-menu)
3. [Features in Detail](#features-in-detail)
   - [1. Clear Database](#1-clear-database)
   - [2. Run Complete Pipeline](#2-run-complete-pipeline)
   - [3. Regenerate Signals](#3-regenerate-signals)
   - [4. Exit](#4-exit)
4. [Progress Tracking](#progress-tracking)
5. [Error Handling](#error-handling)
6. [Keyboard Shortcuts](#keyboard-shortcuts)
7. [Troubleshooting](#troubleshooting)

## Getting Started

To launch the dashboard, run the following command in your terminal:

```bash
poetry run python dashboard.py
```

Or directly through the module:

```bash
poetry run python -m scripts.dashboard
```

## Main Menu

When you start the dashboard, you'll see the following menu:

```
╭──────────────────────────╮
│ Trading System Dashboard │
╰──────────────────────────╯
  1. Clear Database           clean-data     Remove all data from tickers_data and tickers_signals tables
  2. Run Complete Pipeline    run-pipeline   Download data and generate signals
  3. Regenerate Signals       regenerate     Regenerate signals with different settings
  4. Exit                     exit           Exit the dashboard
```

## Features in Detail

### 1. Clear Database

**Option 1** in the main menu allows you to clear all data from the system.

**Workflow:**
1. Select option 1
2. Read and acknowledge the warning message
3. Type `YES` (in uppercase) to confirm deletion or anything else to cancel
4. The system will display progress as it clears each table
5. A confirmation message appears when complete

**Note:** This action cannot be undone. All price data and signals will be permanently deleted.

### 2. Run Complete Pipeline

**Option 2** initiates the data download process for all configured tickers.

**Workflow:**
1. Select option 2
2. The system displays a progress bar showing:
   - Current ticker being processed
   - Number of tickers completed/total
   - Overall progress percentage
3. For each ticker, it shows:
   - Download progress
   - Number of new records added
   - Number of records updated
4. A summary is displayed upon completion

**Technical Details:**
- Downloads 20 days of historical data by default
- Uses 5-minute intervals for intraday data
- Stores data in the PostgreSQL database
- Skips already downloaded data to avoid duplicates

### 3. Regenerate Signals

**Option 3** allows you to regenerate trading signals from existing price data.

**Workflow:**
1. Select option 3
2. The system will prompt for configuration options:
   - Moving average windows
   - Confidence threshold
   - Peak detection settings
3. Progress is shown for each ticker being processed
4. A summary of generated signals is displayed

### 4. Exit

**Option 4** gracefully exits the application.

## Progress Tracking

The dashboard provides real-time progress tracking through:

1. **Progress Bars**
   - Shows completion percentage
   - Displays elapsed and estimated remaining time
   - Updates in real-time

2. **Status Messages**
   - Current operation being performed
   - Success/failure indicators
   - Summary statistics

3. **Color Coding**
   - Green: Success/completion
   - Yellow: Warnings/non-critical information
   - Red: Errors/important warnings

## Error Handling

The dashboard includes comprehensive error handling:

1. **Network Issues**
   - Automatic retries for failed downloads
   - Clear error messages with suggested actions

2. **Database Errors**
   - Connection issues are caught and reported
   - Transaction rollback on failures

3. **Input Validation**
   - Validates all user input
   - Provides clear error messages for invalid input

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ↑/↓ | Navigate menu options |
| Enter | Select option |
| 1-4 | Directly select menu option |
| q/Q | Exit (when available) |
| CTRL+C | Force quit application |

## Troubleshooting

### Common Issues

1. **No Data Downloaded**
   - Check internet connection
   - Verify ticker symbols in `tickers.json`
   - Ensure market is open for intraday data

2. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check `.env` file for correct credentials
   - Ensure user has proper permissions

3. **Progress Bar Not Updating**
   - This is usually just a display issue
   - The process is likely still running in the background
   - Check logs for actual progress

### Viewing Logs

Detailed logs are available in the `logs/` directory:

```bash
# View the latest log file
tail -f logs/log_$(date +%Y%m%d).jsonl
```

## Advanced Usage

### Command Line Arguments

The dashboard supports direct command execution:

```bash
# Run data download directly
poetry run python -m scripts.dashboard run-pipeline

# Regenerate signals with custom parameters
poetry run python -m scripts.dashboard regenerate-signals --short-window 5 --long-window 20

# Clear database (requires confirmation)
poetry run python -m scripts.dashboard clean-data --force
```

### Configuration

Customize the dashboard behavior by modifying:
- `config/settings.py` for application settings
- `.env` for environment-specific configurations
- `tickers.json` for the list of tickers to process

## Best Practices

1. Always check the logs if something unexpected occurs
2. Use the dashboard during market hours for the most up-to-date data
3. Regularly back up your database
4. Monitor disk space when downloading large amounts of historical data

## Support

For additional help, please refer to:
- [Pipeline Workflow Documentation](./pipeline_workflow.md)
- [Quick Reference Guide](./quick_reference.md)
- [Project README](../README.md)
