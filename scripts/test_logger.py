"""
Test script for the structured JSON logger.

This script demonstrates how to use the logger and verifies that log entries
are correctly written to the daily log file in the expected format.
"""
import sys
import os
from datetime import datetime
from pathlib import Path
import json

# Add project root to path for absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.logger import log_info, log_warning, log_error
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

def test_basic_logging():
    """Test basic logging functionality with different log levels."""
    console.print(Panel("[bold blue]Testing Basic Logging[/bold blue]"))
    
    # Test INFO level
    log_info("test_event", "This is a test INFO message")
    console.print("[green]✓[/green] Logged INFO message")
    
    # Test WARNING level
    log_warning("test_warning", "This is a test WARNING message")
    console.print("[green]✓[/green] Logged WARNING message")
    
    # Test ERROR level
    try:
        # Simulate an exception
        raise ValueError("Test exception")
    except Exception as e:
        log_error("test_error", "This is a test ERROR message", exception=e)
        console.print("[green]✓[/green] Logged ERROR message with exception")

def test_ticker_logging():
    """Test logging with ticker information."""
    console.print(Panel("[bold blue]Testing Ticker Logging[/bold blue]"))
    
    # Test ticker-specific logging
    ticker = "AAPL"
    log_info("download_start", f"Downloading data for {ticker}", ticker=ticker)
    console.print(f"[green]✓[/green] Logged ticker event for {ticker}")
    
    # Test with additional data
    additional_data = {
        "interval": "5m",
        "period": "20d",
        "rows": 1440
    }
    log_info(
        "download_complete", 
        f"Successfully downloaded data for {ticker}", 
        ticker=ticker,
        additional=additional_data
    )
    console.print(f"[green]✓[/green] Logged ticker event with additional data")

def display_log_file():
    """Display the contents of the current log file."""
    from core.logger import get_log_filename
    
    log_file = get_log_filename()
    
    if log_file.exists():
        console.print(Panel(f"[bold green]Log File: {log_file}[/bold green]"))
        
        # Read and display the log file contents
        with open(log_file, "r", encoding="utf-8") as f:
            log_entries = [json.loads(line) for line in f.readlines()]
        
        console.print(f"[bold]Found {len(log_entries)} log entries:[/bold]")
        
        # Display the last 5 entries or all if less than 5
        display_entries = log_entries[-5:] if len(log_entries) > 5 else log_entries
        
        for i, entry in enumerate(display_entries):
            json_str = json.dumps(entry, indent=2)
            console.print(f"\n[bold]Entry {len(log_entries) - len(display_entries) + i + 1}:[/bold]")
            console.print(Syntax(json_str, "json", theme="monokai", line_numbers=True))
    else:
        console.print(f"[bold red]Log file not found: {log_file}[/bold red]")

def main():
    """Run all logger tests."""
    console.print("[bold]===== STRUCTURED JSON LOGGER TEST =====\n[/bold]")
    
    # Run tests
    test_basic_logging()
    console.print()
    
    test_ticker_logging()
    console.print()
    
    # Display log file contents
    display_log_file()
    
    console.print("\n[bold green]All tests completed![/bold green]")

if __name__ == "__main__":
    main()
