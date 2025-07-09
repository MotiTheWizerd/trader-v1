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
from core.data.downloader import download_all_tickers
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
    """Run the complete trading pipeline: download data and generate signals.
    
    Args:
        date: Date in YYYY-MM-DD format (defaults to today)
        interval: Data interval (e.g., '1m', '5m', '1h', '1d')
        period: Period to download (e.g., '1d', '5d', '1mo', '1y')
        short_window: Short moving average window
        long_window: Long moving average window
        confidence_threshold: Minimum confidence threshold for signals (0-1)
        peak_window: Window size for peak detection
        peak_threshold: Threshold for peak zone detection (0-1)
        include_reasoning: Whether to include reasoning in signals
        
    Returns:
        bool: True if pipeline completed successfully, False otherwise
    """
    # Parse date if provided, otherwise use today
    target_date = datetime.now() if not date else datetime.strptime(date, "%Y-%m-%d")
    target_date_str = target_date.strftime("%Y%m%d")
    display_date = target_date.strftime("%Y-%m-%d")
    
    try:
        # Run data download
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Downloading ticker data...", total=None)
            
            try:
                # Download data for all tickers
                console.print(f"[bold blue]Downloading data up to {display_date}...[/bold blue]")
                download_results = download_all_tickers(
                    end_date=target_date,  # Use target_date as end_date to get data up to this date
                    interval=interval,
                    period=period
                )
                
                if not download_results:
                    console.print("[red]✗ No data was downloaded![/red]")
                    return False
                    
                console.print(f"[green]✓ Downloaded data for {len(download_results)} tickers[/green]")
                
            except Exception as e:
                console.print(f"[red]✗ Error during download: {str(e)}[/red]")
                return False
                
            progress.update(task, description="Generating signals...")
            
            # Generate signals
            try:
                console.print("\n[bold blue]Generating trading signals...[/bold blue]")
                
                signals_results = generate_all_ma_signals(
                    date=target_date_str,  # Use the target date in YYYYMMDD format for file names
                    short_window=short_window,
                    long_window=long_window,
                    confidence_threshold=confidence_threshold,
                    peak_window=peak_window,
                    peak_threshold=peak_threshold,
                    include_reasoning=include_reasoning
                )
                
                if not signals_results:
                    console.print("[yellow]⚠ No signals were generated![/yellow]")
                    return False
                    
                # Count successful signal generations
                success_count = sum(1 for path in signals_results.values() if path is not None)
                console.print(f"[green]✓ Successfully generated signals for {success_count} out of {len(signals_results)} tickers[/green]")
                
                if success_count == 0:
                    console.print("[red]✗ No valid signals were generated![/red]")
                    return False
                    
                progress.update(task, completed=1, description="[green]✓ Pipeline completed![/green]")
                
            except Exception as e:
                console.print(f"[red]✗ Error during signal generation: {str(e)}[/red]")
                return False
            
        return True
        
    except Exception as e:
        console.print(f"[red]Error in pipeline: {str(e)}[/red]")
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
