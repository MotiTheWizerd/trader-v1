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
"""
import json
import os
import sys
import time
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
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
            - next_open_time (datetime): Next market open time in local timezone
    """
    # Get current time in market timezone (ET)
    now_utc = datetime.now(pytz.UTC)
    now_et = now_utc.astimezone(MARKET_TZ)
    
    # Market opening time (9:30 AM ET)
    market_open_hour = 9
    market_open_minute = 30
    
    # Market closing time (4:00 PM ET)
    market_close_hour = 16
    market_close_minute = 0
    
    # Check if it's a weekday (0 = Monday, 4 = Friday)
    is_weekday = now_et.weekday() <= 4  # Monday to Friday
    
    # Check if today is a holiday
    today_str = now_et.strftime('%Y-%m-%d')
    schedule = NYSE_CALENDAR.schedule(start_date=today_str, end_date=today_str)
    is_holiday = schedule.empty  # Empty schedule means it's a holiday
    
    # Calculate market open time for today in ET
    today_open = MARKET_TZ.localize(datetime(
        now_et.year, now_et.month, now_et.day, 
        market_open_hour, market_open_minute
    ))
    
    today_close = MARKET_TZ.localize(datetime(
        now_et.year, now_et.month, now_et.day, 
        market_close_hour, market_close_minute
    ))
    
    # Get the next market open time using pandas_market_calendars
    # Look ahead up to 10 days to find the next trading day
    end_date = (now_et + timedelta(days=10)).strftime('%Y-%m-%d')
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
    interval: str = "5m",
    period: str = "20d"
) -> Optional[str]:
    """
    Download and save a snapshot of ticker data with timestamp in filename.
    
    Args:
        ticker (str): Ticker symbol
        timestamp (datetime): Current timestamp for the snapshot
        interval (str): Data interval (e.g., "5m")
        period (str): Period to download (e.g., "20d")
        
    Returns:
        Optional[str]: Path to the saved file or None if failed
    """
    try:
        # Check if this is a new ticker or an existing one
        is_new_ticker = len(list(TICKER_DATA_DIR.glob(f"{ticker}/*.csv"))) == 0
        
        # For new tickers, download full history (20d)
        # For existing tickers, only get the latest 5 minutes
        actual_period = period if is_new_ticker else "5m"
        
        # Log what we're doing
        if is_new_ticker:
            display.console.print(f"[blue]New ticker {ticker}: Downloading full {period} history...[/blue]")
            log_info("download_start", f"Downloading full history for new ticker {ticker}", ticker=ticker, 
                    additional={"interval": interval, "period": period, "is_new_ticker": True})
        else:
            display.console.print(f"[blue]Existing ticker {ticker}: Downloading latest data...[/blue]")
            log_info("download_start", f"Downloading latest data for existing ticker {ticker}", ticker=ticker, 
                    additional={"interval": interval, "period": actual_period, "is_new_ticker": False})
        
        # Download data with appropriate period
        df = download_ticker_data(ticker, interval=interval, period=actual_period)
        
        if df is None or df.empty:
            error_msg = f"No data available for {ticker}"
            display.console.print(f"[red]{error_msg}[/red]")
            log_warning("download_empty", error_msg, ticker=ticker)
            return None
        
        # Format timestamp for filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M")
        
        # Get the output file path using the configuration
        output_file = get_ticker_data_path(ticker, timestamp_str)
        
        # Save to file
        df.to_csv(output_file)
        
        success_msg = f"Saved {ticker} data to {output_file}"
        display.console.print(f"[green]{success_msg}[/green]")
        log_info("download_complete", success_msg, ticker=ticker, 
                additional={"filepath": str(filepath), "rows": len(df)})
        
        return str(filepath)
        
    except Exception as e:
        error_msg = f"Error downloading {ticker}: {str(e)}"
        display.console.print(f"[red]{error_msg}[/red]")
        log_error("download_failed", error_msg, ticker=ticker, exception=e)
        return None


def generate_and_save_signals(
    ticker: str,
    data_file: str,
    timestamp: datetime,
    short_window: int = 5,
    long_window: int = 20,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99
) -> Optional[str]:
    """
    Generate signals from a data snapshot and save with timestamp in filename.
    Uses the core signal generation pipeline.
    
    Args:
        ticker (str): Ticker symbol
        data_file (str): Path to the data file
        timestamp (datetime): Current timestamp
        short_window (int): Short moving average window
        long_window (int): Long moving average window
        confidence_threshold (float): Minimum confidence for signals
        peak_window (int): Window for peak detection
        peak_threshold (float): Threshold for peak zone detection
        
    Returns:
        Optional[str]: Path to the saved signals file or None if failed
    """
    try:
        # Load data
        display.console.print(f"[blue]Generating signals for {ticker}...[/blue]")
        log_info("signal_generation_start", f"Generating signals for {ticker}", ticker=ticker,
                additional={"data_file": data_file, "short_window": short_window, "long_window": long_window})
        
        df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        
        if df is None or df.empty:
            error_msg = f"No data available in file {data_file}"
            display.console.print(f"[red]{error_msg}[/red]")
            log_warning("signal_data_empty", error_msg, ticker=ticker)
            return None
        
        # Format timestamp for filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M")
        date_only_str = timestamp.strftime("%Y%m%d")
        
        # Ensure the signals directory exists
        signals_dir = SIGNALS_DIR / ticker
        os.makedirs(signals_dir, exist_ok=True)
        
        # Get the data directory path (parent of ticker directory)
        data_file_path = Path(data_file)
        ticker_dir = data_file_path.parent
        data_dir = ticker_dir.parent  # This is the parent directory containing all ticker directories
        
        try:
            # Use the core signal generation function
            # Pass the data directory and let generate_ma_signals handle the file paths
            output_file = generate_ma_signals(
                ticker=ticker,
                date=date_only_str,  # Use the date string format YYYYMMDD
                short_window=short_window,
                long_window=long_window,
                data_dir=data_dir,  # Pass the data directory
                include_reasoning=True,
                confidence_threshold=confidence_threshold,
                peak_window=peak_window,
                peak_threshold=peak_threshold,
                progress=None  # No progress bar needed here
            )
            
            # The output file from generate_ma_signals will be in the signals directory
            # with format tickers/signals/TICKER/YYYYMMDD_signals.csv
            # We also want to create our timestamped version for the scheduler
            source_file = Path(output_file)
            
            if source_file.exists():
                # Read the signals file
                signals_df = pd.read_csv(source_file)
                
                # Get signal counts for display
                buy_count = signals_df["signal"].value_counts().get("BUY", 0)
                sell_count = signals_df["signal"].value_counts().get("SELL", 0)
                stay_count = signals_df["signal"].value_counts().get("STAY", 0)
                
                # Display signal counts
                display.console.print(
                    f"[green]Generated signals for {ticker}: "
                    f"[bold blue]BUY: {buy_count}[/bold blue], "
                    f"[bold red]SELL: {sell_count}[/bold red], "
                    f"[bold yellow]STAY: {stay_count}[/bold yellow][/green]"
                )
                
                # Create our timestamped version for the scheduler
                scheduler_file = signals_dir / f"{timestamp_str}_signals.csv"
                signals_df.to_csv(scheduler_file)
                
                # Log signal generation completion
                log_info("signal_generation_complete", f"Generated signals for {ticker}", ticker=ticker,
                        additional={
                            "filepath": str(scheduler_file),
                            "buy_count": buy_count,
                            "sell_count": sell_count,
                            "stay_count": stay_count,
                            "total_signals": len(signals_df)
                        })
                
                return str(scheduler_file)
            else:
                error_msg = f"No signals generated for {ticker}"
                display.console.print(f"[red]{error_msg}[/red]")
                log_warning("signal_result_empty", error_msg, ticker=ticker)
                return None
                
        finally:
            # Clean up the temporary file
            if temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                except:
                    pass
    
    except Exception as e:
        error_msg = f"Error generating signals for {ticker}: {str(e)}"
        display.console.print(f"[red]{error_msg}[/red]")
        log_error("signal_generation_failed", error_msg, ticker=ticker, exception=e)
        return None


def process_ticker(
    ticker: str,
    timestamp: datetime,
    interval: str = DEFAULT_INTERVAL,
    period: str = DEFAULT_PERIOD,
    short_window: int = 5,
    long_window: int = 20,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    retry_count: int = 3,
    retry_delay: int = 2
) -> Dict[str, Any]:
    """
    Process a single ticker: download data, generate signals, and save results.
    
    Args:
        ticker (str): Ticker symbol
        timestamp (datetime): Current timestamp
        interval (str): Data interval
        period (str): Period to download
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        confidence_threshold (float): Minimum confidence for signals
        peak_window (int): Window for peak detection
        peak_threshold (float): Threshold for peak zone detection
        retry_count (int): Number of retries for API failures
        retry_delay (int): Delay in seconds between retries
        
    Returns:
        Dict[str, Any]: Dictionary with data and signal file paths
    """
    result = {
        "ticker": ticker,
        "timestamp": timestamp,
        "status": "failed",
        "data_file": None,
        "signal_file": None,
        "error": None
    }
    
    # Skip empty ticker entries
    if not ticker or ticker.strip() == "":
        return result
    
    # Implement retry logic
    for attempt in range(retry_count):
        result["attempts"] += 1
        try:
            # Download and save data snapshot
            data_file = download_and_save_snapshot(
                ticker=ticker,
                timestamp=timestamp,
                interval=interval,
                period=period
            )
            
            if not data_file:
                if attempt < retry_count - 1:
                    retry_msg = f"Retrying download for {ticker} (attempt {attempt + 2}/{retry_count})"
                    display.console.print(f"[yellow]{retry_msg}[/yellow]")
                    log_warning("download_retry", retry_msg, ticker=ticker, 
                              additional={"attempt": attempt + 2, "max_attempts": retry_count})
                    time.sleep(retry_delay)  # Add delay between retries
                    continue
                return result
            
            result["data_file"] = data_file
            
            # Generate and save signals
            signal_file = generate_and_save_signals(
                ticker=ticker,
                data_file=data_file,
                timestamp=timestamp,
                short_window=short_window,
                long_window=long_window,
                confidence_threshold=confidence_threshold,
                peak_window=peak_window,
                peak_threshold=peak_threshold
            )
            
            if not signal_file:
                if attempt < retry_count - 1:
                    retry_msg = f"Retrying signal generation for {ticker} (attempt {attempt + 2}/{retry_count})"
                    display.console.print(f"[yellow]{retry_msg}[/yellow]")
                    log_warning("signal_generation_retry", retry_msg, ticker=ticker,
                              additional={"attempt": attempt + 2, "max_attempts": retry_count})
                    time.sleep(retry_delay)  # Add delay between retries
                    continue
                return result
            
            result["signal_file"] = signal_file
            result["status"] = "success"
            
            # Log successful processing
            log_info("process_ticker_success", f"Successfully processed ticker {ticker}", ticker=ticker,
                    additional={
                        "data_file": data_file,
                        "signal_file": signal_file,
                        "attempts_needed": attempt + 1
                    })
            
            # If we got here, we succeeded, so break the retry loop
            break
        
        except Exception as e:
            if attempt < retry_count - 1:
                retry_msg = f"Error processing {ticker}, retrying (attempt {attempt + 2}/{retry_count}): {str(e)}"
                display.console.print(f"[yellow]{retry_msg}[/yellow]")
                log_warning("process_ticker_retry", retry_msg, ticker=ticker, exception=e,
                          additional={"attempt": attempt + 2, "max_attempts": retry_count})
                time.sleep(retry_delay)  # Add delay between retries
            else:
                error_msg = f"Failed to process {ticker} after {retry_count} attempts: {str(e)}"
                display.show_ticker_error(ticker, e)
                log_error("process_ticker_failed", error_msg, ticker=ticker, exception=e)
                result["error"] = str(e)
    
    return result


def scheduler_job(force: bool = False) -> None:
    """
    Main scheduler job function that runs at scheduled intervals.
    
    Args:
        force (bool, optional): Force execution even if market is closed. Defaults to False.
    """
    # Get current timestamp
    now = datetime.now()
    
    # Log job start
    log_info("scheduler_job_start", f"Starting scheduler job at {now.isoformat()}", 
            additional={"force": force})
    
    # Check if market is open
    is_open, next_open = is_market_open()
    
    if not is_open and not force:
        market_closed_msg = f"Market closed. Next open: {next_open.isoformat()}"
        display.show_market_closed(now, next_open)
        log_info("market_closed", market_closed_msg, 
                additional={"next_open": next_open.isoformat()})
        return
    
    # Ensure directories exist
    ensure_directories()
    
    # Load tickers
    tickers = load_tickers()
    
    # Show job start message
    display.show_job_start(now, len(tickers))
    log_info("processing_tickers", f"Processing {len(tickers)} tickers", 
            additional={"ticker_count": len(tickers), "tickers": tickers})
    
    # Process each ticker
    results = []
    
    with display.progress_context() as progress:
        task = progress.add_task("Processing tickers...", total=len(tickers))
        
        for ticker in tickers:
            result = process_ticker(ticker, now)
            results.append(result)
            progress.update(task, advance=1)
    
    # Save signal metadata
    metadata_file = save_signal_metadata(results, now)
    
    # Show job results
    display.show_job_results(results, now)
    
    # Display signal summary
    display_signal_summary(metadata_file, display.console)
    
    # Log job completion
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count
    
    log_info("scheduler_job_complete", f"Completed scheduler job at {datetime.now().isoformat()}", 
            additional={
                "total_tickers": len(results),
                "success_count": success_count,
                "failed_count": failed_count,
                "metadata_file": metadata_file if metadata_file else None
            })


def run_scheduler() -> None:
    """
    Run the scheduler with a job that executes every 5 minutes.
    """
    # Ensure all directories exist
    ensure_directories()
    
    # Log scheduler startup
    log_info("scheduler_startup", "Starting trading signal scheduler")
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Add job to run every 5 minutes
    scheduler.add_job(
        scheduler_job,
        trigger=CronTrigger(minute='*/5'),  # Run every 5 minutes
        id='trading_signal_job',
        name='Trading Signal Job',
        replace_existing=True
    )
    
    # Show startup message
    display.show_startup_message()
    
    # Run the scheduler
    try:
        # Run the job once immediately
        scheduler_job()
        
        # Start the scheduler
        scheduler.start()
    except KeyboardInterrupt:
        shutdown_msg = "Scheduler stopped by user"
        display.console.print(f"[bold red]{shutdown_msg}[/bold red]")
        log_info("scheduler_shutdown", shutdown_msg)
    except Exception as e:
        error_msg = f"Scheduler error: {str(e)}"
        display.show_error(error_msg)
        log_error("scheduler_error", error_msg, exception=e)


if __name__ == "__main__":
    run_scheduler()
