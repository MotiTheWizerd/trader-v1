"""
Signal metadata export module for the real-time scheduler.

This module handles saving and analyzing signal metadata from scheduler jobs.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from rich.console import Console
from rich.table import Table

# Constants
METADATA_DIR = Path("tickers/metadata")


def ensure_metadata_dir() -> None:
    """Ensure metadata directory exists."""
    METADATA_DIR.mkdir(exist_ok=True, parents=True)


def save_signal_metadata(results: List[Dict[str, Any]], timestamp: datetime) -> str:
    """
    Save a summary JSON with signal counts per job.
    
    Args:
        results (List[Dict[str, Any]]): List of ticker processing results
        timestamp (datetime): Current timestamp
    
    Returns:
        str: Path to the saved metadata file
    """
    # Ensure metadata directory exists
    ensure_metadata_dir()
    
    # Format timestamp for filename
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M")
    metadata_file = METADATA_DIR / f"{timestamp_str}_summary.json"
    
    # Initialize signal counts
    signal_counts = {
        "BUY": 0,
        "SELL": 0,
        "STAY": 0,
        "ERROR": 0
    }
    
    # Count signals from successful results
    successful_tickers = []
    failed_tickers = []
    
    for result in results:
        ticker = result["ticker"]
        if result["status"] == "success" and result["signal_file"]:
            # Read the signal file to count signal types
            signal_file = result["signal_file"]
            try:
                df = pd.read_csv(signal_file)
                if not df.empty:
                    # Count each signal type
                    signal_types = df["signal"].value_counts().to_dict()
                    for signal_type, count in signal_types.items():
                        if signal_type in signal_counts:
                            signal_counts[signal_type] += count
                    
                    # Add to successful tickers
                    successful_tickers.append(ticker)
                else:
                    signal_counts["ERROR"] += 1
                    failed_tickers.append(ticker)
            except Exception:
                signal_counts["ERROR"] += 1
                failed_tickers.append(ticker)
        else:
            signal_counts["ERROR"] += 1
            failed_tickers.append(ticker)
    
    # Create metadata
    metadata = {
        "timestamp": timestamp_str,
        "datetime": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "signal_counts": signal_counts,
        "total_tickers": len(results),
        "successful_tickers": len(successful_tickers),
        "failed_tickers": len(failed_tickers),
        "tickers": {
            "success": successful_tickers,
            "failed": failed_tickers
        }
    }
    
    # Save metadata to JSON file
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    return str(metadata_file)


def display_signal_summary(metadata_file: str, console: Optional[Console] = None) -> None:
    """
    Display a summary of signal counts from a metadata file.
    
    Args:
        metadata_file (str): Path to metadata JSON file
        console (Optional[Console]): Rich console to use for display
    """
    if console is None:
        console = Console()
    
    try:
        # Load metadata
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        # Create summary table
        table = Table(title=f"Signal Summary - {metadata['datetime']}")
        table.add_column("Signal Type", style="cyan")
        table.add_column("Count", style="green")
        
        # Add signal counts to table
        for signal_type, count in metadata["signal_counts"].items():
            if signal_type != "ERROR":
                table.add_row(signal_type, str(count))
        
        # Add ticker stats
        table.add_row("", "")
        table.add_row("Total Tickers", str(metadata["total_tickers"]))
        table.add_row("Successful", str(metadata["successful_tickers"]))
        table.add_row("Failed", str(metadata["failed_tickers"]))
        
        # Display table
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error displaying signal summary: {str(e)}[/bold red]")


def get_latest_metadata_file() -> Optional[str]:
    """
    Get the path to the latest metadata file.
    
    Returns:
        Optional[str]: Path to latest metadata file or None if not found
    """
    ensure_metadata_dir()
    
    # List all metadata files
    metadata_files = list(METADATA_DIR.glob("*_summary.json"))
    
    if not metadata_files:
        return None
    
    # Sort by modification time (newest first)
    latest_file = max(metadata_files, key=lambda p: p.stat().st_mtime)
    return str(latest_file)
