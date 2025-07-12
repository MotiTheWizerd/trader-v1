"""
File operations for the scheduler.

This module provides utilities for file and directory operations used by the scheduler.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from rich.console import Console

# Initialize rich console
console = Console()

def ensure_directories() -> None:
    """Ensure all required directories exist."""
    # Data directories
    data_dir = Path("tickers") / "data"
    signals_dir = Path("tickers") / "signals"
    logs_dir = Path("logs")
    
    # Create directories if they don't exist
    for directory in [data_dir, signals_dir, logs_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        
    return {
        "data_dir": str(data_dir.absolute()),
        "signals_dir": str(signals_dir.absolute()),
        "logs_dir": str(logs_dir.absolute()),
    }


def save_to_csv(
    df: pd.DataFrame, 
    base_dir: Union[str, Path], 
    ticker: str, 
    timestamp: datetime, 
    suffix: str = ""
) -> str:
    """Save a DataFrame to a CSV file with timestamp-based naming.
    
    Args:
        df: DataFrame to save
        base_dir: Base directory path
        ticker: Ticker symbol
        timestamp: Timestamp for the file name
        suffix: Optional suffix for the file name
        
    Returns:
        str: Path to the saved file
    """
    # Create ticker directory if it doesn't exist
    ticker_dir = Path(base_dir) / ticker.lower()
    ticker_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker.lower()}_{timestamp_str}{f'_{suffix}' if suffix else ''}.csv"
    filepath = ticker_dir / filename
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    return str(filepath)


def load_latest_data(
    ticker: str, 
    data_dir: Union[str, Path], 
    max_files: int = 1
) -> Optional[pd.DataFrame]:
    """Load the most recent data file(s) for a ticker.
    
    Args:
        ticker: Ticker symbol
        data_dir: Directory containing data files
        max_files: Maximum number of most recent files to load
        
    Returns:
        Optional[pd.DataFrame]: Combined DataFrame of the most recent data,
            or None if no data found
    """
    ticker_dir = Path(data_dir) / ticker.lower()
    if not ticker_dir.exists():
        return None
        
    # Find all CSV files for the ticker
    data_files = list(ticker_dir.glob("*.csv"))
    if not data_files:
        return None
        
    # Sort by modification time (newest first)
    data_files.sort(key=os.path.getmtime, reverse=True)
    
    # Load the most recent file(s)
    dfs = []
    for filepath in data_files[:max_files]:
        try:
            df = pd.read_csv(filepath)
            df['source_file'] = filepath.name  # Track source file
            dfs.append(df)
        except Exception as e:
            console.log(f"Error loading {filepath}: {e}", style="red")
    
    if not dfs:
        return None
        
    # Combine dataframes if multiple files were loaded
    if len(dfs) > 1:
        return pd.concat(dfs, ignore_index=True)
    return dfs[0]


def cleanup_old_files(directory: Union[str, Path], days_to_keep: int = 30) -> None:
    """Remove files older than the specified number of days.
    
    Args:
        directory: Directory to clean up
        days_to_keep: Number of days of files to keep
    """
    directory = Path(directory)
    if not directory.exists():
        return
        
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
    
    for item in directory.iterdir():
        if item.is_file() and item.stat().st_mtime < cutoff_time:
            try:
                item.unlink()
                console.log(f"Removed old file: {item}")
            except Exception as e:
                console.log(f"Error removing {item}: {e}", style="red")
        elif item.is_dir():
            # Recursively clean subdirectories
            cleanup_old_files(item, days_to_keep)
            # Remove empty directories
            try:
                item.rmdir()
                console.log(f"Removed empty directory: {item}")
            except OSError:
                # Directory not empty, skip
                pass
