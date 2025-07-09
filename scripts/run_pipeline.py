#!/usr/bin/env python
"""
Trading Signal Pipeline Runner

This script runs the complete trading signal pipeline:
1. Downloads the latest ticker data
2. Generates moving average signals with confidence filtering and peak detection

The pipeline processes all tickers defined in tickers.json.
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directory to path to allow importing from core
sys.path.append(str(Path(__file__).parent.parent))

from core.data.downloader import download_all_tickers
from core.signals.moving_average import generate_all_ma_signals

# Initialize rich console
console = Console()

def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the complete trading signal pipeline"
    )
    parser.add_argument(
        "--date", 
        type=str, 
        help="Date in YYYY-MM-DD format (defaults to today)"
    )
    parser.add_argument(
        "--interval", 
        type=str, 
        default="5m", 
        help="Data interval (default: 5m)"
    )
    parser.add_argument(
        "--period", 
        type=str, 
        default="20d", 
        help="Period to download (default: 20d)"
    )
    parser.add_argument(
        "--short-window", 
        type=int, 
        default=5, 
        help="Short-term moving average window (default: 5)"
    )
    parser.add_argument(
        "--long-window", 
        type=int, 
        default=20, 
        help="Long-term moving average window (default: 20)"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.005,
        help="Threshold for signal confidence (default: 0.005 or 0.5%%)"
    )
    parser.add_argument(
        "--peak-window",
        type=int,
        default=12,
        help="Window size for peak detection (default: 12 periods)"
    )
    parser.add_argument(
        "--peak-threshold",
        type=float,
        default=0.99,
        help="Threshold for peak zone detection (default: 0.99 or 99%% of recent max)"
    )
    parser.add_argument(
        "--no-reasoning", 
        action="store_true", 
        help="Exclude reasoning text from signals"
    )
    
    args = parser.parse_args()
    
    # Process date argument
    date = None
    if args.date:
        try:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            console.print("[bold red]Error: Invalid date format. Use YYYY-MM-DD.[/bold red]")
            return 1
    else:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    
    try:
        # Display pipeline start
        console.print(Panel(
            f"[bold green]Starting Trading Signal Pipeline for {date_str}[/bold green]",
            expand=False
        ))
        
        # Step 1: Download ticker data
        console.print("\n[bold blue]Step 1: Downloading ticker data...[/bold blue]")
        download_results = download_all_tickers(
            end_date=date,
            interval=args.interval,
            period=args.period,
            save_date=date
        )
        
        # Display download results
        download_table = Table(title=f"Data Download Results for {date_str}")
        download_table.add_column("Ticker", style="cyan")
        download_table.add_column("File Path", style="green")
        
        for ticker, file_path in download_results.items():
            download_table.add_row(ticker, file_path)
        
        console.print(download_table)
        
        # Step 2: Generate signals
        console.print("\n[bold blue]Step 2: Generating moving average signals...[/bold blue]")
        signal_results = generate_all_ma_signals(
            date=date,
            short_window=args.short_window,
            long_window=args.long_window,
            include_reasoning=not args.no_reasoning,
            confidence_threshold=args.confidence_threshold,
            peak_window=args.peak_window,
            peak_threshold=args.peak_threshold,
            use_single_progress=True
        )
        
        # Display signal results
        signal_table = Table(title=f"Signal Generation Results for {date_str}")
        signal_table.add_column("Ticker", style="cyan")
        signal_table.add_column("Signal File", style="green")
        
        for ticker, file_path in signal_results.items():
            signal_table.add_row(ticker, file_path)
        
        console.print(signal_table)
        
        # Display pipeline completion
        console.print(Panel(
            f"[bold green]Trading Signal Pipeline Completed Successfully for {date_str}[/bold green]",
            expand=False
        ))
        
        return 0
    
    except Exception as e:
        console.print(f"[bold red]Pipeline Error: {e}[/bold red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
