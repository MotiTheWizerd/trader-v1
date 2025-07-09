#!/usr/bin/env python
"""
Script to generate moving average signals from OHLCV data.

Generates signals based on moving average crossover with confidence filtering and peak detection:
- BUY when short-term MA > long-term MA with sufficient confidence
- SELL when short-term MA < long-term MA with sufficient confidence AND price is near a recent peak
- STAY otherwise or when confidence is too low or price is not near a peak

Confidence is calculated as: abs(ma_short - ma_long) / ma_long
Peak detection: A price is in a peak zone if it's within a threshold of the recent maximum
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add parent directory to path to allow importing from core
sys.path.append(str(Path(__file__).parent.parent))

from core.signals.moving_average import generate_ma_signals, generate_all_ma_signals

# Initialize rich console
console = Console()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate moving average signals from OHLCV data"
    )
    parser.add_argument(
        "--ticker", 
        type=str, 
        help="Ticker symbol (leave empty to process all available tickers)"
    )
    parser.add_argument(
        "--date", 
        type=str, 
        help="Date in YYYY-MM-DD format (defaults to today)"
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
        "--data-dir", 
        type=str, 
        default="tickers/data", 
        help="Directory containing ticker data (default: tickers/data)"
    )
    parser.add_argument(
        "--no-reasoning", 
        action="store_true", 
        help="Exclude reasoning text from signals"
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
    
    args = parser.parse_args()
    
    # Process date argument
    date = None
    if args.date:
        try:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            console.print("[bold red]Error: Invalid date format. Use YYYY-MM-DD.[/bold red]")
            return 1
    
    # Process data directory
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        console.print(f"[bold red]Error: Data directory {data_dir} does not exist.[/bold red]")
        return 1
    
    try:
        # Generate signals for a single ticker or all tickers
        if args.ticker:
            file_path = generate_ma_signals(
                ticker=args.ticker,
                date=date,
                short_window=args.short_window,
                long_window=args.long_window,
                data_dir=data_dir,
                include_reasoning=not args.no_reasoning,
                confidence_threshold=args.confidence_threshold,
                peak_window=args.peak_window,
                peak_threshold=args.peak_threshold
            )
            
            console.print(f"[bold green]Successfully generated signals for {args.ticker}[/bold green]")
            console.print(f"[blue]Output saved to: {file_path}[/blue]")
        else:
            results = generate_all_ma_signals(
                date=date,
                short_window=args.short_window,
                long_window=args.long_window,
                data_dir=data_dir,
                include_reasoning=not args.no_reasoning,
                confidence_threshold=args.confidence_threshold,
                peak_window=args.peak_window,
                peak_threshold=args.peak_threshold
            )
            
            # Display results in a table
            table = Table(title="Signal Generation Results")
            table.add_column("Ticker", style="cyan")
            table.add_column("Output File", style="green")
            
            for ticker, file_path in results.items():
                table.add_row(ticker, file_path)
            
            console.print(table)
            
        return 0
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
