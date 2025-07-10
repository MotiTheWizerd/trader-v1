"""
Real-time scheduler for stock signal prediction system.

This module uses APScheduler to run data download and signal generation jobs
every 5 minutes during market hours with structured JSON logging.

Each job:
1. Downloads OHLCV data using yfinance:
   - For new tickers: Full 20-day history (5-minute interval)
   - For existing tickers: Only latest 5-minute data (optimization)
2. Saves a snapshot to tickers/data/<TICKER>/<YYYYMMdd_HHmm>.csv
3. Generates signal predictions (BUY/SELL/STAY)
4. Saves signals to tickers/signals/<TICKER>/<YYYYMMdd_HHmm>_signals.csv
5. Logs all operations to logs/log_<YYYYMMDD>.jsonl with structured data

Features:
- Market hours awareness (only runs during NYSE trading hours)
- Holiday calendar integration (skips non-trading days)
- Structured JSON logging for analytics and monitoring
- Optimized data downloads (full history for new tickers, incremental for existing)
- Retry logic for network failures
- Rich terminal UI with progress indicators
- Graceful shutdown handling with Ctrl+C
"""
import json
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from signal import SIGINT, SIGTERM
from typing import Any, Dict, List, Optional, Tuple

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import time
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any

# Import pytz for timezone handling
import pytz
# Import pandas_market_calendars for holiday awareness
import pandas_market_calendars as mcal

import pandas as pd
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Import configuration
from core.config import (
    PROJECT_ROOT,
    TICKER_DATA_DIR,
    SIGNALS_DIR,
    LOGS_DIR,
    get_ticker_data_path,
    get_signal_file_path,
    get_log_file_path,
    console  # Use the configured console
)

# Add project root to path for absolute imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import project modules

# Default configuration
DEFAULT_INTERVAL = "5m"  # 5-minute intervals
DEFAULT_PERIOD = "20d"    # 20 days of historical data

from core.data.downloader import load_tickers, download_ticker_data
from core.signals.moving_average import generate_ma_signals
from core.logger import log_info, log_warning, log_error
from scripts.scheduler_metadata import save_signal_metadata, display_signal_summary
from ui.scheduler_display import display

# We'll use the display singleton from ui.scheduler_display instead of creating a console here

# Constants
MARKET_TZ = pytz.timezone('US/Eastern')

# Market hours (US Eastern Time)
MARKET_OPEN = dt_time(9, 30)  # 9:30 AM ET
MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET

# NYSE calendar for holiday checks
NYSE_CALENDAR = mcal.get_calendar('NYSE')


def ensure_directories():
    """Ensure all required directories exist.
    
    Note: This function is kept for backward compatibility but directories
    are now managed by the core.config module.
    """
    # Directories are created automatically by core.config
    console.print("[green]✓ All required directories are managed by core.config")


def is_market_open() -> Tuple[bool, datetime]:
    """
    Check if the US stock market is currently open and calculate next open time.
    
    Uses timezone-aware datetime objects to properly handle market hours in ET.
    Accounts for holidays using pandas_market_calendars.
    
    Returns:
        Tuple[bool, datetime]: (is_open, next_open_time)
            - is_open (bool): True if market is open, False otherwise
            - next_open_time (datetime): Next market open time in ET timezone
    """
    # Get current time in ET
    now_et = datetime.now(MARKET_TZ)
    
    # Create time objects for market hours (ET)
    market_open_time = dt_time(9, 30)  # 9:30 AM ET
    market_close_time = dt_time(16, 0)  # 4:00 PM ET
    
    # Check if it's a weekday (0 = Monday, 4 = Friday)
    is_weekday = now_et.weekday() <= 4  # Monday to Friday
    
    # Check if today is a holiday
    today_str = now_et.strftime('%Y-%m-%d')
    schedule = NYSE_CALENDAR.schedule(start_date=today_str, end_date=today_str)
    is_holiday = schedule.empty  # Empty schedule means it's a holiday
    
    # Get current time in ET timezone
    current_time_et = now_et.timetz()
    
    # Check if market is open now
    is_open = False
    if is_weekday and not is_holiday:
        if market_open_time <= current_time_et < market_close_time:
            is_open = True
    
    # Calculate next market open time
    next_open = None
    
    if is_weekday and not is_holiday:
        # If today is a trading day
        if current_time_et < market_open_time:
            # Market opens later today
            next_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        elif current_time_et < market_close_time:
            # Market is open now, next open is tomorrow or next trading day
            next_day = now_et + timedelta(days=1)
            next_open = get_next_market_open(next_day)
        else:
            # Market is closed for today, find next trading day
            next_day = now_et + timedelta(days=1)
            next_open = get_next_market_open(next_day)
    else:
        # Today is not a trading day, find next trading day
        next_day = now_et + timedelta(days=1)
        next_open = get_next_market_open(next_day)
    
    return is_open, next_open

def get_next_market_open(start_date: datetime) -> datetime:
    """Find the next market open date starting from start_date."""
    for days_ahead in range(8):  # Look ahead up to 7 days
        check_date = start_date + timedelta(days=days_ahead)
        check_date_str = check_date.strftime('%Y-%m-%d')
        schedule = NYSE_CALENDAR.schedule(start_date=check_date_str, end_date=check_date_str)
        if not schedule.empty:  # If it's a trading day
            return MARKET_TZ.localize(datetime(
                check_date.year, check_date.month, check_date.day,
                9, 30  # 9:30 AM ET
            ))
    return start_date.replace(hour=9, minute=30, second=0, microsecond=0)
    future_schedule = NYSE_CALENDAR.schedule(start_date=today_str, end_date=end_date)
    
    if is_holiday or not is_weekday or now_et >= today_close:
        # Market is closed today (holiday or weekend) or it's after closing time
        # Find the next market open date
        if not future_schedule.empty:
            next_market_day = future_schedule.iloc[0]
            # Parse the market_open time which is already a timestamp
            market_open_time = pd.to_datetime(next_market_day['market_open'])
            # Create a datetime in ET timezone
            next_open_time = MARKET_TZ.localize(
                datetime(market_open_time.year, market_open_time.month, market_open_time.day,
                        market_open_time.hour, market_open_time.minute, market_open_time.second)
            )
        else:
            # Fallback if no schedule found (unlikely)
            if is_weekday:
                # Today is a weekday but closed (holiday or after hours)
                next_day = now_et + timedelta(days=1)
                # If tomorrow is weekend, jump to Monday
                if next_day.weekday() > 4:  # Saturday or Sunday
                    days_until_monday = 7 - next_day.weekday()
                    next_day = now_et + timedelta(days=days_until_monday)
            else:
                # Weekend - calculate next Monday
                days_until_monday = 1 if now_et.weekday() == 6 else 7 - now_et.weekday()
                next_day = now_et + timedelta(days=days_until_monday)
            
            next_open_time = MARKET_TZ.localize(datetime(
                next_day.year, next_day.month, next_day.day, 
                market_open_hour, market_open_minute
            ))
    elif now_et < today_open:
        # Market opens later today
        next_open_time = today_open
    else:
        # Market is currently open
        next_open_time = today_open  # Already open
    
    # Check if market is currently open
    is_open = False
    if is_weekday and not is_holiday:
        # Check if it's between opening and closing times
        if today_open <= now_et < today_close:
            is_open = True
    
    # Return the next_open_time in the market timezone (ET)
    # No need to convert to local timezone which can cause timezone issues
    return is_open, next_open_time


def download_and_save_snapshot(
    ticker: str,
    timestamp: datetime,
    interval: str = "1m",
    period: str = None  # Kept for backward compatibility, not used
) -> Optional[Dict[str, Any]]:
    """
    Download and save only new ticker data to the database.
    
    Args:
        ticker (str): Ticker symbol
        timestamp (datetime): Current timestamp for the snapshot
        interval (str): Data interval (e.g., "1m")
        period (str): Kept for backward compatibility, not used
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary with download results or None if failed
        
    Note:
        This function will only download data that is newer than the most recent
        record in the database for the given ticker. For the first run, it will
        fetch the last day of data.
    """
    try:
        from core.db.deps import get_db
        from core.db.crud.tickers_data_db import save_ticker_data
        
        # Log what we're doing
        display.console.print(f"[blue]Downloading {ticker} data...[/blue]")
        log_info("download_start", f"Downloading data for ticker {ticker}", ticker=ticker, 
                additional={"interval": interval, "period": period})
        
        # Download data
        df = download_ticker_data(ticker, interval=interval, period=period)
        
        if df is None or df.empty:
            error_msg = f"No data available for {ticker}"
            display.console.print(f"[red]{error_msg}[/red]")
            log_warning("download_empty", error_msg, ticker=ticker)
            return None
        
        # Save to database
        with get_db() as db:
            saved_count = save_ticker_data(db, ticker, df)
        
        success_msg = f"Saved {saved_count} records for {ticker} to database"
        display.console.print(f"[green]{success_msg}[/green]")
        log_info("download_complete", success_msg, ticker=ticker, 
                additional={"records_saved": saved_count})
        
        # Get the number of rows in the DataFrame
        row_count = len(df) if df is not None else 0
        
        return {
            "ticker": ticker,
            "records_saved": saved_count,
            "row_count": row_count,  # Add row count to the result
            "timestamp": timestamp.isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error downloading {ticker}: {str(e)}"
        display.console.print(f"[red]{error_msg}[/red]")
        log_error("download_failed", error_msg, ticker=ticker, exception=e)
        return None


def generate_and_save_signals(
    ticker: str,
    timestamp: datetime,
    short_window: int = 5,
    long_window: int = 20,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99
) -> Optional[Dict[str, Any]]:
    """
    Generate signals from database data and save to the database.
    
    Args:
        ticker (str): Ticker symbol
        timestamp (datetime): Current timestamp
        short_window (int): Short moving average window
        long_window (int): Long moving average window
        confidence_threshold (float): Minimum confidence for signals
        peak_window (int): Window for peak detection
        peak_threshold (float): Threshold for peak zone detection
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary with signal generation results or None if failed
    """
    try:
        from core.db.deps import get_db
        from core.db.crud.tickers_data_db import get_prices_for_ticker
        from core.db.crud.tickers_signals_db import save_signals_batch
        from core.signals.moving_average import generate_ma_signals
        
        display.console.print(f"[blue]Generating signals for {ticker}...[/blue]")
        log_info("signal_generation_start", f"Generating signals for {ticker}", ticker=ticker)
        
        # Get data from database
        with get_db() as db:
            prices = get_prices_for_ticker(db, ticker)
            
            if not prices:
                error_msg = f"No price data found for {ticker} in database"
                display.console.print(f"[yellow]{error_msg}[/yellow]")
                log_warning("no_price_data", error_msg, ticker=ticker)
                return None
                
            # Convert to DataFrame
            data = []
            for p in prices:
                data.append({
                    'timestamp': p.timestamp,
                    'open': p.open,
                    'high': p.high,
                    'low': p.low,
                    'close': p.close,
                    'volume': p.volume,
                    'ticker': ticker
                })
            
            df = pd.DataFrame(data)
            
            # Ensure timestamp is timezone-naive
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
        
        # Generate signals
        signals = generate_ma_signals(
            ticker=ticker,
            date=timestamp,
            short_window=short_window,
            long_window=long_window,
            confidence_threshold=confidence_threshold,
            peak_window=peak_window,
            peak_threshold=peak_threshold,
            df=df  # Pass the DataFrame directly
        )
        
        if signals is None or signals.empty:
            error_msg = f"No signals generated for {ticker}"
            display.console.print(f"[yellow]{error_msg}[/yellow]")
            log_warning("no_signals", error_msg, ticker=ticker)
            return None
        
        # Save signals to database
        signals_list = []
        for _, row in signals.iterrows():
            signals_list.append({
                'ticker': ticker,
                'timestamp': row['timestamp'],
                'signal': row['signal'],
                'confidence': float(row.get('confidence', 0.0)),
                'reasoning': str(row.get('reasoning', '')),
                'created_at': datetime.utcnow()
            })
        
        with get_db() as db:
            saved_count = save_signals_batch(db, signals_list)
        
        # Get signal counts for display
        buy_count = signals["signal"].value_counts().get("BUY", 0)
        sell_count = signals["signal"].value_counts().get("SELL", 0)
        stay_count = signals["signal"].value_counts().get("STAY", 0)
        
        # Display signal counts
        display.console.print(
            f"[green]Generated signals for {ticker}: "
            f"[bold blue]BUY: {buy_count}[/bold blue], "
            f"[bold red]SELL: {sell_count}[/bold red], "
            f"[bold yellow]STAY: {stay_count}[/bold yellow][/green]"
        )
        
        # Log signal generation completion
        success_msg = f"Saved {saved_count} signals for {ticker} to database"
        display.console.print(f"[green]{success_msg}[/green]")
        log_info("signals_saved", success_msg, ticker=ticker, 
                additional={
                    "signal_count": saved_count,
                    "buy_count": buy_count,
                    "sell_count": sell_count,
                    "stay_count": stay_count
                })
        
        return {
            'ticker': ticker,
            'signal_count': saved_count,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'stay_count': stay_count,
            'timestamp': timestamp.isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error generating signals for {ticker}: {str(e)}"
        display.console.print(f"[red]{error_msg}[/red]")
        log_error("signal_generation_failed", error_msg, ticker=ticker, exception=e, exc_info=True)
        return None


def process_ticker(
    ticker: str,
    timestamp: datetime,
    interval: str = "5m",
    period: str = "20d",
    retry_count: int = 3,
    retry_delay: int = 2
) -> Dict[str, Any]:
    """
    Process a single ticker: download and save price data.
    
    Args:
        ticker (str): Ticker symbol
        timestamp (datetime): Current timestamp
        interval (str): Data interval
        period (str): Period to download
        retry_count (int): Number of retries for API failures
        retry_delay (int): Delay in seconds between retries
        
    Returns:
        Dict[str, Any]: Dictionary with data file path and status
    """
    # Initialize result dictionary with expected fields for display
    result = {
        "ticker": ticker,
        "status": "failed",  # Will be updated to "success" if successful
        "attempts": 1,       # Default to 1 attempt
        "data_file": None,
        "signal_file": None,  # Keep for compatibility with display
        "error": None
    }
    
    try:
        # Download and save data
        data_result = download_and_save_snapshot(
            ticker=ticker,
            timestamp=timestamp,
            interval=interval,
            period=period
        )
        
        if not data_result or "error" in data_result:
            error_msg = data_result.get("error", "Unknown error downloading data") if data_result else "No data returned"
            result["error"] = error_msg
            return result
            
        # Update result for successful download
        result.update({
            "status": "success",
            "data_file": data_result.get("data_file"),
            "row_count": data_result.get("row_count", 0),  # Add row count to result
            "records_saved": data_result.get("records_saved", 0)  # Also include records_saved for completeness
        })
        
    except Exception as e:
        error_msg = f"Error processing {ticker}: {str(e)}"
        log_error("ticker_processing_error", error_msg, ticker=ticker, error=str(e))
        result["error"] = error_msg
    
    return result


def scheduler_job(force: bool = False) -> None:
    """
    Main scheduler job function that runs at scheduled intervals.
    Focuses only on data fetching, not signal generation.
    
    Args:
        force (bool, optional): Force execution even if market is closed. Defaults to False.
    """
    # Get current time in market timezone
    now = datetime.now(pytz.UTC)
    market_time = now.astimezone(MARKET_TZ)
    
    # Skip if outside market hours and not forced
    if not force and not is_market_open():
        log_info("market_closed", "Skipping job - market is closed")
        return
    
    # Load tickers
    tickers = load_tickers()
    if not tickers:
        log_warning("no_tickers", "No tickers found to process")
        return
    
    # Show job start
    display.show_job_start(now, len(tickers))
    
    # Track results
    results = []
    
    # Process each ticker (data fetching only)
    with display.progress_context() as progress:
        task = progress.add_task("Processing tickers...", total=len(tickers))
        for ticker in tickers:
            result = process_ticker(
                ticker=ticker,
                timestamp=now,
                interval="5m",
                period="20d"
            )
            results.append(result)
            progress.update(task, advance=1)
    
    # Show job results
    display.show_job_results(results, now)
    
    # Log completion
    success_count = sum(1 for r in results if r.get("status") == "success")
    total_count = len(results)
    
    # Log data fetch completion
    log_info(
        "data_fetch_run_complete",
        f"Completed fetching data for {success_count}/{total_count} tickers",
        additional={
            "success_count": success_count,
            "total_count": total_count
        }
    )
    
    # Log job completion
    log_info(
        "scheduler_job_complete", 
        f"Completed scheduler job at {datetime.now(pytz.UTC).isoformat()}",
        additional={
            "total_tickers": total_count,
            "successful_tickers": success_count,
            "failed_count": total_count - success_count,
            "metadata_file": None
        }
    )


def run_scheduler() -> None:
    """
    Run the scheduler with a job that executes every minute.
    Handles graceful shutdown on keyboard interrupt.
    """
    # Ensure all directories exist
    ensure_directories()
    
    # Initialize logging
    log_info("scheduler_startup", "Starting trading signal scheduler")
    
    # Configure scheduler
    scheduler = BlockingScheduler(timezone=str(MARKET_TZ))
    
    # Add job to run every minute during market hours
    scheduler.add_job(
        scheduler_job,
        'cron',
        minute='*',  # Every minute
        timezone=MARKET_TZ,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300  # 5 minutes grace period
    )
    
    # Run the first job immediately
    scheduler.add_job(
        scheduler_job,
        'date',
        run_date=datetime.now(pytz.UTC) + timedelta(seconds=2),  # Small delay to ensure scheduler is ready
        timezone=MARKET_TZ
    )
    
    class SchedulerShutdownHandler:
        """Handle graceful shutdown of the scheduler."""
        def __init__(self, sched):
            self.is_shutting_down = False
            self.scheduler = sched
        
        def __call__(self, signum, frame):
            """Handle shutdown signals gracefully."""
            if self.is_shutting_down:
                # Force exit if we get a second interrupt
                display.console.print("\n[bold red]Force shutdown requested...[/bold red]")
                sys.exit(1)
                
            self.is_shutting_down = True
            display.console.print("\n[bold yellow]Shutting down scheduler, please wait...[/bold yellow]")
            
            try:
                self.scheduler.shutdown(wait=True)
                display.console.print("[green]✓ Scheduler stopped cleanly[/green]")
            except Exception as e:
                display.console.print(f"[red]Error during shutdown: {str(e)}[/red]")
            
            sys.exit(0)
    
    # Create shutdown handler instance with scheduler reference
    shutdown_handler = SchedulerShutdownHandler(scheduler)
    
    # Register signal handlers
    signal.signal(SIGINT, shutdown_handler)   # Handle Ctrl+C
    signal.signal(SIGTERM, shutdown_handler)  # Handle systemd/other process managers
    
    try:
        # Show startup message
        display.show_startup_message()
        display.console.print("Running jobs every 1 minute during market hours")
        display.console.print("Press Ctrl+C to stop the scheduler\n")
        
        # Run the first job immediately
        scheduler_job()
        
        # Run the scheduler
        scheduler.start()
        
    except Exception as e:
        display.console.print(f"\n[bold red]Scheduler error: {str(e)}[/bold red]")
        try:
            scheduler.shutdown()
        except Exception as shutdown_error:
            display.console.print(f"[red]Error during shutdown: {str(shutdown_error)}[/red]")
        raise

if __name__ == "__main__":
    run_scheduler()
