"""
UI components for displaying ticker data download information.
Uses rich library for terminal output.
"""
from typing import Dict, List, Any
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from datetime import datetime

console = Console()


def display_download_progress(tickers: List[str]) -> tuple:
    """
    Create and display a progress bar for ticker data download.
    
    Args:
        tickers (List[str]): List of ticker symbols to download
    
    Returns:
        tuple: (progress, total_task, ticker_tasks) - Progress object and task IDs
    """
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
    )
    
    # Create a task for overall progress
    total_task = progress.add_task("Downloading tickers...", total=len(tickers))
    
    # Create tasks for each ticker
    ticker_tasks = {}
    for ticker in tickers:
        ticker_tasks[ticker] = progress.add_task(f"{ticker:8}", total=1)
    
    # Display a note about data cleaning
    console.print("[bold cyan]Note: All data will be automatically cleaned before saving:[/bold cyan]")
    console.print("  • Removing unnecessary columns (Dividends, Stock Splits)")
    console.print("  • Ensuring timestamp is properly formatted")
    console.print("  • Sorting rows by timestamp")
    console.print("  • Removing null values")
    console.print("  • Standardizing column names")
    
    return progress, total_task, ticker_tasks


def display_download_summary(results: Dict[str, str], elapsed_time: float) -> None:
    """
    Display a summary table of downloaded ticker data.
    
    Args:
        results (Dict[str, str]): Dictionary mapping ticker symbols to file paths or error status
        elapsed_time (float): Total elapsed time for the download
    """
    table = Table(title="Ticker Data Download Summary")
    
    table.add_column("Ticker", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("File Path", style="blue")
    table.add_column("Date Used", style="yellow")
    table.add_column("Data Cleaned", style="magenta")
    
    success_count = 0
    for ticker, file_path in results.items():
        if file_path == "ERROR":
            # Handle error case
            table.add_row(ticker, "❌ Failed", "N/A", "N/A", "N/A")
        else:
            # Handle success case
            try:
                # Extract the date from the file path
                path = Path(file_path)
                date_str = path.stem  # Gets the filename without extension
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}" if len(date_str) == 8 else date_str
                
                table.add_row(ticker, "✅ Success", file_path, formatted_date, "✅ Yes")
                success_count += 1
            except Exception:
                # Fallback if path parsing fails
                table.add_row(ticker, "✅ Success", file_path, "Unknown", "✅ Yes")
                success_count += 1
    
    console.print(table)
    console.print(f"[bold green]Total download time: {elapsed_time:.2f} seconds")
    
    if success_count > 0:
        console.print("\n[bold cyan]Data Cleaning Summary:[/bold cyan]")
        console.print("  ✅ Removed unnecessary columns (Dividends, Stock Splits)")
        console.print("  ✅ Ensured timestamp is properly formatted")
        console.print("  ✅ Sorted rows by timestamp")
        console.print("  ✅ Removed null values")
        console.print("  ✅ Standardized column names (timestamp, open, high, low, close, volume)")
        console.print("\n[italic]All data files are ready for analysis![/italic]")



def display_ticker_data_preview(ticker: str, data: Any, rows: int = 5) -> None:
    """
    Display a preview of the downloaded ticker data.
    
    Args:
        ticker (str): Ticker symbol
        data (Any): DataFrame containing the ticker data
        rows (int): Number of rows to display
    """
    console.print(Panel(f"[bold]Preview of {ticker} data", style="cyan"))
    
    if hasattr(data, "head"):
        console.print(data.head(rows))
    else:
        console.print("[yellow]Data preview not available")


def display_error(ticker: str, error_message: str) -> None:
    """
    Display an error message for a ticker download.
    
    Args:
        ticker (str): Ticker symbol
        error_message (str): Error message
    """
    console.print(f"[bold red]Error downloading {ticker}: {error_message}")
