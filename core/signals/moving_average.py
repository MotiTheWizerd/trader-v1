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
from pathlib import Path
from typing import Optional, Union, List, Dict, Tuple, Any
import json
import numpy as np
import pandas as pd
from datetime import datetime

from rich.progress import (
    Progress, 
    TextColumn, 
    BarColumn, 
    TaskProgressColumn,
    TimeRemainingColumn
)

from core.config import (
    get_ticker_data_path,
    get_signal_file_path,
    console  # Use the configured console
)
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
    
    # Convert date to YYYYMMDD format
    if date is None:
        date_str = datetime.now().strftime("%Y%m%d")
    elif isinstance(date, datetime):
        date_str = date.strftime("%Y%m%d")
    else:
        # Handle string date, remove any non-numeric characters
        date_str = ''.join(c for c in str(date) if c.isdigit())
        # Ensure we have at least 8 digits (YYYYMMDD)
        if len(date_str) < 8:
            date_str = datetime.now().strftime("%Y%m%d")
        else:
            # Take first 8 digits in case there's extra
            date_str = date_str[:8]
    
    # Get file paths using the configuration
    input_file = Path(get_ticker_data_path(ticker, date_str))
    output_file = Path(get_signal_file_path(ticker, date_str))
    
    # Debug output
    if progress is None:
        console.print(f"[yellow]Looking for input file: {input_file.absolute()}")
        console.print(f"[yellow]Input file exists: {input_file.exists()}")
        console.print(f"[yellow]Current working directory: {Path.cwd()}")
    
    # Check if input file exists
    if not input_file.exists():
        console.print(f"[red]Input file not found: {input_file}")
        return None
        
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Debug: List files in the input file's parent directory
    input_dir = input_file.parent
    if input_dir.exists():
        files = list(input_dir.glob('*'))
        if progress is None:
            console.print(f"[yellow]Files in directory {input_dir}:")
            for f in files:
                console.print(f"  - {f.name} (size: {f.stat().st_size} bytes)")
    else:
        console.print(f"[red]Input directory does not exist: {input_dir}")
        return None

    # Read the OHLCV data
    try:
        df = pd.read_csv(input_file)
        if progress is None:
            console.print(f"[green]Successfully read {len(df)} rows from {input_file}")
    except Exception as e:
        console.print(f"[red]Error reading {input_file}: {e}")
        return None

    # Ensure timestamp column is properly formatted
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
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
    
    # Apply confidence filter and get the masks
    df = apply_confidence_filter(
        df,
        confidence_col='confidence',
        signal_col='signal',
        window=100,  # Look back window for dynamic threshold
        fallback_threshold=confidence_threshold,  # Fallback minimum confidence
        z_min=2.0,  # For z-score method
        quantile_min=0.9,  # For quantile method
        use_quantile=False  # Use z-score method by default
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
    
    # Save signals to CSV
    df.to_csv(output_file, index=False)
    
    # Print summary
    buy_count = df["signal"].value_counts().get("BUY", 0)
    sell_count = df["signal"].value_counts().get("SELL", 0)
    stay_count = df["signal"].value_counts().get("STAY", 0)
    
    # Calculate how many signals were downgraded due to low confidence or not being in peak zone
    low_confidence_count = len(df[mask_low_confidence])
    not_peak_count = len(df[mask_sell_not_peak & ~mask_low_confidence])
    
    # Only show completion message if we're not using a progress bar
    if progress is None:
        console.print(f"[bold green]Signal generation complete for {ticker} on {date_str}[/bold green]")
        console.print(f"[green]BUY signals: {buy_count}[/green]")
        console.print(f"[red]SELL signals: {sell_count}[/red]")
        console.print(f"[yellow]STAY signals: {stay_count}[/yellow]")
        console.print(f"[blue]Signals downgraded: {low_confidence_count} due to low confidence, {not_peak_count} SELLs not near peaks[/blue]")
        console.print(f"[blue]Output saved to: {output_file}[/blue]")
    
    return str(output_file)

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
            if output_file:
                results[ticker] = str(output_file)
                success_count += 1
            else:
                failed_tickers.append(ticker)
                
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
