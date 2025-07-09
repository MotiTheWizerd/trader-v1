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
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Initialize rich console
console = Console()

def generate_ma_signals(
    ticker: str,
    date: Optional[Union[str, datetime]] = None,
    short_window: int = 5,
    long_window: int = 20,
    data_dir: Path = Path("tickers/data"),
    include_reasoning: bool = True,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    progress: Optional[Progress] = None
) -> str:
    """
    Generate moving average signals from OHLCV data.
    
    Args:
        ticker (str): Ticker symbol
        date (Optional[Union[str, datetime]]): Date for the file, defaults to today
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        data_dir (Path): Directory containing ticker data
        include_reasoning (bool): Whether to include reasoning text with signals
    
    Returns:
        str: Path to the saved signals file
    """
    # Use today's date if not provided
    if date is None:
        date = datetime.now()
    
    # Convert string date to datetime if needed
    if isinstance(date, str):
        date = pd.to_datetime(date)
    
    # Format the date as YYYYMMdd
    date_str = date.strftime("%Y%m%d")
    
    # Create the file paths
    ticker_dir = data_dir / ticker
    input_file = ticker_dir / f"{date_str}.csv"
    output_file = ticker_dir / f"{date_str}_signals.csv"
    
    # Check if input file exists
    if not input_file.exists():
        raise FileNotFoundError(f"OHLCV data file not found: {input_file}")
    
    # Load OHLCV data
    console.print(f"[bold blue]Loading OHLCV data for {ticker} on {date_str}...[/bold blue]")
    df = pd.read_csv(input_file)
    
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
    data_dir: Path = Path("tickers/data"),
    include_reasoning: bool = True,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    use_single_progress: bool = True
) -> Dict[str, str]:
    """
    Generate moving average signals for all tickers with available data.
    
    Args:
        date (Optional[Union[str, datetime]]): Date for the file, defaults to today
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        data_dir (Path): Directory containing ticker data
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
    
    # Get all ticker directories
    ticker_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    tickers = [d.name for d in ticker_dirs]
    
    results = {}
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"Generating signals for {len(tickers)} tickers...", total=len(tickers))
        
        for ticker in tickers:
            try:
                # Check if OHLCV data exists for this ticker and date
                input_file = data_dir / ticker / f"{date_str}.csv"
                if not input_file.exists():
                    console.print(f"[yellow]Skipping {ticker}: No data for {date_str}[/yellow]")
                    continue
                
                # Generate signals - pass the progress bar if using a single one
                file_path = generate_ma_signals(
                    ticker=ticker,
                    date=date,
                    short_window=short_window,
                    long_window=long_window,
                    data_dir=data_dir,
                    include_reasoning=include_reasoning,
                    confidence_threshold=confidence_threshold,
                    peak_window=peak_window,
                    peak_threshold=peak_threshold,
                    progress=progress if use_single_progress else None
                )
                results[ticker] = file_path
            except Exception as e:
                console.print(f"[bold red]Error generating signals for {ticker}: {e}[/bold red]")
            
            progress.update(task, advance=1)
    
    # Print summary
    console.print(f"[bold green]Signal generation complete for all tickers on {date_str}[/bold green]")
    console.print(f"[green]Successfully processed {len(results)} out of {len(tickers)} tickers[/green]")
    
    return results
