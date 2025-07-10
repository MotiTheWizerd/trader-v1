"""
CRUD package for database operations.
"""
from .tickers_data_db import (
    insert_price,
    get_prices_for_ticker,
    delete_old_prices
)

from .tickers_signals_db import (
    insert_signal,
    get_signals_for_ticker,
    get_latest_signal,
    delete_old_signals
)

__all__ = [
    # Ticker data operations
    'insert_price',
    'get_prices_for_ticker',
    'delete_old_prices',
    
    # Signal operations
    'insert_signal',
    'get_signals_for_ticker',
    'get_latest_signal',
    'delete_old_signals',
]
