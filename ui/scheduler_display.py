"""
UI components for the real-time scheduler display.

This module contains rich-formatted UI components for displaying scheduler status,
job results, and error messages in the terminal.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.layout import Layout
from rich.text import Text


class SchedulerDisplay:
    """Rich-formatted display for the real-time scheduler."""
    
    def __init__(self):
        """Initialize the scheduler display."""
        self.console = Console()
    
    def show_startup_message(self) -> None:
        """Display scheduler startup message."""
        self.console.print(Panel(
            "[bold green]Real-Time Stock Signal Scheduler[/bold green]\n"
            "[blue]Running jobs every 1 minute during market hours[/blue]",
            title="Startup",
            border_style="green"
        ))
        self.console.print("[yellow]Press Ctrl+C to exit[/yellow]")
    
    def show_market_closed(self, now: datetime, next_open_time=None) -> None:
        """Display market closed message with countdown until market open.
        
        Args:
            now (datetime): Current timestamp
            next_open_time (datetime, optional): Next market open time. Defaults to None.
        """
        from datetime import timedelta
        
        # Use the provided now parameter
        current_date = now.strftime("%Y-%m-%d")
        day_name = now.strftime("%A")
        
        message = f"[yellow]Market is currently closed on {day_name}, {current_date}.[/yellow]\n"
        message += "The scheduler is running but jobs will be skipped until market opens.\n\n"
        
        if next_open_time:
            # Make sure both datetimes have timezone info before subtraction
            if next_open_time.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=next_open_time.tzinfo)
            elif not next_open_time.tzinfo and now.tzinfo:
                next_open_time = next_open_time.replace(tzinfo=now.tzinfo)
                
            time_until_open = next_open_time - now
            hours = time_until_open.seconds // 3600
            minutes = (time_until_open.seconds % 3600) // 60
            
            if time_until_open.days > 0:
                message += f"[cyan]Next market open: {next_open_time.strftime('%Y-%m-%d %H:%M')} "
                message += f"({time_until_open.days} days, {hours} hours, {minutes} minutes from now)[/cyan]"
            else:
                message += f"[cyan]Next market open: {next_open_time.strftime('%H:%M')} today "
                message += f"({hours} hours, {minutes} minutes from now)[/cyan]"
        
        self.console.print(Panel(
            message,
            title="Market Closed",
            border_style="yellow"
        ))
    
    def progress_context(self) -> Progress:
        """
        Create a progress bar context manager for job execution.
        
        Returns:
            Progress: Rich progress bar context manager
        """
        return Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=self.console
        )
    
    def show_job_start(self, timestamp: datetime, num_tickers: int = 0) -> None:
        """
        Display job start message.
        
        Args:
            timestamp (datetime): Current timestamp
            num_tickers (int, optional): Number of tickers to process. Defaults to 0.
        """
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        message = f"[bold blue]Starting scheduled job at {timestamp_str}[/bold blue]"
        if num_tickers > 0:
            message += f"\n[cyan]Processing {num_tickers} tickers[/cyan]"
            
        self.console.print(Panel(
            message,
            title="Job Start",
            border_style="blue"
        ))
    
    def show_job_results(self, results: List[Dict[str, Any]], timestamp: datetime) -> None:
        """
        Display job results in a formatted table and summary.
        
        Args:
            results (List[Dict[str, Any]]): List of job results
            timestamp (datetime): Current timestamp
        """
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Create results table
        table = Table(title=f"Trading Signal Job Results - {timestamp_str}")
        table.add_column("Ticker", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Attempts", style="yellow")
        table.add_column("Rows Fetched", style="blue")
        table.add_column("Records Saved", style="green")
        table.add_column("Data File", style="blue")
        
        # Add results to table
        for result in results:
            ticker = result["ticker"]
            status = result["status"]
            attempts = result.get("attempts", 1)  # Default to 1 if not present
            row_count = result.get("row_count", 0)
            records_saved = result.get("records_saved", 0)
            data_file = result.get("data_file", "N/A")
            
            status_style = "green" if status == "success" else "red"
            
            # Format the data file name to be more concise, handling None values
            data_file_display = "N/A"
            if data_file and data_file != "N/A":
                try:
                    data_file_display = Path(data_file).name
                except (TypeError, AttributeError):
                    data_file_display = str(data_file) if data_file is not None else "N/A"
            
            table.add_row(
                ticker,
                f"[{status_style}]{status.upper()}[/{status_style}]",
                str(attempts),
                str(row_count) if status == "success" and row_count is not None else "N/A",
                str(records_saved) if status == "success" and records_saved is not None else "N/A",
                data_file_display
            )
        
        # Print results table
        self.console.print(table)
        
        # Show job summary
        success_count = sum(1 for r in results if r["status"] == "success")
        total_count = len(results)
        
        if total_count == 0:
            self.console.print("[yellow]No tickers processed.[/yellow]")
            return
        
        success_rate = (success_count / total_count) * 100
        
        # Determine color based on success rate
        if success_rate >= 90:
            color = "green"
        elif success_rate >= 50:
            color = "yellow"
        else:
            color = "red"
        
        self.console.print(Panel(
            f"[bold {color}]Job completed: {success_count}/{total_count} tickers processed successfully ({success_rate:.1f}%)[/bold {color}]",
            title="Job Summary",
            border_style=color
        ))
    
    # show_job_summary method has been integrated into show_job_results
    
    def show_error(self, message: str) -> None:
        """
        Display error message.
        
        Args:
            message (str): Error message
        """
        self.console.print(Panel(
            f"[bold red]{message}[/bold red]",
            title="Error",
            border_style="red"
        ))
    
    def show_ticker_error(self, ticker: str, error: Exception) -> None:
        """
        Display ticker-specific error message.
        
        Args:
            ticker (str): Ticker symbol
            error (Exception): Error that occurred
        """
        self.console.print(f"[bold red]Error processing {ticker}: {str(error)}[/bold red]")

    def show_next_update_countdown(self, next_run_time: datetime) -> None:
        """
        Display a countdown to the next scheduled update.
        
        Args:
            next_run_time (datetime): When the next update is scheduled to run
        """
        from datetime import datetime
        
        # Ensure we're working with timezone-aware datetimes
        now = datetime.now(pytz.UTC)
        if next_run_time.tzinfo is None:
            next_run_time = pytz.UTC.localize(next_run_time)
            
        time_until_next = next_run_time - now
        if time_until_next.total_seconds() < 0:
            return  # Don't show countdown if the next run time is in the past
            
        seconds = int(time_until_next.total_seconds())
        minutes, seconds = divmod(seconds, 60)
        
        # Only show if less than 5 minutes remaining
        if minutes < 5:
            countdown_str = f"[bold cyan]Next update in: {minutes:02d}:{seconds:02d}[/bold cyan]"
            self.console.print(countdown_str, end="\r")


# Singleton instance for global use
display = SchedulerDisplay()
