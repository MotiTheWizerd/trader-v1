"""
Data management for the scheduler.

This module handles downloading, processing, and saving market data.
"""
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import pytz
import yfinance as yf
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.db.deps import get_db
from core.db.models.tickers_data import TickersData
from core.scheduler.utils import file_ops
from core.scheduler.market_hours import is_market_open

# Initialize rich console
console = Console()

# Timezone for market data (Eastern Time)
NYC = pytz.timezone("America/New_York")


def download_historical_data(
    ticker: str,
    period: str = "20d",
    interval: str = "5m",
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> Optional[pd.DataFrame]:
    """Download historical market data for a ticker.
    
    Args:
        ticker: Ticker symbol
        period: Data period to download (e.g., "1d", "5d", "1mo", "3mo", "1y", "max")
        interval: Data interval (e.g., "1m", "5m", "15m", "1h", "1d")
        progress: Rich Progress instance for progress tracking
        task_id: Task ID for progress updates
        
    Returns:
        Optional[pd.DataFrame]: Downloaded data, or None if download failed
    """
    if progress and task_id is not None:
        progress.update(
            task_id,
            description=f"[cyan]Downloading {ticker} data...",
            total=100,
            completed=0
        )
    
    try:
        # Download data using yfinance
        try:
            # Download with minimal processing first
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                threads=False,      # Avoid thread-related issues
                auto_adjust=False,  # Don't auto-adjust, we'll handle it
                prepost=False,      # Don't include pre/post market data
                actions=False,      # Don't include dividends and stock splits in the main dataframe
            )
            
            # Debug: Print the raw data we got back
            console.log(f"[yellow]Raw data columns for {ticker}:", list(data.columns))
            
            # Defensive checks
            if not isinstance(data, pd.DataFrame):
                raise ValueError(f"Downloaded data is not a DataFrame: {type(data)}")
                
            # If we got an empty DataFrame, try with a different period
            if data.empty:
                console.log(f"[yellow]No data returned for {ticker} with period={period}, trying with period='1d'")
                return download_historical_data(ticker, period='1d', interval=interval, progress=progress, task_id=task_id)
                
            # Handle MultiIndex columns (which happens with multiple tickers)
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten the multi-index and remove any empty strings
                data.columns = ['_'.join(str(c).lower() for c in col if c).strip('_') 
                              for col in data.columns.values]
                
                # Remove the ticker suffix from column names since we already have the ticker
                ticker_lower = ticker.lower()
                data.columns = [col.replace(f'_{ticker_lower}', '') for col in data.columns]
            
            # Normalize column names (convert to lowercase and strip whitespace)
            data.columns = [str(col).lower().strip() for col in data.columns]
            
            # Remove duplicate columns if any
            if data.columns.duplicated().any():
                data = data.loc[:, ~data.columns.duplicated()]
                
            # Reset index if it's a MultiIndex or if it's a DatetimeIndex
            if isinstance(data.index, (pd.MultiIndex, pd.DatetimeIndex)):
                data = data.reset_index()
                
            # Check if we have the required data
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            available_columns = [col.lower() for col in data.columns]
            
            # See which required columns we have
            found_columns = [col for col in required_columns if col in available_columns]
            
            if not found_columns:
                raise ValueError(f"No valid price data columns found. Available columns: {list(data.columns)}")
                
            # If we're missing some columns, log a warning but continue with what we have
            missing_columns = [col for col in required_columns if col not in available_columns]
            if missing_columns:
                console.log(f"[yellow]Warning: Missing columns for {ticker}: {missing_columns}. Available: {available_columns}")
            
        except Exception as e:
            console.log(f"[red]Error downloading {ticker} data: {e}")
            if 'data' in locals() and not data.empty:
                console.log(f"[yellow]Data columns: {list(data.columns)}")
                console.log(f"[yellow]Data sample:\n{data.head()}")
            return None
        
        if data.empty:
            console.log(f"[yellow]No data returned for {ticker}")
            return None
        
        # Reset index to make Datetime a column
        data = data.reset_index()
        
        # At this point, columns are already in lowercase and standardized
        # Create a mapping of possible source columns to our target columns
        column_mapping = {
            # Timestamp columns
            'date': 'timestamp',
            'datetime': 'timestamp',
            # OHLCV columns
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            # Additional columns
            'adj close': 'adj_close',
            'dividends': 'dividends',
            'stock splits': 'stock_splits'
        }
        
        # Find which columns we have that match our mapping
        available_columns = {}
        for src_col in data.columns:
            src_col_lower = str(src_col).lower().strip()
            if src_col_lower in column_mapping:
                target_col = column_mapping[src_col_lower]
                available_columns[target_col] = src_col
        
        # If we don't have the basic OHLCV columns, log an error and return None
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in available_columns]
        
        if missing_columns:
            console.log(f"[red]Missing required columns for {ticker}: {missing_columns}")
            console.log(f"[yellow]Available columns: {list(data.columns)}")
            return None
        
        # Rename the columns we want to keep
        data = data.rename(columns={v: k for k, v in available_columns.items()})
        
        # Keep only the columns we've mapped
        data = data[list(available_columns.keys())]
        
        # Add ticker column
        data['ticker'] = ticker.upper()
        
        # Ensure timestamp is timezone-aware (UTC)
        if 'timestamp' in data.columns and not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
            data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        if 'timestamp' in data.columns and data['timestamp'].dt.tz is None:
            # Assume UTC if no timezone is set
            data['timestamp'] = data['timestamp'].dt.tz_localize('UTC')
        
        if progress and task_id is not None:
            progress.update(task_id, completed=100)
        
        return data
    
    except Exception as e:
        console.log(f"[red]Error downloading {ticker} data: {e}")
        if progress and task_id is not None:
            progress.update(task_id, visible=False)
        return None


def save_to_database(
    df: pd.DataFrame,
    ticker: str,
    timestamp: datetime,
    session: Any
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """Save price data to the database.
    
    Args:
        df: DataFrame containing price data
        ticker: Ticker symbol
        timestamp: Current timestamp for the snapshot
        session: Database session
        
    Returns:
        Tuple[int, int, List[Dict[str, Any]]]: 
            - Number of new records inserted
            - Number of existing records skipped
            - List of errors that occurred
    """
    if df.empty:
        return 0, 0, []
    
    inserted = 0
    skipped = 0
    errors = []
    
    # Ensure timestamp is timezone-aware (UTC)
    if timestamp.tzinfo is None:
        timestamp = pytz.utc.localize(timestamp)
    
    try:
        # Process each row
        for _, row in df.iterrows():
            try:
                # Check if record already exists
                exists = session.query(TickersData).filter_by(
                    ticker=ticker.upper(),
                    timestamp=row['timestamp']
                ).first()
                
                if exists:
                    skipped += 1
                    continue
                
                # Create new price data record
                price_data = TickersData(
                    ticker=ticker.upper(),
                    timestamp=row['timestamp'],
                    open=row.get('open'),
                    high=row.get('high'),
                    low=row.get('low'),
                    close=row.get('close'),
                    volume=int(row.get('volume', 0)),
                    dividends=row.get('dividends', 0.0),
                    stock_splits=row.get('stock_splits', 0.0)
                )
                
                session.add(price_data)
                inserted += 1
                
                # Commit in batches to avoid large transactions
                if inserted % 100 == 0:
                    session.commit()
            
            except Exception as e:
                errors.append({
                    'ticker': ticker,
                    'timestamp': row.get('timestamp'),
                    'error': str(e)
                })
        
        # Final commit for any remaining records
        session.commit()
        
        return inserted, skipped, errors
    
    except Exception as e:
        session.rollback()
        errors.append({
            'ticker': ticker,
            'timestamp': timestamp.isoformat(),
            'error': f"Database error: {str(e)}"
        })
        return inserted, skipped, errors


def process_ticker(
    ticker: str,
    timestamp: Optional[datetime] = None,
    interval: str = "5m",
    period: str = "20d",
    retry_count: int = 3,
    retry_delay: int = 2,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> Dict[str, Any]:
    """Process a single ticker: download data and save to database.
    
    Args:
        ticker: Ticker symbol
        timestamp: Timestamp for the snapshot (defaults to now)
        interval: Data interval (e.g., "5m", "1h", "1d")
        period: Period of data to download (e.g., "1d", "5d", "1mo")
        retry_count: Number of retry attempts for failed downloads
        retry_delay: Delay between retry attempts in seconds
        progress: Rich Progress instance for progress tracking
        task_id: Task ID for progress updates
        
    Returns:
        Dict[str, Any]: Processing results
    """
    if timestamp is None:
        timestamp = datetime.now(pytz.utc)
    
    result = {
        'ticker': ticker.upper(),
        'timestamp': timestamp.isoformat(),
        'success': False,
        'records_inserted': 0,
        'records_skipped': 0,
        'errors': [],
        'retries': 0
    }
    
    # Track if we're in a retry loop
    attempt = 0
    
    while attempt <= retry_count:
        attempt += 1
        
        try:
            # Download data
            df = download_historical_data(
                ticker=ticker,
                period=period,
                interval=interval,
                progress=progress,
                task_id=task_id
            )
            
            if df is None or df.empty:
                result['errors'].append({
                    'attempt': attempt,
                    'error': 'No data returned from API'
                })
                continue
            
            # Save to database
            with get_db() as session:
                inserted, skipped, errors = save_to_database(
                    df=df,
                    ticker=ticker,
                    timestamp=timestamp,
                    session=session
                )
                
                result.update({
                    'success': True,
                    'records_inserted': inserted,
                    'records_skipped': skipped,
                    'retries': attempt - 1
                })
                
                if errors:
                    result['errors'].extend(errors)
                
                return result
        
        except Exception as e:
            error_msg = str(e)
            result['errors'].append({
                'attempt': attempt,
                'error': error_msg
            })
            
            if attempt <= retry_count:
                time.sleep(retry_delay)
    
    # If we get here, all retries failed
    result['success'] = False
    return result
