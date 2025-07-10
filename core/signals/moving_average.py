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
from rich.progress import Progress, TaskProgressColumn, TimeRemainingColumn, TextColumn, BarColumn

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
    task_id: Optional[int] = None
) -> Optional[str]:
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
    
    Returns:
        Optional[str]: Path to the saved signals file, or None if generation failed
    """
    # Only show debug info if we're not using a progress bar
    if progress is None:
        console.print(f"\n[yellow]=== Processing {ticker} ===[/yellow]")
    
    # Handle date formatting - accept both datetime and string in YYYYMMDD or YYYYMMDDHHMM format
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
    
    # Initialize the _is_new_data column early to prevent KeyError
    df = load_historical_data(ticker)
    if df is None or df.empty:
        logger.error(f"No historical data found for {ticker}")
        return None
    
    # Initialize _is_new_data as True for all rows by default
    df['_is_new_data'] = True
        
    # Try to find existing signals to determine which data is new
    signal_dir = Path(get_signal_file_path(ticker, "*", "dynamic")).parent
    signal_files = list(signal_dir.glob(f"*{ticker}*dynamic*.csv"))
    latest_signal_file = None
    
    if signal_files:
        try:
            # Find the most recent signal file
            latest_signal_file = max(signal_files, key=lambda x: x.stat().st_mtime)
            # Read the last timestamp from the signal file
            existing_signals = pd.read_csv(latest_signal_file)
            if 'timestamp' in existing_signals.columns and not existing_signals.empty:
                last_timestamp = pd.to_datetime(existing_signals['timestamp'].iloc[-1])
                # Update _is_new_data based on timestamp comparison
                df['_is_new_data'] = (df.index > last_timestamp)
                if not df['_is_new_data'].any():
                    logger.info(f"No new data to process for {ticker} since last run")
                    return str(latest_signal_file)  # Return existing file if no new data
        except Exception as e:
            logger.warning(f"Error reading existing signals for {ticker}: {e}")
            # If there's an error, process all data as new
            df['_is_new_data'] = True
    
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
    output_files = {}
    
    for conf_type in confidence_types:
        try:
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
            
            try:
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
                
                if not new_signals.empty:
                    # Ensure output directory exists
                    output_dir = Path(conf_output_file).parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save the new signals
                    new_signals.to_csv(conf_output_file, index=False)
                    output_files[conf_type] = conf_output_file
                    
                    # Count signals for logging
                    buy_count = (new_signals["signal"] == "BUY").sum()
                    sell_count = (new_signals["signal"] == "SELL").sum()
                    stay_count = (new_signals["signal"] == "STAY").sum()
                    
                    logger.info(f"Saved {len(new_signals)} new {conf_type} signals for {ticker}:")
                    logger.info(f"  Timestamp range: {new_signals['timestamp'].min()} to {new_signals['timestamp'].max()}")
                    logger.info(f"  BUY: {buy_count}, SELL: {sell_count}, STAY: {stay_count}")
                    
                    # If we saved signals, make sure the output file exists
                    if not Path(conf_output_file).exists():
                        logger.error(f"Failed to save signals to {conf_output_file}")
                        continue
                else:
                    logger.warning(f"No new signals to save for {ticker} in the last 5 minutes")
                    # If we have existing signals, use the latest file
                    if latest_signal_file and latest_signal_file.exists():
                        output_files[conf_type] = str(latest_signal_file)
                
            except Exception as e:
                logger.error(f"Error saving {conf_type} signals for {ticker}: {str(e)}")
                continue
            
            # Calculate statistics for this confidence type
            buy_count = (current_signals["signal"] == "BUY").sum()
            sell_count = (current_signals["signal"] == "SELL").sum()
            stay_count = (current_signals["signal"] == "STAY").sum()
            
            # Only show completion message if we're not using a progress bar
            if progress is None:
                console.print(f"\n[bold]{conf_type.capitalize()} confidence signals:[/bold]")
                console.print(f"  [green]BUY signals: {buy_count}[/green]")
                console.print(f"  [red]SELL signals: {sell_count}[/red]")
                console.print(f"  [yellow]STAY signals: {stay_count}[/yellow]")
                console.print(f"  [blue]Threshold: {threshold_used:.6f} ({threshold_method})[/blue]")
                console.print(f"  [cyan]Saved to: {conf_output_file}[/cyan]")
        except Exception as e:
            console.print(f"[red]Error processing {conf_type} confidence for {ticker}: {str(e)}[/red]")
            continue
    
    # Return the dynamic path for backward compatibility, or the first available path if dynamic failed
    return output_files.get('dynamic', next(iter(output_files.values()), ''))

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
) -> Dict[str, str]:
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
        Dictionary mapping ticker symbols to their output file paths.
        
    Note:
        The dynamic confidence threshold is calculated using either:
        - Z-score method: mean + (Z_MIN * std) of recent confidence values, or
        - Quantile method: QUANTILE_MIN percentile of recent confidence values
        
        The method and parameters can be configured in core/config/constants.py
    """
    from typing import Dict  # Import Dict for return type annotation
    
    # Get list of all tickers
    try:
        tickers = get_all_tickers()
    except Exception as e:
        console.print(f"[red]Error getting tickers: {str(e)}[/red]")
        return {}
        
    results: Dict[str, str] = {}
    success_count = 0
    failed_tickers: List[str] = []
    
    if not tickers:
        console.print("[yellow]No tickers found in the data directory.[/yellow]")
        return results
    
    # Process each ticker
    for i, ticker in enumerate(tickers):
        if progress and task_id is not None:
            progress.update(task_id, advance=1, description=f"Processing {ticker}")
        else:
            console.print(f"\n[bold blue]=== Processing {ticker} ===[/bold blue]")
        
        try:
            try:
                output_file = generate_ma_signals(
                    ticker=ticker,
                    date=date,
                    short_window=short_window,
                    long_window=long_window,
                    include_reasoning=include_reasoning,
                    confidence_threshold=confidence_threshold,
                    peak_window=peak_window,
                    peak_threshold=peak_threshold,
                    progress=progress,
                    task_id=task_id
                )
                
                # Check if we got a valid output file path
                if output_file and Path(output_file).exists():
                    results[ticker] = str(output_file)
                    success_count += 1
                    
                    # Log the successful generation
                    if progress:
                        progress.console.print(f"[green]✓ Generated signals for {ticker}[/green]")
                    else:
                        console.print(f"[green]✓ Generated signals for {ticker}[/green]")
                else:
                    # If no new signals but we have a previous file, use that
                    latest_signal_file = get_latest_signal_file(ticker, date)
                    if latest_signal_file and latest_signal_file.exists():
                        results[ticker] = str(latest_signal_file)
                        success_count += 1
                        if progress:
                            progress.console.print(f"[yellow]⚠ Using existing signals for {ticker} (no new data)[/yellow]")
                        else:
                            console.print(f"[yellow]⚠ Using existing signals for {ticker} (no new data)[/yellow]")
                    else:
                        failed_tickers.append(ticker)
                        if progress:
                            progress.console.print(f"[yellow]⚠ No signals generated for {ticker} (no data)[/yellow]")
                        else:
                            console.print(f"[yellow]⚠ No signals generated for {ticker} (no data)[/yellow]")
            except Exception as e:
                error_msg = f"Error processing {ticker}: {str(e)}"
                failed_tickers.append(ticker)
                if progress:
                    progress.console.print(f"[red]{error_msg}[/red]")
                else:
                    console.print(f"[red]{error_msg}[/red]")
                
        except Exception as e:
            error_msg = f"Error processing {ticker}: {str(e)}"
            if progress:
                progress.console.print(f"[red]{error_msg}[/red]")
            else:
                console.print(f"[red]{error_msg}[/red]")
            failed_tickers.append(ticker)
    
    # Print summary
    console.print("\n[bold]Signal Generation Summary:[/bold]")
    console.print(f"[green]✓ Successfully processed: {success_count} tickers[/green]")
    
    if failed_tickers:
        console.print(
            f"[red]✗ Failed to process {len(failed_tickers)} tickers: "
            f"{', '.join(failed_tickers)}[/red]"
        )
    
    return results
