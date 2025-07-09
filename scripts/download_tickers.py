#!/usr/bin/env python
"""
Script to download ticker data using the core data module.
Displays progress and results using the UI module.

Follows the project structure rules:
- Each ticker's data is saved by date in: tickers/data/<TICKER>/<YYYYMMdd>.csv
- UI components are kept separate from business logic
- Uses rich library for terminal output
"""
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich import print as rprint

from core.data import (
    download_ticker_data,  # Still needed for preview
    load_tickers,
    process_ticker_data,
    process_all_tickers
)
from ui.data_display import (
    display_download_progress,
    display_download_summary,
    display_ticker_data_preview,
    display_error
)

console = Console()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Download ticker data")
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)",
        default=None
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)",
        default=None
    )
    parser.add_argument(
        "--period",
        type=str,
        help="Period to download (e.g., 1d, 5d, 1mo, 3mo, 1y, max)",
        default="20d"
    )
    parser.add_argument(
        "--interval",
        type=str,
        help="Data interval (e.g., 1d, 1h, 5m)",
        default="5m"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date to use for file naming (YYYY-MM-DD), defaults to today",
        default=None
    )
    parser.add_argument(
        "--tickers",
        type=str,
        nargs="+",
        help="Specific tickers to download (default: all from tickers.json)",
        default=None
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the downloaded data"
    )
    return parser.parse_args()


def main():
    """Main function to download ticker data."""
    args = parse_args()
    
    # Get tickers to download
    if args.tickers:
        tickers = args.tickers
    else:
        tickers = load_tickers()
    
    if not tickers:
        rprint("[bold red]No tickers found to download!")
        return
    
    # Determine the save date
    save_date = None
    if args.date:
        try:
            save_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            console.print(f"[bold red]Invalid date format: {args.date}. Using date from data range.")
    # If --date is not provided, the downloader will use end_date or start_date for the filename
    
    # Display information using rich
    console.print(f"[bold green]Downloading data for {len(tickers)} tickers")
    console.print(f"[bold blue]Tickers: {', '.join(tickers)}")
    if args.start_date and args.end_date:
        console.print(f"[bold yellow]Date range: {args.start_date} to {args.end_date}")
    elif args.period:
        console.print(f"[bold yellow]Period: {args.period}")
    console.print(f"[bold cyan]Interval: {args.interval}")
    
    # Setup progress tracking
    progress, total_task, ticker_tasks = display_download_progress(tickers)
    
    # Start timing
    start_time = time.time()
    
    # Process all tickers using the pipeline
    results = {}
    
    with progress:
        for ticker in tickers:
            try:
                # Process ticker data through the pipeline (download, clean, save)
                file_path = process_ticker_data(
                    ticker,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    interval=args.interval,
                    period=args.period if not args.start_date else None,
                    save_date=save_date
                )
                results[ticker] = file_path
                
                # Update progress
                progress.update(ticker_tasks[ticker], completed=1)
                progress.update(total_task, advance=1)
                
                # Preview data if requested
                if args.preview:
                    # Download data again just for preview
                    preview_data = download_ticker_data(
                        ticker,
                        start_date=args.start_date,
                        end_date=args.end_date,
                        interval=args.interval,
                        period=args.period if not args.start_date else None
                    )
                    display_ticker_data_preview(ticker, preview_data)
                
            except ValueError as e:
                # Handle specific ValueError exceptions (like future dates or validation errors)
                console.print(f"[bold red]Error processing {ticker}: {str(e)}")
                # Add to results with error status
                results[ticker] = "ERROR"
                progress.update(ticker_tasks[ticker], completed=1)
                progress.update(total_task, advance=1)
            except Exception as e:
                # Handle other exceptions
                console.print(f"[bold red]Unexpected error processing {ticker}: {str(e)}")
                # Add to results with error status
                results[ticker] = "ERROR"
                progress.update(ticker_tasks[ticker], completed=1)
                progress.update(total_task, advance=1)
                
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Display summary
    display_download_summary(results, elapsed_time)


if __name__ == "__main__":
    main()
