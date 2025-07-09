"""
Structured JSON logger for the stock trading prediction system.

This module provides a centralized logging mechanism that writes structured
JSON log entries to daily log files in newline-delimited format (.jsonl).

Each log entry contains:
- timestamp: ISO 8601 format
- level: INFO, WARNING, ERROR
- ticker: Stock ticker symbol (if applicable)
- event: Short keyword describing the event
- message: Human-readable message
- additional: Optional dictionary of additional data

Log files are stored in the logs/ directory with naming pattern:
log_<YYYYMMDD>.jsonl (e.g., log_20250708.jsonl)
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Union


# Constants
LOG_DIR = Path("logs")
LOG_LEVELS = ["INFO", "WARNING", "ERROR"]


def ensure_log_directory() -> None:
    """Ensure the log directory exists."""
    os.makedirs(LOG_DIR, exist_ok=True)


def get_log_filename() -> Path:
    """
    Generate the log filename for the current date.
    
    Returns:
        Path: Path to the log file
    """
    today = datetime.now().strftime("%Y%m%d")
    return LOG_DIR / f"log_{today}.jsonl"


def log_event(
    level: str,
    event: str,
    message: str,
    ticker: Optional[str] = None,
    additional: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log an event in JSON format to the daily log file.
    
    Args:
        level (str): Log level - INFO, WARNING, ERROR
        event (str): Event type keyword (e.g., download_complete)
        message (str): Human-readable message
        ticker (str, optional): Stock ticker symbol if applicable
        additional (Dict[str, Any], optional): Additional data to include
        
    Returns:
        Dict[str, Any]: The log entry that was written
    """
    # Validate log level
    level = level.upper()
    if level not in LOG_LEVELS:
        level = "INFO"  # Default to INFO if invalid level
    
    # Ensure log directory exists
    ensure_log_directory()
    
    # Create log entry
    timestamp = datetime.now().isoformat(timespec='seconds')
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "event": event,
        "message": message
    }
    
    # Add optional fields if provided
    if ticker:
        log_entry["ticker"] = ticker
    
    if additional:
        log_entry.update(additional)
    
    # Get log filename for today
    log_file = get_log_filename()
    
    # Write log entry to file (append mode)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
        f.flush()  # Ensure entry is written immediately
    
    return log_entry


def log_info(
    event: str,
    message: str,
    ticker: Optional[str] = None,
    additional: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log an INFO level event.
    
    Args:
        event (str): Event type keyword
        message (str): Human-readable message
        ticker (str, optional): Stock ticker symbol if applicable
        additional (Dict[str, Any], optional): Additional data to include
        
    Returns:
        Dict[str, Any]: The log entry that was written
    """
    return log_event("INFO", event, message, ticker, additional)


def log_warning(
    event: str,
    message: str,
    ticker: Optional[str] = None,
    additional: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log a WARNING level event.
    
    Args:
        event (str): Event type keyword
        message (str): Human-readable message
        ticker (str, optional): Stock ticker symbol if applicable
        additional (Dict[str, Any], optional): Additional data to include
        
    Returns:
        Dict[str, Any]: The log entry that was written
    """
    return log_event("WARNING", event, message, ticker, additional)


def log_error(
    event: str,
    message: str,
    ticker: Optional[str] = None,
    exception: Optional[Exception] = None,
    additional: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log an ERROR level event.
    
    Args:
        event (str): Event type keyword
        message (str): Human-readable message
        ticker (str, optional): Stock ticker symbol if applicable
        exception (Exception, optional): Exception object if available
        additional (Dict[str, Any], optional): Additional data to include
        
    Returns:
        Dict[str, Any]: The log entry that was written
    """
    # Add exception details if provided
    if exception:
        if not additional:
            additional = {}
        additional["exception"] = {
            "type": type(exception).__name__,
            "message": str(exception)
        }
    
    return log_event("ERROR", event, message, ticker, additional)
