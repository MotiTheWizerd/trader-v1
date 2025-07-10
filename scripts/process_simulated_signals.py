"""
Process simulated data through the signal generation pipeline.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import pandas as pd
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.data.simulator import DataSimulator, simulate_ticker_data
from core.signals.moving_average import generate_ma_signals, generate_all_ma_signals
from core.config.paths import get_ticker_data_path, get_signal_file_path
from core.logger import log_info, log_error, log_warning

# Configure logger
def get_logger(name):
    """Create a simple logger interface that maps to our logging functions."""
    class Logger:
        def __init__(self, name):
            self.name = name.split('.')[-1]  # Use just the last part of the name
            
        def info(self, message, **kwargs):
            log_info("info", message, **kwargs)
            
        def warning(self, message, **kwargs):
            log_warning("warning", message, **kwargs)
            
        def error(self, message, **kwargs):
            # Extract exc_info if present and convert to exception parameter
            exc_info = kwargs.pop('exc_info', None)
            exception = kwargs.pop('exception', None)
            if exc_info and isinstance(exc_info, tuple):
                exception = exc_info[1]  # Get the exception instance
            log_error("error", message, exception=exception, **kwargs)
    
    return Logger(name)

# Create logger instance
logger = get_logger(__name__)

# Configure console for rich output
console = Console()

class SimulatedSignalProcessor:
    """Process simulated data through the signal generation pipeline."""
    
    def __init__(self, tickers: List[str], base_prices: Optional[Dict[str, float]] = None, 
                 volatility: float = 0.015, volume_range: Tuple[int, int] = (1000, 10000)):
        """
        Initialize the signal processor.
        
        Args:
            tickers: List of ticker symbols to process
            base_prices: Optional dictionary of base prices for each ticker
            volatility: Price volatility (as a fraction of base_price)
            volume_range: Range for random volume generation (min, max)
        """
        self.tickers = tickers
        self.base_prices = base_prices or {ticker: 100.0 for ticker in tickers}
        self.volatility = volatility
        self.volume_range = volume_range
        self.simulators = {
            ticker: DataSimulator(
                base_price=self.base_prices[ticker],
                volatility=volatility,
                volume_range=volume_range
            )
            for ticker in tickers
        }
    
    def generate_and_process_data(self, num_candles: int = 1, 
                               timestamp: Optional[datetime] = None) -> Dict[str, str]:
        """
        Generate simulated data and process it through the signal pipeline.
        
        Args:
            num_candles: Number of 5-minute candles to generate
            timestamp: Starting timestamp (defaults to now - num_candles * 5 minutes)
            
        Returns:
            Dict mapping ticker symbols to their signal file paths
        """
        signal_paths = {}
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing tickers...", total=len(self.tickers))
            
            for ticker in self.tickers:
                progress.update(task, description=f"Processing {ticker}...")
                
                try:
                    # Generate simulated data
                    simulator = self.simulators[ticker]
                    data_path = simulator.save_simulated_data(
                        ticker=ticker,
                        num_candles=5,  # Generate 5 candles (25 minutes of data)
                        timestamp=timestamp
                    )
                    
                    if not data_path:
                        logger.error(f"Failed to generate data for {ticker}")
                        continue
                        
                    logger.info(f"Generated data for {ticker}: {data_path}")
                    
                    # Format the date part for the signal file name (YYYYMMDDHHMM)
                    signal_timestamp = timestamp or datetime.now()
                    date_str = signal_timestamp.strftime("%Y%m%d%H%M")
                    
                    logger.info(f"Generating signals for {ticker} using historical data...")
                    
                    # Generate signals with the exact timestamp for the output file
                    # The function will automatically load historical data
                    signal_path = generate_ma_signals(
                        ticker=ticker,
                        date=date_str,  # Pass the formatted date string
                        short_window=5,  # Short moving average window
                        long_window=20,  # Long moving average window
                        include_reasoning=True,
                        confidence_threshold=0.005,  # Confidence threshold for signals
                        peak_window=12,  # Window for peak detection
                        peak_threshold=0.99,  # Threshold for peak detection
                        progress=progress
                    )
                    
                    if signal_path:
                        signal_paths[ticker] = signal_path
                        logger.info(f"Successfully generated signals for {ticker}: {signal_path}")
                    else:
                        logger.warning(f"No signals generated for {ticker} (returned None)")
                        
                    # Verify the signal file was created
                    if signal_path and not Path(signal_path).exists():
                        logger.error(f"Signal file not found at expected path: {signal_path}")
                    
                except Exception as e:
                    logger.error(f"Error processing {ticker}: {str(e)}", exc_info=True)
                
                progress.update(task, advance=1)
        
        return signal_paths

def main():
    """Main function to run the signal processing pipeline on simulated data."""
    # Configuration
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    base_prices = {
        "AAPL": 150.0,
        "MSFT": 300.0,
        "GOOGL": 2500.0,
        "AMZN": 120.0,
        "META": 350.0
    }
    volatility = 0.015  # 1.5% volatility
    
    # Initialize processor
    processor = SimulatedSignalProcessor(
        tickers=tickers,
        base_prices=base_prices,
        volatility=volatility,
        volume_range=(1000, 10000)
    )
    
    # Generate and process data
    console.rule("[bold blue]Starting Signal Generation")
    console.print(f"Processing {len(tickers)} tickers...")
    
    # Generate 50 candles (~4 hours of 5-minute data) to ensure we have enough for signal generation
    # The moving average windows are 5 (short) and 20 (long), so we need at least 20 bars
    signal_paths = processor.generate_and_process_data(num_candles=50)
    
    # Display results
    console.rule("[bold green]Processing Complete")
    console.print("\nGenerated signals for the following tickers:")
    for ticker, path in signal_paths.items():
        console.print(f"  • {ticker}: [cyan]{path}")

if __name__ == "__main__":
    main()
