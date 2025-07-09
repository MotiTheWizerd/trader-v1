#!/usr/bin/env python
"""
Data pipeline module for ticker data.

This module provides functions to orchestrate the flow of data from
downloading to cleaning to saving.
"""
from typing import Dict, List, Optional, Union
from datetime import datetime
import os
import pandas as pd

from core.data.downloader import (
    download_ticker_data,
    save_ticker_data,
    load_tickers,
    ensure_data_directory,
    DATA_DIR
)
from core.data.cleaner import clean_ticker_data, validate_ticker_data


def process_ticker_data(
    ticker: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = "5m",
    period: Optional[str] = None,
    save_date: Optional[datetime] = None,
) -> str:
    """
    Process ticker data through the complete pipeline:
    1. Download raw data
    2. Clean data
    3. Save cleaned data
    
    Args:
        ticker (str): Ticker symbol
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
        period (Optional[str]): Period to download
        save_date (Optional[datetime]): Date to use for the file name, defaults to today
    
    Returns:
        str: Path to the saved file
        
    Raises:
        ValueError: If data validation fails
    """
    # Step 1: Download raw data
    raw_data = download_ticker_data(ticker, start_date, end_date, interval, period)
    
    # Step 2: Clean data
    cleaned_data = clean_ticker_data(raw_data)
    
    # Step 3: Validate data
    if not validate_ticker_data(cleaned_data):
        raise ValueError(f"Data validation failed for {ticker}")
    
    # Step 4: Save cleaned data
    file_path = save_ticker_data(ticker, cleaned_data, save_date)
    
    return file_path


def process_all_tickers(
    tickers: Optional[List[str]] = None,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    interval: str = "5m",
    period: Optional[str] = None,
    save_date: Optional[datetime] = None,
) -> Dict[str, str]:
    """
    Process multiple tickers through the complete pipeline.
    
    Args:
        tickers (Optional[List[str]]): List of ticker symbols, if None, load from tickers.json
        start_date (Optional[Union[str, datetime]]): Start date for data download
        end_date (Optional[Union[str, datetime]]): End date for data download
        interval (str): Data interval (e.g., "1d", "1h", "5m")
        period (Optional[str]): Period to download
        save_date (Optional[datetime]): Date to use for the file name, defaults to today
    
    Returns:
        Dict[str, str]: Dictionary mapping ticker symbols to file paths
    """
    # Ensure data directory exists
    ensure_data_directory()
    
    # Load tickers if not provided
    if tickers is None:
        tickers = load_tickers()
    
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
    
    results = {}
    for ticker in tickers:
        try:
            file_path = process_ticker_data(
                ticker,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                period=period,
                save_date=save_date
            )
            results[ticker] = file_path
        except Exception as e:
            # Log error and continue with next ticker
            print(f"Error processing {ticker}: {str(e)}")
            results[ticker] = "ERROR"
    
    return results
