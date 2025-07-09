"""
Centralized path configuration for the trading system.

This module provides a single source of truth for all file paths and
naming conventions used throughout the application.

To change the file structure, only modify the path patterns below.
All other files should use these functions to get paths.
"""
from pathlib import Path
from typing import Optional

# Base directory for all data
TICKERS_DIR = Path("tickers")

# File path patterns - these are the only things you need to change
# to modify the file structure
TICKER_DATA_PATTERN = "{ticker}/data/date_{date}.csv"
SIGNAL_FILE_PATTERN = "{ticker}/signals/signal_{date}.csv"

def get_ticker_data_path(ticker: str, date: str) -> str:
    """
    Get the path to a ticker's data file.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        date: Date string in YYYYMMDD format
        
    Returns:
        String path to the ticker's data file
        Format: "tickers/{ticker}/data/date_{date}.csv"
    """
    return str(TICKERS_DIR / TICKER_DATA_PATTERN.format(ticker=ticker, date=date))

def get_signal_file_path(ticker: str, date: str) -> str:
    """
    Get the path to a signal file.
    
    Args:
        ticker: Stock ticker symbol
        date: Date string in YYYYMMDD format
        
    Returns:
        String path to the signal file
        Format: "tickers/{ticker}/signals/signal_{date}.csv"
    """
    return str(TICKERS_DIR / SIGNAL_FILE_PATTERN.format(ticker=ticker, date=date))
