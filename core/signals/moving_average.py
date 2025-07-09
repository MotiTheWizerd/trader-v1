"""
Moving Average Signal Generator Module.

This module generates trading signals based on moving average crossover strategy:
- BUY when short-term MA crosses above long-term MA with sufficient confidence
- SELL when short-term MA crosses below long-term MA with sufficient confidence AND price is near a recent peak
- STAY otherwise or when insufficient data or low confidence

Confidence is calculated as the normalized absolute difference between the moving averages:
    confidence = abs(ma_short - ma_long) / ma_long

Peak detection is used to validate SELL signals, ensuring they only trigger when price is
near a local maximum (within a configurable percentage threshold).

Signals with low confidence or SELL signals not near peaks are downgraded to STAY to reduce false positives.
"""
import os
from pathlib import Path
from typing import Optional, Union, Dict, Any
import pandas as pd
from datetime import datetime
import json
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Import configuration
from core.config import (
    get_ticker_data_path,
    get_signal_file_path,
    console  # Use the configured console
)

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
    Generate moving average signals from OHLCV data.
    
    Args:
        ticker (str): Ticker symbol
        date (Optional[Union[str, datetime]]): Date for the file, defaults to today
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        include_reasoning (bool): Whether to include reasoning text with signals
    
    Returns:
        Optional[str]: Path to the saved signals file, or None if generation failed
    """
    # Only show debug info if we're not using a progress bar
    if progress is None:
        console.print(f"\n[yellow]=== Processing {ticker} ===[/yellow]")
    
    # Use today's date if not provided
    if date is None:
        date = datetime.now()
    
    # Convert date to string if it's a datetime object
    if isinstance(date, datetime):
        date_str = date.strftime("%Y%m%d")
    else:
        date_str = date or datetime.now().strftime("%Y%m%d")
    
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
            BarColumn(),
            TaskProgressColumn(),
            console=console
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
    console.print("[bold blue]Generating signals with confidence filtering and peak detection...[/bold blue]")
    
    # Calculate confidence as normalized absolute distance between MAs
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
    
    # Apply confidence filtering
    mask_low_confidence = (df["confidence"] < confidence_threshold) & ~mask_insufficient
    df.loc[mask_low_confidence, "signal"] = "STAY"
    
    # Apply peak zone filtering for SELL signals
    mask_sell_not_peak = (df["signal"] == "SELL") & ~df["is_peak_zone"]
    df.loc[mask_sell_not_peak, "signal"] = "STAY"
    
    # Add reasoning if requested
    if include_reasoning:
        df["reasoning"] = ""
        df.loc[mask_buy & ~mask_low_confidence, "reasoning"] = "Short-term MA above long-term MA with sufficient confidence"
        df.loc[mask_sell & ~mask_low_confidence & df["is_peak_zone"], "reasoning"] = "Short-term MA below long-term MA with sufficient confidence, near local price peak"
        df.loc[mask_low_confidence, "reasoning"] = f"Signal confidence below threshold ({confidence_threshold:.3f})"
        df.loc[mask_sell_not_peak & ~mask_low_confidence, "reasoning"] = "SELL rejected: price not near recent peak"
        df.loc[mask_insufficient, "reasoning"] = "Insufficient data for MA calculation"
    
    # Select columns for output
    columns = ["timestamp", "close", "ma_short", "ma_long", "confidence", "signal", "recent_max", "is_peak_zone"]
    if include_reasoning:
        columns.append("reasoning")
    
    signals_df = df[columns]
    
    # Save signals to CSV
    signals_df.to_csv(output_file, index=False)
    
    # Print summary
    buy_count = signals_df["signal"].value_counts().get("BUY", 0)
    sell_count = signals_df["signal"].value_counts().get("SELL", 0)
    stay_count = signals_df["signal"].value_counts().get("STAY", 0)
    
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
    Generate moving average signals for all tickers with available data.
    
    Args:
        date (Optional[Union[str, datetime]]): Date for the file, defaults to today
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        include_reasoning (bool): Whether to include reasoning text with signals
    
    Returns:
        Dict[str, str]: Dictionary mapping ticker symbols to their signal file paths
    """
    # Use today's date if not provided
    if date is None:
        date = datetime.now()
    
    # Convert string date to datetime if needed
    if isinstance(date, str):
        date = pd.to_datetime(date)
    
    # Format the date as YYYYMMdd
    date_str = date.strftime("%Y%m%d")
    
    # Get the project root directory (one level up from core/signals)
    project_root = Path(__file__).parent.parent.parent
    tickers_file = project_root / "tickers.json"
    
    console.print(f"[yellow]Loading tickers from: {tickers_file.absolute()}")
    
    if not tickers_file.exists():
        console.print(f"[red]Tickers file not found: {tickers_file.absolute()}")
        console.print(f"[yellow]Current working directory: {Path.cwd()}")
        console.print(f"[yellow]Contents of project root: {[f.name for f in project_root.glob('*')]}")
        return {}
    
    try:
        with open(tickers_file, 'r') as f:
            tickers_data = json.load(f)
            tickers = tickers_data.get('tickers', [])
            
        if not tickers:
            console.print("[yellow]No tickers found in tickers.json")
            return {}
            
        console.print(f"[green]Found {len(tickers)} tickers in tickers.json")
        
    except Exception as e:
        console.print(f"[red]Error loading tickers: {e}")
        return {}
    
    # Initialize counters
    success_count = 0
    failed_tickers = []
    results = {}
    
    # Process each ticker
    for ticker in tickers:
        try:
            # Generate signals
            signal_path = generate_ma_signals(
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
            
            if signal_path:
                results[ticker] = signal_path
                success_count += 1
            else:
                failed_tickers.append(ticker)
                
            if progress is not None and task_id is not None:
                progress.update(task_id, advance=1)
        
        except Exception as e:
            console.print(f"[red]Error processing {ticker}: {str(e)}[/red]")
            failed_tickers.append(ticker)
            if progress is not None and task_id is not None:
                progress.update(task_id, advance=1)
    
    # Print summary
    console.print(f"\n[bold]Signal Generation Summary for {date_str}:[/bold]")
    console.print(f"[green]✓ Successfully processed: {success_count} tickers")
    
    if failed_tickers:
        console.print(f"[red]✗ Failed to process {len(failed_tickers)} tickers: {', '.join(failed_tickers)}")
    
    # Return results only for successful generations
    return {k: v for k, v in results.items() if v is not None}
