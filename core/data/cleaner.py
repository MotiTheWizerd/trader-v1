#!/usr/bin/env python
"""
Data cleaning module for ticker data.

This module provides functions to clean and prepare ticker data
before saving it to disk.
"""
from typing import List, Optional
import pandas as pd


def clean_ticker_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean ticker data by:
    - Dropping unnecessary columns (Dividends, Stock Splits)
    - Ensuring timestamp is parsed as datetime
    - Sorting rows by timestamp
    - Ensuring consistent column naming
    - Removing null values
    - Ensuring proper data types
    
    Args:
        df (pd.DataFrame): Raw ticker data
    
    Returns:
        pd.DataFrame: Cleaned ticker data
    """
    # Make a copy to avoid modifying the original
    cleaned_df = df.copy()
    
    # Drop unnecessary columns if they exist
    columns_to_drop = ['Dividends', 'Stock Splits']
    existing_columns = [col for col in columns_to_drop if col in cleaned_df.columns]
    if existing_columns:
        cleaned_df = cleaned_df.drop(columns=existing_columns)
    
    # Ensure timestamp is parsed as datetime
    if 'timestamp' in cleaned_df.columns:
        cleaned_df['timestamp'] = pd.to_datetime(cleaned_df['timestamp'])
    elif 'Datetime' in cleaned_df.columns:
        cleaned_df['timestamp'] = pd.to_datetime(cleaned_df['Datetime'])
        cleaned_df = cleaned_df.drop(columns=['Datetime'])
    elif 'Date' in cleaned_df.columns:
        cleaned_df['timestamp'] = pd.to_datetime(cleaned_df['Date'])
        cleaned_df = cleaned_df.drop(columns=['Date'])
    
    # Ensure consistent column naming (all lowercase)
    cleaned_df.columns = [col.lower() for col in cleaned_df.columns]
    
    # Map common column names to our standard names
    column_mapping = {
        'adj close': 'close',
        'adj_close': 'close',
        'vol': 'volume'
    }
    
    # Rename columns based on the mapping
    cleaned_df = cleaned_df.rename(columns=column_mapping)
    
    # Ensure required columns exist with correct names
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    # Check if all required columns exist
    missing_columns = [col for col in required_columns if col not in cleaned_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Sort rows by timestamp
    cleaned_df = cleaned_df.sort_values('timestamp')
    
    # Drop rows with null values
    cleaned_df = cleaned_df.dropna()
    
    # Ensure proper data types
    cleaned_df['open'] = cleaned_df['open'].astype(float)
    cleaned_df['high'] = cleaned_df['high'].astype(float)
    cleaned_df['low'] = cleaned_df['low'].astype(float)
    cleaned_df['close'] = cleaned_df['close'].astype(float)
    cleaned_df['volume'] = cleaned_df['volume'].astype(float)
    
    # Select only the required columns in the correct order
    cleaned_df = cleaned_df[required_columns]
    
    # Verify the DataFrame is not empty
    if cleaned_df.empty:
        raise ValueError("Cleaning resulted in an empty DataFrame")
    
    return cleaned_df


def validate_ticker_data(df: pd.DataFrame) -> bool:
    """
    Validate that the ticker data meets our requirements.
    
    Args:
        df (pd.DataFrame): Ticker data to validate
    
    Returns:
        bool: True if data is valid, False otherwise
    """
    # Check if DataFrame is empty
    if df.empty:
        return False
    
    # Check if required columns exist
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_columns):
        return False
    
    # Check if there are any null values
    if df[required_columns].isnull().any().any():
        return False
    
    # Check if timestamp is sorted
    if not df['timestamp'].equals(df['timestamp'].sort_values()):
        return False
    
    return True
