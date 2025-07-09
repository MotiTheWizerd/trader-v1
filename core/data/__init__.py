"""
Core data module for the trading prediction system.
"""
from core.data.downloader import (
    download_ticker_data,
    save_ticker_data,
    download_and_save_ticker_data,
    download_all_tickers,
    load_tickers,
    ensure_data_directory,
    DEFAULT_INTERVAL,
    DEFAULT_PERIOD,
    TICKERS_FILE,
    DATA_DIR
)

from core.data.cleaner import (
    clean_ticker_data,
    validate_ticker_data
)

from core.data.pipeline import (
    process_ticker_data,
    process_all_tickers
)

__all__ = [
    "download_ticker_data",
    "save_ticker_data",
    "download_and_save_ticker_data",
    "download_all_tickers",
    "load_tickers",
    "ensure_data_directory",
    "DEFAULT_INTERVAL",
    "DEFAULT_PERIOD",
    "TICKERS_FILE",
    "DATA_DIR",
    "clean_ticker_data",
    "validate_ticker_data",
    "process_ticker_data",
    "process_all_tickers"
]
