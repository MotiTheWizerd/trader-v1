"""
Pipeline operations for the trading system dashboard.

This module provides functions to run the complete trading pipeline,
including data downloading and signal generation.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn
)

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import pipeline components
from core.data.downloader import download_all_tickers, load_tickers
from core.signals.moving_average import generate_all_ma_signals

# Initialize console
console = Console()

def run_complete_pipeline(
    date: Optional[str] = None,
    interval: str = "5m",
    period: str = "20d",
    short_window: int = 5,
    long_window: int = 20,
    confidence_threshold: float = 0.005,
    peak_window: int = 12,
    peak_threshold: float = 0.99,
    include_reasoning: bool = True
) -> bool:
    """Run the data download pipeline.
    
    Args:
        date: Date in YYYY-MM-DD format (defaults to today)
        interval: Data interval (e.g., '1m', '5m', '1h', '1d')
        period: Period to download (e.g., '1d', '5d', '1mo', '1y')
        short_window: Short moving average window (not used, kept for backward compatibility)
        long_window: Long moving average window (not used, kept for backward compatibility)
        confidence_threshold: Minimum confidence threshold for signals (not used, kept for backward compatibility)
        peak_window: Window size for peak detection (not used, kept for backward compatibility)
        peak_threshold: Threshold for peak zone detection (not used, kept for backward compatibility)
        include_reasoning: Whether to include reasoning in signals (not used, kept for backward compatibility)
        
    Returns:
        bool: True if download completed successfully, False otherwise
    """
    # Parse date if provided, otherwise use today
    target_date = datetime.now() if not date else datetime.strptime(date, "%Y-%m-%d")
    display_date = target_date.strftime("%Y-%m-%d")
    
    try:
        # Create a progress bar for the operation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("({task.completed}/{task.total} tickers)"),
            transient=True,
            refresh_per_second=10
        ) as progress:
            # Add a task for the download progress
            overall_task = progress.add_task("[cyan]Downloading ticker data...", total=100)
            
            try:
                # Download data for all tickers, passing our progress bar
                console.print(f"[bold blue]Downloading data up to {display_date}...[/bold blue]")
                
                # Create a task for the download progress
                download_task = progress.add_task(
                    "[green]Downloading tickers...",
                    total=len(load_tickers())  # We know the total number of tickers
                )
                
                # Download with progress updates
                download_results = download_all_tickers(
                    end_date=target_date,  # Use target_date as end_date
                    interval=interval,
                    period=period,
                    progress=progress,
                    task_id=download_task
                )
                
                # Remove the download task
                progress.remove_task(download_task)
                
                if not download_results:
                    console.print("[red]✗ No data was downloaded![/red]")
                    return False
                
                # Count successful downloads
                success_count = sum(1 for result in download_results.values() if sum(result) > 0)
                console.print(f"[green]✓ Successfully downloaded data for {success_count} out of {len(download_results)} tickers[/green]")
                
                if success_count == 0:
                    console.print("[yellow]⚠ No new data was downloaded![/yellow]")
                    return False
                
                # Update overall progress to 100%
                progress.update(overall_task, completed=100, description="[green]✓ Download completed![/green]")
                
                return True
                
            except Exception as e:
                console.print(f"[red]✗ Error during download: {str(e)}[/red]")
                return False
            
    except Exception as e:
        console.print(f"[red]Error in download pipeline: {str(e)}[/red]")
        return False

def get_pipeline_status() -> Dict[str, Any]:
    """Get the status of the pipeline.
    
    Returns:
        Dict containing pipeline status information
    """
    # This is a placeholder - in a real implementation, you might check:
    # - Last run time
    # - Success/failure status
    # - Number of tickers processed
    # - Any errors encountered
    
    return {
        "last_run": None,  # Would be a datetime
        "status": "never_run",  # 'success', 'failed', 'in_progress', 'never_run'
        "tickers_processed": 0,
        "errors": []
    }
