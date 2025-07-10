"""
Data loading utilities for the trading system.

This module provides functions to load and manage ticker data.
"""
import json
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Union
from datetime import datetime

# Project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
TICKERS_JSON = PROJECT_ROOT / "tickers.json"
TICKERS_DIR = PROJECT_ROOT / "tickers"

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
        return None


def load_historical_data(ticker: str) -> Optional[pd.DataFrame]:
    """
    Load all available historical data for a ticker from all data files.
    
    Args:
        ticker: Ticker symbol (case-insensitive)
        
    Returns:
        pd.DataFrame: Combined historical data with timestamps as index,
                     or None if no data found
    """
    ticker = ticker.upper()
    ticker_dir = TICKERS_DIR / ticker / "data"
    
    if not ticker_dir.exists():
        print(f"Directory not found: {ticker_dir}")
        return None
    
    print(f"Looking for data files in: {ticker_dir}")
    
    # First, list all CSV files in the directory for debugging
    all_csv_files = list(ticker_dir.glob("*.csv"))
    print(f"\nAll CSV files in {ticker_dir}:")
    for f in all_csv_files:
        print(f"  - {f.name}")
    
    # Try different patterns to find data files
    patterns_to_try = [
        f"*_{ticker}_data.csv",       # Timestamped files (YYYYMMDDHHMM_TICKER_data.csv)
        f"[0-9]{{6}}_{ticker}_data.csv",  # Monthly files (YYYYMM_TICKER_data.csv)
        f"{ticker}_data.csv",          # Main data file (TICKER_data.csv)
        f"{ticker}_*.csv",             # Any CSV file starting with ticker
        f"*{ticker}*.csv"              # Any CSV file containing ticker name
    ]
    
    data_files = []
    
    for pattern in patterns_to_try:
        try:
            files = list(ticker_dir.glob(pattern))
            if files:
                print(f"\nFound {len(files)} files with pattern '{pattern}':")
                for f in files:
                    print(f"  - {f.name}")
                # Add new files, avoiding duplicates
                new_files = [f for f in files if f not in data_files]
                data_files.extend(new_files)
        except Exception as e:
            print(f"Error with pattern '{pattern}': {e}")
    
    # If still no files found, try a more aggressive search
    if not data_files and all_csv_files:
        print("\nNo files matched specific patterns, trying all CSV files...")
        data_files = all_csv_files
    
    if not data_files:
        print(f"No data files found for {ticker} in {ticker_dir}")
        return None
    
    # Sort files by name (which includes timestamp) in descending order
    data_files.sort(reverse=True)
    print(f"Found {len(data_files)} data files for {ticker}")
    
    all_data = []
    total_rows = 0
    
    # Read all available data files
    print(f"Found {len(data_files)} data files for {ticker}")
    
    for file_path in data_files:
        try:
            print(f"\nReading file: {file_path.name}")
            print(f"  - Full path: {file_path}")
            
            # Read the file
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            print(f"  - Read {len(df)} rows")
            print(f"  - Columns: {df.columns.tolist()}")
            print(f"  - First row: {df.iloc[0].to_dict() if not df.empty else 'Empty'}")
            print(f"  - Last row: {df.iloc[-1].to_dict() if not df.empty else 'Empty'}")
            
            # Ensure timestamp column exists and set as index if not already
            if 'timestamp' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
                # Convert to datetime and make timezone-naive
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
                df.set_index('timestamp', inplace=True)
            
            # If index is not datetime, try to convert it
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    # Convert to datetime and make timezone-naive
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                except Exception as e:
                    print(f"  - Could not convert index to datetime: {e}")
                    continue
            
            # Ensure we have the required columns (case-insensitive)
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df.columns = [str(col).lower() for col in df.columns]
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"  - Missing required columns: {missing_cols}")
                continue
            
            # Append to our data
            all_data.append(df)
            total_rows += len(df)
            print(f"  - Added to dataset (total: {total_rows} rows)")
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    if not all_data:
        print("No valid data found in any files")
        return None
    
    if not all_data:
        print("No valid data to combine")
        return None
        
    try:
        # Combine all dataframes
        combined = pd.concat(all_data, axis=0)
        
        # Remove duplicates (keeping the first occurrence)
        combined = combined[~combined.index.duplicated(keep='first')]
        
        # Sort by index (timestamp)
        combined = combined.sort_index()
        
        # Ensure we have the required columns (case-insensitive)
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        combined.columns = [str(col).lower() for col in combined.columns]
        
        # Check for missing required columns
        missing_cols = [col for col in required_cols if col not in combined.columns]
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")
            return None
            
        # Ensure data types are correct
        for col in required_cols:
            combined[col] = pd.to_numeric(combined[col], errors='coerce')
            
        # Drop any rows with missing values in required columns
        combined = combined.dropna(subset=required_cols)
        
        if combined.empty:
            print("No valid data after cleaning")
            return None
            
        print(f"Successfully combined {len(combined)} rows of historical data for {ticker}")
        print(f"Date range: {combined.index.min()} to {combined.index.max()}")
        
        return combined
        
    except Exception as e:
        print(f"Error combining data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
