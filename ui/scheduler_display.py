"""
UI components for the real-time scheduler display.

This module contains rich-formatted UI components for displaying scheduler status,
job results, and error messages in the terminal.
"""
from datetime import datetime
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
            "[blue]Running jobs every 5 minutes during market hours[/blue]",
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
        table.add_column("Data File", style="blue")
        table.add_column("Signal File", style="green")
        
        # Add results to table
        for result in results:
            ticker = result["ticker"]
            status = result["status"]
            attempts = result.get("attempts", 1)  # Default to 1 if not present
            data_file = result["data_file"] or "N/A"
            signal_file = result["signal_file"] or "N/A"
            
            status_style = "green" if status == "success" else "red"
            table.add_row(
                ticker,
                f"[{status_style}]{status.upper()}[/{status_style}]",
                str(attempts),
                data_file.split("/")[-1] if data_file != "N/A" else "N/A",
                signal_file.split("/")[-1] if signal_file != "N/A" else "N/A"
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


# Singleton instance for global use
display = SchedulerDisplay()
