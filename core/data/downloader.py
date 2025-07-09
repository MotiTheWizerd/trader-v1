"""
Ticker data downloader module using yfinance.
Handles downloading historical OHLCV data for stock tickers by date.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import json
import pandas as pd
import yfinance as yf
from pathlib import Path

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
    
    # Ensure timestamp is in the right format
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df


def save_ticker_data(
    ticker: str, data: pd.DataFrame, date: Optional[datetime] = None
) -> str:
    """
    Save ticker data to a CSV file using the configured path format.
    
    Args:
        ticker (str): Ticker symbol
        data (pd.DataFrame): DataFrame containing the ticker data
        date (Optional[datetime]): Date for the file name, defaults to today
    
    Returns:
        str: Path to the saved file
    """
    # Use provided date or today's date
    if date is None:
        date = datetime.now()
    
    # Format the date as YYYYMMdd
    date_str = date.strftime("%Y%m%d")
    
    # Get the file path from configuration
    file_path = get_ticker_data_path(ticker.upper(), date_str)
    
    # Ensure the parent directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save the data
    data.to_csv(file_path)
    
    return file_path


def download_and_save_ticker_data(
    ticker: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = DEFAULT_INTERVAL,
    period: Optional[str] = None,
    save_date: Optional[datetime] = None,
) -> str:
    """
    Download and save ticker data in one operation.
    
    Args:
        ticker (str): Ticker symbol
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
        period (Optional[str]): Period to download
        save_date (Optional[datetime]): Date to use for the file name, defaults to today
    
    Returns:
        str: Path to the saved file
    """
    data = download_ticker_data(ticker, start_date, end_date, interval, period)
    
    # Determine the appropriate date for the filename
    if save_date is None:
        if end_date is not None:
            # Use end_date if provided
            if isinstance(end_date, str):
                save_date = pd.to_datetime(end_date).to_pydatetime()
            else:
                save_date = end_date
        elif start_date is not None:
            # Use start_date if end_date is not provided
            if isinstance(start_date, str):
                save_date = pd.to_datetime(start_date).to_pydatetime()
            else:
                save_date = start_date
        # Otherwise, save_date will remain None and today's date will be used
    
    return save_ticker_data(ticker, data, save_date)


def download_all_tickers(
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = DEFAULT_INTERVAL,
    period: Optional[str] = None,
    save_date: Optional[Union[str, datetime]] = None,
) -> Dict[str, str]:
    """
    Download data for all tickers in the tickers.json file.
    
    Args:
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
        period (Optional[str]): Period to download
        save_date (Optional[Union[str, datetime]]): Date to use for the file name, defaults to today
    
    Returns:
        Dict[str, str]: Dictionary mapping ticker symbols to their data file paths
    """
    tickers = load_tickers()
    results = {}
    
    # Convert save_date to datetime if it's a string
    if isinstance(save_date, str):
        save_date = pd.to_datetime(save_date).to_pydatetime()
    
    for ticker in tickers:
        try:
            file_path = download_and_save_ticker_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date or datetime.now(),  # Use current time if end_date not provided
                interval=interval,
                period=period,
                save_date=save_date
            )
            results[ticker] = file_path
        except Exception as e:
            print(f"Error downloading {ticker}: {str(e)}")
    
    return results
