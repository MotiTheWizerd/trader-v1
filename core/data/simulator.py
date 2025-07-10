"""
Data simulator module for generating mock OHLCV data in the same format as yfinance.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import random

from core.config.paths import get_ticker_data_path

class DataSimulator:
    """Simulates 5-minute OHLCV data for backtesting and development."""
    
    def __init__(self, base_price: float = 100.0, volatility: float = 0.01, 
                 volume_range: Tuple[int, int] = (1000, 10000)):
        """
        Initialize the data simulator.
        
        Args:
            base_price: Starting price for the simulation
            volatility: Price volatility (as a fraction of base_price)
            volume_range: Range for random volume generation (min, max)
        """
        self.base_price = base_price
        self.volatility = volatility
        self.volume_range = volume_range
        self.current_price = base_price
        
    def generate_candles(self, num_candles: int = 1, 
                        timestamp: Optional[datetime] = None) -> pd.DataFrame:
        """
        Generate a DataFrame of OHLCV data.
        
        Args:
            num_candles: Number of 5-minute candles to generate
            timestamp: Starting timestamp (defaults to now - num_candles * 5 minutes)
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data and datetime index
        """
        if timestamp is None:
            timestamp = datetime.now() - timedelta(minutes=5 * num_candles)
            
        timestamps = [timestamp + timedelta(minutes=5 * i) for i in range(num_candles)]
        data = []
        
        for _ in range(num_candles):
            # Generate random price movement
            price_change = (2 * np.random.random() - 1) * self.volatility * self.current_price
            new_price = self.current_price + price_change
            
            # Generate OHLC prices with some randomness
            o = self.current_price
            h = max(o, new_price) * (1 + np.random.random() * 0.002)
            l = min(o, new_price) * (1 - np.random.random() * 0.002)
            c = new_price
            
            # Generate random volume
            v = random.randint(*self.volume_range)
            
            data.append([o, h, l, c, v])
            self.current_price = c  # Update current price for next candle
            
        df = pd.DataFrame(
            data, 
            columns=['open', 'high', 'low', 'close', 'volume'],
            index=pd.DatetimeIndex(timestamps, name='Datetime')
        )
        
        # Add a timestamp column for compatibility with signal generation
        df['timestamp'] = df.index
        
        return df
    
    def save_simulated_data(self, ticker: str, num_candles: int = 1, 
                           timestamp: Optional[datetime] = None) -> str:
        """
        Generate and save simulated data to a CSV file with timestamp in the filename.
        
        Args:
            ticker: Ticker symbol for the file name
            num_candles: Number of 5-minute candles to generate
            timestamp: Timestamp for the file name (defaults to now)
            
        Returns:
            str: Path to the saved file
        """
        # Generate the data ending at the specified timestamp
        df = self.generate_candles(num_candles, timestamp)
        
        # Use the end time of the last candle as the file timestamp
        if timestamp is None:
            file_timestamp = datetime.now()
        else:
            # If timestamp was provided, use it directly
            file_timestamp = timestamp
            
        # Format: YYYYMMDDHHMM_TICKER_data.csv
        timestamp_str = file_timestamp.strftime("%Y%m%d%H%M")
        
        # Get the file path using the path module
        file_path = Path(get_ticker_data_path(
            ticker=ticker.upper(),
            date=timestamp_str  # Using full timestamp as the date part
        ))
        
        # Ensure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp column for compatibility with signal generation
        df_to_save = df.copy()
        df_to_save['timestamp'] = df_to_save.index
        
        # Always create a new file (no appending)
        df_to_save.to_csv(file_path, index=True)
        
        return str(file_path)


def simulate_ticker_data(ticker: str, num_candles: int = 1, 
                        base_price: float = 100.0, volatility: float = 0.01,
                        volume_range: Tuple[int, int] = (1000, 10000),
                        timestamp: Optional[datetime] = None) -> str:
    """
    Convenience function to simulate and save ticker data in one call.
    
    Args:
        ticker: Ticker symbol
        num_candles: Number of 5-minute candles to generate
        base_price: Starting price for the simulation
        volatility: Price volatility (as a fraction of base_price)
        volume_range: Range for random volume generation (min, max)
        timestamp: Starting timestamp (defaults to now - num_candles * 5 minutes)
        
    Returns:
        str: Path to the saved file
    """
    simulator = DataSimulator(base_price, volatility, volume_range)
    return simulator.save_simulated_data(ticker, num_candles, timestamp)
