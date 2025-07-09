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
    data_dir: Union[str, Path] = Path("tickers/data"),
    include_reasoning: bool = True,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> str:
    """
    Generate moving average signals from OHLCV data.
    
    Args:
        ticker (str): Ticker symbol
        date (Optional[Union[str, datetime]]): Date for the file, defaults to today
        short_window (int): Short-term moving average window
        long_window (int): Long-term moving average window
        data_dir (Union[str, Path]): Directory containing ticker data
        include_reasoning (bool): Whether to include reasoning text with signals
    
    Returns:
        str: Path to the saved signals file
    """
    # Only show debug info if we're not using a progress bar
    if progress is None:
        console.print(f"\n[yellow]=== Processing {ticker} ===[/yellow]")
    console.print(f"[yellow]Data directory (input): {data_dir}")
    
    # Ensure data_dir is a Path object
    data_dir = Path(data_dir)
    console.print(f"[yellow]Data directory (resolved): {data_dir.absolute()}")
    console.print(f"[yellow]Data directory exists: {data_dir.exists()}")
    
    # List all files in the data directory for debugging
    if data_dir.exists():
        console.print(f"[yellow]Contents of {data_dir}:")
        for f in data_dir.glob('*'):
            console.print(f"  - {f.name} (dir: {f.is_dir()})")
    # Use today's date if not provided
    if date is None:
        date = datetime.now()
    
    # Convert string date to datetime if needed
    if isinstance(date, str):
        date = pd.to_datetime(date)
    
    # Format the date as YYYYMMdd
    date_str = date.strftime("%Y%m%d")
    
    # Create the file paths
    ticker_data_dir = data_dir / ticker
    signals_dir = data_dir.parent / "signals" / ticker
    
    console.print(f"[yellow]Ticker data directory: {ticker_data_dir.absolute()}")
    console.print(f"[yellow]Ticker data directory exists: {ticker_data_dir.exists()}")
    
    # Ensure signals directory exists
    signals_dir.mkdir(parents=True, exist_ok=True)
    
    # Note: The files are saved as YYYYMMDD_TICKER_.csv (with an extra underscore before .csv)
    input_file = ticker_data_dir / f"{date_str}_{ticker}_.csv"
    output_file = signals_dir / f"{date_str}_{ticker}_signals.csv"
    
    console.print(f"[yellow]Looking for input file: {input_file.absolute()}")
    console.print(f"[yellow]Input file exists: {input_file.exists()}")
    
    if ticker_data_dir.exists():
        console.print(f"[yellow]Files in {ticker_data_dir}:")
        for f in ticker_data_dir.glob('*'):
            console.print(f"  - {f.name} (size: {f.stat().st_size} bytes)")
    
    # Debug output
    console.print(f"[yellow]Looking for data file: {input_file.absolute()}")
    console.print(f"[yellow]Current working directory: {Path.cwd()}")
    console.print(f"[yellow]File exists: {input_file.exists()}")
    console.print(f"[yellow]Parent directory exists: {ticker_data_dir.exists()}")
    if ticker_data_dir.exists():
        files = list(ticker_data_dir.glob('*'))
        console.print(f"[yellow]Files in directory {ticker_data_dir}:")
        for f in files:
            console.print(f"[yellow]  - {f.name} (exists: {f.exists()}, is_file: {f.is_file()})")
    
    # Check if input file exists
    if not input_file.exists():
        console.print(f"[red]ERROR: File not found: {input_file.absolute()}")
        console.print(f"[red]Current working directory: {Path.cwd()}")
        console.print(f"[red]Trying to find file with pattern: {ticker_data_dir}/{date_str}_*.csv")
        
        # Try to find any matching files
        matching_files = list(ticker_data_dir.glob(f"{date_str}_*.csv"))
        if matching_files:
            console.print("[yellow]Found these matching files:")
            for f in matching_files:
                console.print(f"  - {f.name}")
        else:
            console.print("[red]No matching files found!")
        
        raise FileNotFoundError(f"OHLCV data file not found: {input_file.absolute()}")
    
    console.print(f"[green]Found data file: {input_file.absolute()}")
    
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
    data_dir: Union[str, Path] = Path("tickers/data"),
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
    
    # Debug output
    console.print(f"[yellow]Scanning for ticker data in: {data_dir.absolute()}")
    console.print(f"[yellow]Data directory exists: {data_dir.exists()}")
    
    # Get all ticker directories
    ticker_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    tickers = [d.name for d in ticker_dirs]
    
    console.print(f"[yellow]Found {len(tickers)} ticker directories: {tickers}")
    
    # Initialize counters
    success_count = 0
    failed_tickers = []
    
    # Ensure we have ticker directories
    if not tickers:
        console.print("[red]No ticker directories found!")
        console.print(f"[red]Data directory: {data_dir.absolute()}")
        console.print("[red]Contents of data directory:")
        for f in data_dir.glob('*'):
            console.print(f"  - {f.name} (dir: {f.is_dir()})")
    
    results = {}
    
    # Create a new progress bar if one wasn't provided
    progress_created = False
    if progress is None:
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
        progress.start()
        progress_created = True
    
    # Add a new task if task_id wasn't provided
    if task_id is None:
        task = progress.add_task(f"Generating signals for {len(tickers)} tickers...", total=len(tickers))
    else:
        task = task_id
    
    for ticker in tickers:
        try:
            # Check if OHLCV data exists for this ticker and date
            # File format is YYYYMMDD_TICKER_.csv (with an extra underscore at the end)
            input_file = data_dir / ticker / f"{date_str}_{ticker}_.csv"
            if not input_file.exists():
                console.print(f"[yellow]Skipping {ticker}: No data file found at {input_file.absolute()}[/yellow]")
                # Debug: List files in the directory to help with troubleshooting
                ticker_dir = data_dir / ticker
                if ticker_dir.exists():
                    files = list(ticker_dir.glob("*.csv"))
                    if files:
                        console.print(f"[yellow]Found these files in {ticker_dir}:")
                        for f in files:
                            console.print(f"  - {f.name}")
                continue
            
            # Generate signals with the progress bar
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
                progress=progress,
                task_id=task
            )          
            results[ticker] = file_path
            success_count += 1
            
            if progress is not None:
                progress.update(task, advance=1)
        
        except Exception as e:
            console.print(f"[red]Error processing {ticker}: {str(e)}[/red]")
            failed_tickers.append(ticker)
            if progress is not None:
                progress.update(task, advance=1)
    
    # Print summary
    if progress_created:
        progress.stop()
    
    console.print(f"[bold green]Signal generation complete for all tickers on {date_str}[/bold green]")
    if success_count > 0:
        console.print(f"[green]Successfully processed {success_count} out of {len(tickers)} tickers[/green]")
    if failed_tickers:
        console.print(f"[red]Failed to process {len(failed_tickers)} tickers: {failed_tickers}[/red]")
    
    return results
