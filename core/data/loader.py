"""
Data loading utilities for the trading system.

This module provides functions to load and manage ticker data.
"""
import json
from pathlib import Path
from typing import List, Optional

# Project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
TICKERS_JSON = PROJECT_ROOT / "tickers.json"

def get_all_tickers() -> List[str]:
    """
    Get a list of all ticker symbols from the tickers.json file.
    
    Returns:
        List[str]: List of ticker symbols.
        
    Raises:
        FileNotFoundError: If tickers.json does not exist.
        json.JSONDecodeError: If tickers.json is not valid JSON.
        KeyError: If the 'tickers' key is missing from the JSON.
    """
    if not TICKERS_JSON.exists():
        raise FileNotFoundError(f"Tickers file not found at {TICKERS_JSON}")
    
    with open(TICKERS_JSON, 'r') as f:
        data = json.load(f)
    
    if 'tickers' not in data:
        raise KeyError("No 'tickers' key found in tickers.json")
    
    return [ticker.upper() for ticker in data['tickers'] if ticker.strip()]

def get_ticker_data(ticker: str) -> Optional[dict]:
    """
    Get data for a specific ticker from tickers.json.
    
    Args:
        ticker: The ticker symbol to look up.
        
    Returns:
        dict: The ticker data if found, None otherwise.
    """
    try:
        tickers = get_all_tickers()
        return ticker.upper() in tickers
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return False
