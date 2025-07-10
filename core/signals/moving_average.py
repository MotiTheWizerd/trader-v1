"""
Moving Average Signal Generator Module.

This module generates trading signals based on moving average crossover strategy:
- BUY when short-term MA crosses above long-term MA with sufficient confidence
- SELL when short-term MA crosses below long-term MA with sufficient confidence AND price is near a recent peak
- STAY otherwise or when insufficient data or low confidence

Confidence is calculated as the normalized absolute difference between the moving averages:
    confidence = abs(ma_short - ma_long) / ma_long

Dynamic confidence threshold:
- Uses a rolling window (default 100 bars) to calculate statistics
- Can use either z-score (default) or quantile-based thresholding
- Falls back to fixed threshold during initial window or when volatility is too low

Peak detection is used to validate SELL signals, ensuring they only trigger when price is
near a local maximum (within a configurable percentage threshold).

Signals with low confidence or SELL signals not near peaks are downgraded to STAY to reduce false positives.
"""
import os
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Rich progress bar
from rich.progress import Progress, TaskProgressColumn, TimeRemainingColumn, TextColumn, BarColumn, SpinnerColumn

# Import logger configuration
import logging
from core.logger import log_info, log_warning, log_error

# Configure logger
logger = logging.getLogger(__name__)

# Import path configuration
from core.config.paths import get_ticker_data_path, get_signal_file_path

# Import data loading
from core.data.loader import load_historical_data

# Import console
from core.config.console import console
from core.config.settings import DEBUG

# Import confidence threshold utilities
from .confidence import apply_confidence_filter

# Import load_tickers from downloader module
from core.data.downloader import load_tickers as get_all_tickers

def generate_ma_signals(
    ticker: str,
    date: Optional[Union[str, datetime]] = None,
    short_window: int = 5,
    long_window: int = 20,
    include_reasoning: bool = True,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None,
    df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Generate moving average signals from OHLCV data using dynamic confidence thresholds.
    
    The confidence threshold is dynamically calculated based on recent market volatility.
    For each row t, the confidence value is compared to a rolling window of the
    previous WINDOW_CONF bars to determine if the signal is statistically significant.
    
    Dynamic threshold options (configured in constants.py):
    - z-score: threshold = mean + Z_MIN * std
    - quantile: threshold = QUANTILE_MIN percentile
    
    Falls back to fixed confidence_threshold during the initial window or when volatility is too low.
    
    Args:
        ticker (str): Ticker symbol
        date (Optional[Union[str, datetime]]): Date for the file, defaults to today
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        include_reasoning (bool): Whether to include reasoning text with signals
        confidence_threshold (float): Fixed confidence threshold (fallback)
        peak_window (int): Window for detecting local price peaks
        peak_threshold (float): Threshold for peak detection (0-1)
        progress (Optional[Progress]): Rich progress bar instance
        task_id (Optional[int]): Task ID for progress tracking
        df (Optional[pd.DataFrame]): Optional DataFrame with price data
    
    Returns:
        pd.DataFrame: DataFrame containing the generated signals
    """
    # Only show debug info if we're not using a progress bar
    if progress is None or task_id is None:
        console.print(f"\n[yellow]=== Processing {ticker} ===[/yellow]")
    elif progress is not None and task_id is not None:
        progress.update(task_id, description=f"Processing {ticker}")
    
    # If no DataFrame provided, try to get data from database
    if df is None:
        try:
            if progress is not None and task_id is not None:
                progress.update(task_id, description=f"Fetching data for {ticker}")
            
            from core.db.deps import get_db
            from core.db.crud.tickers_data_db import get_prices_for_ticker
            
            try:
                with get_db() as db:
                    prices = get_prices_for_ticker(db, ticker)
                    if not prices:
                        msg = f"No price data found for {ticker} in database"
                        logger.warning(msg)
                        if progress is not None and task_id is not None:
                            progress.print(f"[yellow]{msg}[/yellow]")
                        return pd.DataFrame()
                        
                    # Convert to DataFrame
                    if progress is not None and task_id is not None:
                        progress.update(task_id, description=f"Processing {ticker} data")
                    
                    # Create DataFrame from prices
                    data = []
                    for p in prices:
                        data.append({
                            'timestamp': p.timestamp,
                            'open': p.open,
                            'high': p.high,
                            'low': p.low,
                            'close': p.close,
                            'volume': p.volume,
                            'ticker': ticker
                        })
                    
                    df = pd.DataFrame(data)
                    
                    # Ensure timestamp is timezone-naive
                    if not df.empty and 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
            
            except Exception as e:
                error_msg = f"Database error for {ticker}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                if progress is not None and task_id is not None:
                    progress.print(f"[red]{error_msg}[/red]")
                return pd.DataFrame()
                
        except Exception as e:
            error_msg = f"Error fetching price data for {ticker}: {str(e)}"
            logger.error(error_msg)
            if progress is not None and task_id is not None:
                progress.print(f"[red]{error_msg}[/red]")
            return pd.DataFrame()
    
    if df is None or df.empty:
        logger.warning(f"No data available for {ticker}")
        return pd.DataFrame()
    
    # Ensure we have the required columns
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        error_msg = f"Missing required columns in data for {ticker}: {', '.join(missing_columns)}"
        logger.error(error_msg)
        if progress is not None and task_id is not None:
            progress.print(f"[red]{error_msg}[/red]")
        return pd.DataFrame()
    
    if progress is not None and task_id is not None:
        progress.update(task_id, description=f"Generating signals for {ticker}")
    
    # Handle date filtering if date parameter is provided
    if date is None:
        date_str = datetime.now().strftime("%Y%m%d%H%M")
    elif isinstance(date, datetime):
        date_str = date.strftime("%Y%m%d%H%M")
    else:
        # Handle string date, remove any non-numeric characters
        date_str = ''.join(c for c in str(date) if c.isdigit())
        # Ensure we have at least YYYYMMDD
        if len(date_str) < 8:
            # If we don't have enough digits, use current date
            date_str = datetime.now().strftime("%Y%m%d%H%M")
        
        # Take first 12 characters (YYYYMMDDHHMM) if longer
        date_str = date_str[:12]
    
    # Only load historical data if no DataFrame was provided
    if df is None or df.empty:
        try:
            from core.db.deps import get_db
            with get_db() as db:
                prices = get_prices_for_ticker(db, ticker)
                if not prices:
                    logger.error(f"No historical data found for {ticker} in database")
                    return pd.DataFrame()
                
                # Convert to DataFrame
                data = []
                for p in prices:
                    data.append({
                        'timestamp': p.timestamp,
                        'open': p.open,
                        'high': p.high,
                        'low': p.low,
                        'close': p.close,
                        'volume': p.volume,
                        'ticker': ticker
                    })
                
                df = pd.DataFrame(data)
                
                # Ensure timestamp is timezone-naive
                if not df.empty and 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
                    
        except Exception as e:
            logger.error(f"Error loading historical data for {ticker}: {str(e)}", exc_info=True)
            return pd.DataFrame()
            
        if df is None or df.empty:
            logger.error(f"No historical data found for {ticker}")
            return pd.DataFrame()
    
    # Initialize _is_new_data as True for all rows by default
    df = df.copy()  # Create a copy to avoid modifying the input DataFrame
    df['_is_new_data'] = True
        
    # Try to find existing signals to determine which data is new
    signal_dir = Path(get_signal_file_path(ticker, "*", "dynamic")).parent
    signal_files = list(signal_dir.glob(f"*{ticker}*dynamic*.csv"))
    latest_signal_file = None
    
    if signal_files:
        latest_signal_file = None
        try:
            # Find the most recent signal file
            latest_signal_file = max(signal_files, key=lambda x: x.stat().st_mtime)
            # Read the last timestamp from the signal file
            last_signals = pd.read_csv(latest_signal_file)
            if not last_signals.empty and 'timestamp' in last_signals.columns:
                last_timestamp = pd.to_datetime(last_signals['timestamp']).max()
                logger.info(f"Found existing signal file with last timestamp: {last_timestamp}")
                
                # Filter data to only include new data points
                df = df[df['timestamp'] > last_timestamp]
                
                if df.empty:
                    logger.info(f"No new data points since last signal generation for {ticker}")
                    return pd.DataFrame()
        except Exception as e:
            logger.warning(f"Error reading existing signal file: {str(e)}")
            # Continue with full data if there's an error reading the file
            df['_is_new_data'] = True
        finally:
            # Ensure we close any open resources here
            pass
    
    # The signal file handling is now done in the first block
    # No duplicate code needed here
        
    # Adjust window sizes if we don't have enough data
    if len(df) < long_window * 2:
        # If we don't have enough data for the default windows, adjust them
        max_possible_window = max(5, len(df) // 2)  # Ensure at least 5 for short window
        if max_possible_window < 5:  # If we have very little data, just use what we have
            logger.warning(f"Very limited data for {ticker} ({len(df)} rows). Using all available data.")
            short_window = 3
            long_window = 5
        else:
            # Scale down the windows proportionally
            ratio = max_possible_window / long_window
            short_window = max(5, int(short_window * ratio))
            long_window = max(10, int(long_window * ratio))
            logger.warning(f"Adjusted windows for {ticker} to short={short_window}, long={long_window} based on available data")
    
    logger.info(f"Using {len(df)} rows of data for {ticker} with windows: short={short_window}, long={long_window}")
        
    logger.info(f"Loaded {len(df)} rows of historical data for {ticker}")
    
    # Ensure we have the required columns (case-insensitive)
    df.columns = [col.lower() for col in df.columns]
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    for col in required_columns:
        if col not in df.columns:
            error_msg = f"Missing required column '{col}' in historical data for {ticker}"
            logger.error(error_msg)
            if progress and task_id is not None:
                progress.update(task_id, description=f"[red]{error_msg}")
            return None
    
    # Ensure the index is datetime and sort
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        else:
            df.index = pd.to_datetime(df.index)
    
    df.sort_index(inplace=True)
    
    # Ensure we have enough data points
    if len(df) < long_window:
        error_msg = (
            f"Not enough data points ({len(df)}) for {ticker}. "
            f"Need at least {long_window} for the long moving average."
        )
        logger.error(error_msg)
        if progress and task_id is not None:
            progress.update(task_id, description=f"[red]{error_msg}")
        return None
    
    # Ensure output directory exists (use dynamic path as base)
    output_dir = Path(get_signal_file_path(ticker, date_str, 'dynamic')).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Debug: Show info about the loaded data
    if progress is None:
        console.print(f"[green]Successfully loaded {len(df)} rows of historical data for {ticker}")
        if not df.empty:
            console.print(f"Date range: {df.index.min()} to {df.index.max()}")
            console.print(f"Columns: {', '.join(df.columns)}")
    
    # Ensure we have the required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        console.print(f"[red]Missing required columns: {', '.join(missing_cols)}")
        return None
    
    # Calculate moving averages and peak detection
    # If no external progress bar is provided, create a local one
    if progress is None:
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True
        ) as local_progress:
            task = local_progress.add_task("Calculating indicators...", total=3)
            
            # Calculate short-term moving average
            df["ma_short"] = df["close"].rolling(window=short_window).mean()
            local_progress.update(task, advance=1)
            
            # Calculate long-term moving average
            df["ma_long"] = df["close"].rolling(window=long_window).mean()
            local_progress.update(task, advance=1)
            
            # Calculate recent price maximum for peak detection
            df["recent_max"] = df["close"].rolling(window=peak_window).max()
            df["is_peak_zone"] = df["close"] >= df["recent_max"] * peak_threshold
            local_progress.update(task, advance=1)
    else:
        # Use the provided external progress bar
        # Calculate short-term moving average
        df["ma_short"] = df["close"].rolling(window=short_window).mean()
        
        # Calculate long-term moving average
        df["ma_long"] = df["close"].rolling(window=long_window).mean()
        
        # Calculate recent price maximum for peak detection
        df["recent_max"] = df["close"].rolling(window=peak_window).max()
        df["is_peak_zone"] = df["close"] >= df["recent_max"] * peak_threshold
    
    # Generate signals
    console.print("[bold blue]Generating signals with dynamic confidence filtering and peak detection...[/bold blue]")
    
    # Calculate raw confidence as normalized absolute distance between MAs
    df["confidence"] = abs(df["ma_short"] - df["ma_long"]) / df["ma_long"]
    
    # Initialize signal column
    df["signal"] = "STAY"
    
    # Apply signal logic
    mask_buy = (df["ma_short"] > df["ma_long"])
    mask_sell = (df["ma_short"] < df["ma_long"])
    
    # Apply initial signals
    df.loc[mask_buy, "signal"] = "BUY"
    df.loc[mask_sell, "signal"] = "SELL"
    
    # Handle insufficient data (NaN values in moving averages)
    mask_insufficient = df["ma_short"].isna() | df["ma_long"].isna() | df["recent_max"].isna()
    df.loc[mask_insufficient, "signal"] = "STAY"
    df.loc[mask_insufficient, "confidence"] = 0.0
    
    # Apply confidence threshold filter
    df = apply_confidence_filter(
        df,
        confidence_col='confidence',
        signal_col='signal',
        fixed_threshold=confidence_threshold,
        fallback_threshold=confidence_threshold
    )
    
    # Create masks for statistics
    mask_low_confidence = (df['confidence'] < df['threshold_used']) & (df['signal'] != 'STAY')
    mask_sell_not_peak = (df['signal'] == 'SELL') & ~df['is_peak_zone']

    # Get the threshold method for logging
    threshold_method = df.get('threshold_method', 'unknown').iloc[0] if not df.empty else 'unknown'
    console.print(f"[cyan]Using dynamic confidence threshold: {threshold_method}[/cyan]")
    
    # Apply peak zone filtering for SELL signals
    df.loc[mask_sell_not_peak, "signal"] = "STAY"
    
    # Debug info
    if progress is None or DEBUG:
        console.print("[yellow]Confidence statistics (last 5 rows):[/yellow]")
        debug_cols = ["confidence", "threshold_used"]
        if 'conf_mean' in df.columns and 'conf_std' in df.columns:
            debug_cols.extend(["conf_mean", "conf_std"])
        console.print(df[debug_cols].tail())
    
    # Add reasoning if requested
    if include_reasoning:
        # Initialize reasoning column
        df["reasoning"] = ""
        
        # Add reasoning for BUY signals
        mask_buy = (df["signal"] == "BUY")
        df.loc[mask_buy, "reasoning"] = (
            "BUY: Short MA crossed above Long MA with confidence " +
            df["confidence"].apply(lambda x: f"{x:.4f}") +
            " (threshold: " + df["threshold_used"].apply(lambda x: f"{x:.4f}") + ")"
        )
        
        # Add reasoning for SELL signals
        mask_sell = (df["signal"] == "SELL")
        df.loc[mask_sell, "reasoning"] = (
            "SELL: Short MA crossed below Long MA with confidence " +
            df["confidence"].apply(lambda x: f"{x:.4f}") +
            " (threshold: " + df["threshold_used"].apply(lambda x: f"{x:.4f}") + 
            ") and price near recent peak"
        )
        
        # Add reasoning for STAY signals (filtered by confidence)
        mask_stay_conf = (df["signal"] == "STAY") & ~mask_insufficient & ~mask_sell_not_peak
        df.loc[mask_stay_conf, "reasoning"] = (
            "STAY: Confidence too low (" +
            df["confidence"].apply(lambda x: f"{x:.4f}")
            + " < " + 
            df["threshold_used"].apply(lambda x: f"{x:.4f}") + ")"
        )
        
        # Add reasoning for STAY signals (filtered by peak detection)
        mask_stay_peak = (df["signal"] == "STAY") & mask_sell_not_peak
        df.loc[mask_stay_peak, "reasoning"] = "STAY: Price not near recent peak"
        
        # Add reasoning for insufficient data
        df.loc[mask_insufficient, "reasoning"] = "STAY: Insufficient data for signal generation"
    
    # Select columns for output
    columns = [
        "timestamp", "open", "high", "low", "close", "volume",
        "ma_short", "ma_long", "recent_max", "is_peak_zone",
        "signal", "confidence", "threshold_used"
    ]
    
    # Add any additional confidence-related columns that exist
    for col in ["conf_mean", "conf_std", "threshold_method"]:
        if col in df.columns:
            columns.append(col)
    
    if include_reasoning and "reasoning" in df.columns:
        columns.append("reasoning")
        
    # Ensure all required columns exist
    for col in ["ma_short", "ma_long", "recent_max", "is_peak_zone", "confidence", "threshold_used"]:
        if col not in df.columns:
            df[col] = np.nan
    
    # Select and reorder columns
    df = df[[col for col in columns if col in df.columns]]
    
    # Ensure the signal directory exists
    signal_dir = Path(get_signal_file_path(ticker, date_str, "dynamic")).parent
    signal_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate signals with both fixed and dynamic confidence
    confidence_types = ['fixed', 'dynamic']
    output_frames = {}
    
    # Initialize output frames with empty DataFrames
    for conf_type in confidence_types:
        output_frames[conf_type] = pd.DataFrame()
    
    try:
        for conf_type in confidence_types:
            try:
                if progress is not None and task_id is not None:
                    progress.update(task_id, description=f"Generating {conf_type} signals for {ticker}")
                
                # Create a copy of signals for this confidence type
                current_signals = df.copy()
                
                # Apply the appropriate confidence filter
                if conf_type == 'fixed':
                    # For fixed confidence, we force USE_DYNAMIC_CONFIDENCE=False
                    current_signals = apply_confidence_filter(
                        current_signals,
                        confidence_col='confidence',
                        signal_col='signal',
                        fixed_threshold=confidence_threshold,
                        use_dynamic_confidence=False
                    )
                    threshold_used = confidence_threshold
                    threshold_method = 'fixed'
                else:
                    # For dynamic confidence, use the default behavior
                    current_signals = apply_confidence_filter(
                        current_signals,
                        confidence_col='confidence',
                        signal_col='signal',
                        fixed_threshold=confidence_threshold,
                        use_dynamic_confidence=True
                    )
                    threshold_used = current_signals['threshold_used'].iloc[0] if 'threshold_used' in current_signals.columns else confidence_threshold
                    threshold_method = current_signals.get('threshold_method', ['dynamic'])[0]
                
                # Update the threshold information
                current_signals['threshold_used'] = threshold_used
                current_signals['threshold_method'] = threshold_method
                
                # Get the appropriate output path
                conf_output_file = get_signal_file_path(ticker, date_str, conf_type)
                output_dir = Path(conf_output_file).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Ensure we have valid signals to process
                if current_signals is None or current_signals.empty:
                    logger.warning(f"No signals generated for {ticker} with {conf_type} confidence")
                    continue
                    
                # Ensure timestamp column exists
                if 'timestamp' not in current_signals.columns:
                    logger.error(f"No timestamp column in signals for {ticker}")
                    continue
                    
                # Sort by timestamp to ensure we're getting the latest
                current_signals = current_signals.sort_values('timestamp')
                
                # Get the last timestamp from the current data
                last_timestamp = pd.to_datetime(current_signals['timestamp']).max()
                
                # Filter for the most recent data points (last 5 minutes)
                time_threshold = last_timestamp - pd.Timedelta(minutes=5)
                new_signals = current_signals[pd.to_datetime(current_signals['timestamp']) >= time_threshold]
                
                if new_signals.empty:
                    continue
                
                # Ensure output directory exists
                output_dir = Path(conf_output_file).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Prepare signals for insertion
                signals_to_insert = []
                for _, row in new_signals.iterrows():
                    signal_data = {
                        'ticker': ticker.upper(),  # Ensure consistent case
                        'timestamp': row['timestamp'].to_pydatetime() if hasattr(row['timestamp'], 'to_pydatetime') else row['timestamp'],
                        'signal': str(row['signal']).upper(),  # Ensure uppercase signal
                        'signal_type': f'ma_{conf_type}',  # e.g., 'ma_dynamic' or 'ma_fixed'
                        'confidence': float(row.get('confidence', 0.0)),
                        'reasoning': str(row.get('reasoning', ''))  # Optional field
                    }
                    # Log the signal being prepared for debugging
                    logger.debug(f"Preparing signal for {ticker}: {signal_data}")
                    signals_to_insert.append(signal_data)
                
                # Insert signals one at a time with error handling
                from core.db.crud.tickers_signals_db import insert_signal
                from core.db.deps import get_db
                from sqlalchemy.exc import SQLAlchemyError
                
                inserted_count = 0
                try:
                    # Use context manager for database session
                    with get_db() as db:
                        for signal_data in signals_to_insert:
                            try:
                                # Insert one signal at a time
                                insert_signal(db, signal_data)
                                db.commit()
                                inserted_count += 1
                                logger.debug(f"Inserted signal for {ticker} at {signal_data.get('timestamp')}")
                            except SQLAlchemyError as e:
                                db.rollback()
                                error_msg = f"Error inserting signal for {ticker} at {signal_data.get('timestamp')}: {str(e)}"
                                logger.error(error_msg, exc_info=True)
                                if progress is not None and task_id is not None:
                                    progress.print(f"[red]{error_msg}[/red]")
                except Exception as e:
                    error_msg = f"Database error for {ticker}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    if progress is not None and task_id is not None:
                        progress.print(f"[red]{error_msg}[/red]")
                
                # Log the results
                buy_count = (new_signals["signal"] == "BUY").sum()
                sell_count = (new_signals["signal"] == "SELL").sum()
                stay_count = (new_signals["signal"] == "STAY").sum()
                
                if inserted_count > 0:
                    logger.info(f"Successfully inserted {inserted_count} signals for {ticker}")
                else:
                    logger.warning(f"No signals were inserted for {ticker}")
                
                success_msg = f"✓ Processed {len(new_signals)} {conf_type} signals for {ticker} (BUY: {buy_count}, SELL: {sell_count}, STAY: {stay_count})"
                logger.info(success_msg)
                
                if progress is not None and task_id is not None:
                    progress.print(success_msg)
                
                # Store the signals in output_frames
                output_frames[conf_type] = new_signals
                
            except Exception as e:
                error_msg = f"✗ Error processing {conf_type} confidence for {ticker}: {str(e)}"
                logger.error(error_msg)
                if progress is not None and task_id is not None:
                    progress.print(f"[red]{error_msg}[/red]")
                continue
        
        # Return the signals DataFrame
        if 'dynamic' in output_frames and not output_frames['dynamic'].empty:
            return output_frames['dynamic']
        return next((df for df in output_frames.values() if not df.empty), pd.DataFrame())
    
    except Exception as e:
        logger.error(f"Error in signal generation for {ticker}: {str(e)}")
        return pd.DataFrame()

def generate_all_ma_signals(
    date: Optional[Union[str, datetime]] = None,
    short_window: int = 5,
    long_window: int = 20,
    include_reasoning: bool = True,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> Dict[str, int]:
    """
    Generate moving average signals for all tickers with dynamic confidence thresholds.
    
    This function processes each ticker, generating signals based on moving average
    crossovers, with dynamic confidence thresholds that adapt to market volatility.
    
    Args:
        date: Date for which to generate signals (YYYYMMDD format or datetime object).
              If None, uses the most recent date with data.
        short_window: Window size for the short moving average (default: 5).
        long_window: Window size for the long moving average (default: 20).
        include_reasoning: Whether to include reasoning for each signal (default: True).
        confidence_threshold: Fallback confidence threshold when dynamic threshold
                            cannot be calculated (default: 0.005).
        peak_window: Window size for peak detection (default: 12).
        peak_threshold: Threshold for peak detection (0-1, default: 0.99).
        progress: Rich Progress object for tracking progress (optional).
        task_id: Task ID for the progress bar (optional).
        
    Returns:
        Dictionary mapping ticker symbols to the number of signals generated.
        
    Note:
        The dynamic confidence threshold is calculated using either:
        - Z-score method: mean + (Z_MIN * std) of recent confidence values, or
        - Quantile method: QUANTILE_MIN percentile of recent confidence values
    """
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from core.db.deps import get_db
    from core.db.crud import get_prices_for_ticker
    
    console = Console()
    
    # Convert date to string if it's a datetime object
    if date is None:
        date_str = datetime.now().strftime("%Y%m%d")
    elif isinstance(date, datetime):
        date_str = date.strftime("%Y%m%d")
    else:
        date_str = str(date)
    
    tickers = load_tickers()
    results = {}
    
    # Set up progress bar if not provided
    progress_bar = progress
    task = task_id
    
    if progress_bar is None:
        progress_bar = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
        task = progress_bar.add_task("Generating signals...", total=len(tickers))
        progress_bar.start()
    
    # Initialize counters and trackers
    success_count = 0
    failed_tickers = []
    total_signals = 0
    
    try:
        for i, ticker in enumerate(tickers):
            if progress_bar is not None and task is not None:
                progress_bar.update(task, description=f"Processing {ticker}")
            
            try:
                # Get price data from database
                with get_db() as db:
                    prices = get_prices_for_ticker(db, ticker)
                    if not prices:
                        logger.warning(f"No price data available for {ticker} in database")
                        results[ticker] = 0
                        failed_tickers.append(ticker)
                        continue
                        
                    # Convert to DataFrame for signal generation
                    price_dicts = []
                    for p in prices:
                        try:
                            price_dicts.append({
                                'timestamp': p.timestamp,
                                'open': float(p.open) if p.open is not None else None,
                                'high': float(p.high) if p.high is not None else None,
                                'low': float(p.low) if p.low is not None else None,
                                'close': float(p.close) if p.close is not None else None,
                                'volume': int(p.volume) if p.volume is not None else 0
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Skipping invalid price data for {ticker}: {str(e)}")
                            continue
                    
                    if not price_dicts:
                        logger.warning(f"No valid price data found for {ticker}")
                        results[ticker] = 0
                        failed_tickers.append(ticker)
                        continue
                        
                    df = pd.DataFrame(price_dicts)
                    
                    # Generate signals - this will automatically save to database
                    signals = generate_ma_signals(
                        ticker=ticker,
                        date=date_str,
                        short_window=short_window,
                        long_window=long_window,
                        include_reasoning=include_reasoning,
                        confidence_threshold=confidence_threshold,
                        peak_window=peak_window,
                        peak_threshold=peak_threshold,
                        progress=progress_bar,
                        task_id=task,
                        df=df  # Pass the DataFrame directly
                    )
                    
                    # Count the number of signals (non-NaN signal values)
                    signal_count = signals['signal'].notna().sum()
                    results[ticker] = signal_count
                    total_signals += signal_count
                    success_count += 1
                    
                    if progress_bar is not None and task is not None:
                        progress_bar.print(f"✓ {ticker}: Generated {signal_count} signals")
                    
            except Exception as e:
                error_msg = f"✗ Error processing {ticker}: {str(e)}"
                if progress_bar is not None:
                    progress_bar.print(error_msg)
                else:
                    console.print(error_msg)
                results[ticker] = 0
                failed_tickers.append(ticker)
            
            # Update progress
            if progress_bar is not None and task is not None:
                progress_bar.update(task, advance=1)
    
    finally:
        # Only stop the progress bar if we created it
        if progress is None and progress_bar is not None:
            progress_bar.stop()
    
    # Print summary
    console.print("\n[bold]Signal Generation Summary:[/bold]")
    console.print(f"[green]✓ Successfully processed: {success_count} tickers")
    console.print(f"[green]✓ Total signals generated: {total_signals}[/green]")
    
    if failed_tickers:
        console.print(
            f"[red]✗ Failed to process {len(failed_tickers)} tickers: "
            f"{', '.join(failed_tickers)}[/red]"
        )
    
    return results
