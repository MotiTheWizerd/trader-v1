"""
Configuration module for the trading system.

This package provides a centralized way to access configuration settings
and file paths throughout the application.
"""
from pathlib import Path
from rich.console import Console

# Initialize the console
console = Console()

# Import and re-export the path functions
from .paths import get_ticker_data_path, get_signal_file_path

__all__ = [
    'console',
    'get_ticker_data_path',
    'get_signal_file_path',
]
