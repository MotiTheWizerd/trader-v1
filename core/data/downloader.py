"""
Ticker data downloader module using yfinance.
Handles downloading historical OHLCV data for stock tickers by date.
"""
import os
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
import json
import pandas as pd
import yfinance as yf
from pathlib import Path
from sqlalchemy.orm import Session
from rich.progress import Progress

# Import database models and CRUD operations
from core.db.deps import get_db
from core.db.models.tickers_data import TickersData
from core.db.crud.tickers_data_db import insert_price, get_prices_for_ticker, delete_old_prices
from core.db.crud.tickers_signals_db import insert_signal

# Import path configuration
from core.config import get_ticker_data_path

# Default parameters
DEFAULT_INTERVAL = "5m"
DEFAULT_PERIOD = "20d"
TICKERS_FILE = Path("tickers.json")
FILE_FORMAT = "csv"  # Using CSV instead of parquet to avoid dependency issues


def load_tickers() -> List[str]:
    """
    Load ticker symbols from the tickers.json file.
    
    Returns:
        List[str]: List of ticker symbols
    """
    with open(TICKERS_FILE, "r") as f:
        data = json.load(f)
    return data.get("tickers", [])


def download_ticker_data(
    ticker: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = DEFAULT_INTERVAL,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """
    Download historical data for a specific ticker.
    
    Args:
        ticker (str): Ticker symbol
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
                      Note: For 5m interval, Yahoo Finance only provides data for the last 60 days
        period (Optional[str]): Period to download (e.g., "1d", "5d", "1mo", "3mo", "1y", "max")
                              Used if start_date and end_date are not provided
    
    Returns:
        pd.DataFrame: DataFrame containing the historical data
        
    Raises:
        ValueError: If no data is available for the specified date range
        
    Note:
        Yahoo Finance has the following limitations:
        - 1m data is available for the last 7 days
        - 5m data is available for the last 60 days
        - 1h data is available for the last 730 days
        - 1d data is available for the last ~50 years
    """
    # Check if dates are in the future
    today = datetime.now().date()
    
    if start_date is not None:
        if isinstance(start_date, str):
            start_date_obj = pd.to_datetime(start_date).date()
        else:
            start_date_obj = start_date.date()
        
        if start_date_obj > today:
            raise ValueError(f"Start date {start_date_obj} is in the future. Cannot download future data.")
    
    if end_date is not None:
        if isinstance(end_date, str):
            end_date_obj = pd.to_datetime(end_date).date()
        else:
            end_date_obj = end_date.date()
        
        if end_date_obj > today:
            # Adjust end_date to today if it's in the future
            print(f"Warning: End date {end_date_obj} is in the future. Using today's date instead.")
            end_date = today
    
    # If no dates are provided, use period
    if start_date is None and end_date is None and period is None:
        period = DEFAULT_PERIOD
    
    # Create ticker object
    ticker_obj = yf.Ticker(ticker)
    
    # Download data
    df = ticker_obj.history(
        start=start_date,
        end=end_date,
        interval=interval,
        period=period
    )
    
    # Check if data is empty
    if df.empty:
        raise ValueError(f"No data available for {ticker} with the specified date range or period.")
    
    # Reset index to make Date a column
    df = df.reset_index()
    
    # Rename columns to standard format
    df.rename(columns={
        "Date": "timestamp",
        "Datetime": "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    }, inplace=True)
    
    # Ensure timestamp is in the right format and timezone-aware
    if "timestamp" in df.columns:
        # Convert to datetime if not already
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # If timestamps are timezone-naive, localize to UTC
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize('UTC')
        # If they have timezone info, convert to UTC
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert('UTC')
    
    # Ensure all numeric columns are properly typed
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'dividends', 'stock_splits']
    for col in numeric_cols:
        if col in df.columns:
            if col == 'volume':
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    return df


def save_ticker_data(
    db: Session, ticker: str, data: pd.DataFrame, date: Optional[datetime] = None
) -> Tuple[int, int]:
    """
    Save ticker data to the database.
    
    Args:
        db: SQLAlchemy database session
        ticker (str): Ticker symbol
        data (pd.DataFrame): DataFrame containing the ticker data
        date (Optional[datetime]): Date for reference, defaults to today
    
    Returns:
        Tuple[int, int]: Number of records inserted, number of records updated
    """
    if date is None:
        date = datetime.now()
    
    inserted = 0
    updated = 0
    
    # Process each row in the DataFrame
    for _, row in data.iterrows():
        try:
            # Convert timestamp to timezone-aware datetime if needed
            timestamp = row['timestamp']
            if hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()
                
            # Ensure timestamp is timezone-aware (localize to UTC if naive)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            else:
                timestamp = timestamp.astimezone(pytz.UTC)
            
            # Prepare data dictionary with properly formatted timestamp
            price_data = {
                'ticker': ticker.upper(),
                'timestamp': timestamp,
                'open': float(row['open']) if pd.notna(row.get('open')) else 0.0,
                'high': float(row['high']) if pd.notna(row.get('high')) else 0.0,
                'low': float(row['low']) if pd.notna(row.get('low')) else 0.0,
                'close': float(row['close']) if pd.notna(row.get('close')) else 0.0,
                'volume': int(row['volume']) if pd.notna(row.get('volume')) else 0,
                'dividends': float(row.get('dividends', 0)) if pd.notna(row.get('dividends')) else 0.0,
                'stock_splits': float(row.get('stock_splits', 0)) if pd.notna(row.get('stock_splits')) else 0.0,
            }
            
            # Check if this record already exists (same ticker and timestamp)
            existing = db.query(TickersData).filter(
                TickersData.ticker == ticker.upper(),
                TickersData.timestamp == price_data['timestamp']
            ).first()
            
            if existing:
                # Update existing record
                for key, value in price_data.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                # Insert new record
                insert_price(db, price_data)
                inserted += 1
                
        except Exception as e:
            db.rollback()
            print(f"Error processing row for {ticker} at {row.get('timestamp')}: {str(e)}")
            continue
    
    return inserted, updated
    
    return inserted, updated


def download_and_save_ticker_data(
    ticker: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = DEFAULT_INTERVAL,
    period: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Download and save ticker data in one operation.
    
    Args:
        ticker (str): Ticker symbol
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
        period (Optional[str]): Period to download
    
    Returns:
        Tuple[int, int]: Number of records inserted and updated
    """
    try:
        # Download the data
        data = download_ticker_data(ticker, start_date, end_date, interval, period)
        if data.empty:
            print(f"No data downloaded for {ticker}")
            return 0, 0
            
        # Process with database session
        with get_db() as db:
            try:
                inserted, updated = save_ticker_data(db, ticker, data)
                return inserted, updated
            except Exception as e:
                print(f"Error saving data for {ticker}: {str(e)}")
                return 0, 0
                
    except Exception as e:
        print(f"Error downloading data for {ticker}: {str(e)}")
        return 0, 0


def download_all_tickers(
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = DEFAULT_INTERVAL,
    period: Optional[str] = None,
    progress: Optional['Progress'] = None,
    task_id: Optional[int] = None,
) -> Dict[str, Tuple[int, int]]:
    """
    Download data for all tickers in the tickers.json file and save to database.
    
    Args:
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
        period (Optional[str]): Period to download
        progress (Optional[Progress]): Rich Progress instance (if already in a progress context)
        task_id (Optional[int]): Task ID for the progress bar (if already in a progress context)
    
    Returns:
        Dict[str, Tuple[int, int]]: Dictionary mapping ticker symbols to (inserted, updated) counts
    """
    from rich.console import Console
    from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
    
    tickers = load_tickers()
    results = {}
    console = Console()
    
    # Only create a new progress bar if one isn't provided
    progress_bar = None
    task = None
    
    if progress is None:
        # Set up progress bar if not provided
        progress_bar = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("({task.completed}/{task.total} tickers)"),
            console=console,
            refresh_per_second=10
        )
        task = progress_bar.add_task("Downloading ticker data...", total=len(tickers))
        progress_bar.start()
    else:
        progress_bar = progress
        task = task_id
        # Initialize the task with the total number of tickers if it's a new task
        if task is None or not progress.tasks[task].started:
            task = progress.add_task("Downloading tickers...", total=len(tickers))
    
    try:
        for i, ticker in enumerate(tickers):
            if progress_bar is not None and task is not None:
                progress_bar.update(task, description=f"Processing {ticker}")
            else:
                console.print(f"Processing {ticker} ({i+1}/{len(tickers)})...")
            
            try:
                # Download and save data for this ticker
                inserted, updated = download_and_save_ticker_data(
                    ticker, start_date, end_date, interval, period
                )
                
                results[ticker] = (inserted, updated)
                if progress_bar is not None:
                    progress_bar.print(f"✓ {ticker}: {inserted} new, {updated} updated")
                else:
                    console.print(f"  ✓ {ticker}: {inserted} new, {updated} updated")
                
            except Exception as e:
                error_msg = f"✗ Error processing {ticker}: {str(e)}"
                if progress_bar is not None:
                    progress_bar.print(error_msg)
                else:
                    console.print(error_msg)
                results[ticker] = (0, 0)
            
            # Update progress if we're using a progress bar
            if progress_bar is not None and task is not None:
                progress_bar.update(task, advance=1, refresh=True)
    
    finally:
        # Only stop the progress bar if we created it
        if progress is None and progress_bar is not None:
            progress_bar.stop()
    
    # Print summary
    total_inserted = sum(r[0] for r in results.values())
    total_updated = sum(r[1] for r in results.values())
    summary = (
        f"\n✓ Downloaded data for {len([r for r in results.values() if r[0] > 0 or r[1] > 0])}/{len(tickers)} tickers\n"
        f"✓ Total: {total_inserted} new records, {total_updated} updated records"
    )
    
    if progress_bar is not None:
        progress_bar.print(summary)
    else:
        console.print(summary)
    
    return results
