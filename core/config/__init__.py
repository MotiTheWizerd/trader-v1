"""
Configuration module for the trading system.

This package provides a centralized way to access configuration settings
and file paths throughout the application.
"""
from pathlib import Path

# Import the console from the console module
from .console import console

# Make console available when importing from core.config
__all__ = ['console']

# Import and re-export the path functions
from .paths import (
    PROJECT_ROOT,
    TICKERS_DIR,
    TICKER_DATA_DIR,
    SIGNALS_DIR,
    LOGS_DIR,
    get_ticker_data_path,
    get_signal_file_path,
    get_log_file_path
)
from .utils import ensure_directory_exists, ensure_required_directories

# Ensure all required directories exist when the module is imported
ensure_required_directories()

__all__ = [
    'PROJECT_ROOT',
    'TICKERS_DIR',
    'TICKER_DATA_DIR',
    'SIGNALS_DIR',
    'LOGS_DIR',
    'console',
    'get_ticker_data_path',
    'get_signal_file_path',
    'get_log_file_path',
    'ensure_directory_exists',
    'ensure_required_directories'
]
