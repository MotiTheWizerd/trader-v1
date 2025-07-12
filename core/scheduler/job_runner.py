"""
Job runner for the scheduler.

This module handles the execution and scheduling of jobs.
"""
import signal
import sys
import time
import uuid
import threading
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports
from apscheduler.schedulers.blocking import BlockingScheduler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Local application imports
from core.db.deps import get_db
from core.scheduler.market_hours import is_market_open, get_next_market_open
from core.scheduler.utils import log_job_start, log_job_end
from core.scheduler.data_manager import process_ticker

# Global progress instance and lock
_global_progress = None
_progress_lock = threading.Lock()

# Global console instance
console = Console()

def get_global_progress() -> Progress:
    """Get or create a global Progress instance."""
    global _global_progress
    
    if _global_progress is None:
        with _progress_lock:
            if _global_progress is None:  # Double-checked locking pattern
                _global_progress = Progress(
                    SpinnerColumn(),
                    "•",
                    TextColumn("[progress.description]{task.description}"),
                    transient=True
                )
    return _global_progress

# Global flag for shutdown
shutdown_event = Event()


class SchedulerShutdownHandler:
    """Handle graceful shutdown of the scheduler."""
    
    def __init__(self, scheduler: BlockingScheduler):
        """Initialize with the scheduler instance."""
        self.scheduler = scheduler
        self.shutdown_requested = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        if self.shutdown_requested:
            # Second interrupt - force exit
            console.log("\n[red]Forcing immediate shutdown...")
            sys.exit(1)
            
        self.shutdown_requested = True
        console.log("\n[yellow]Shutting down gracefully (press Ctrl+C again to force)...")
        
        # Shutdown the scheduler
        self.scheduler.shutdown(wait=False)
        
        # Set the global shutdown event
        shutdown_event.set()


def countdown_worker(stop_event: Event, scheduler: BlockingScheduler) -> None:
    """Background thread that shows a countdown to the next scheduled job.
    
    Args:
        stop_event: Event to signal the thread to stop
        scheduler: Scheduler instance to get next run time from
    """
    # Disable countdown display as it's causing display issues
    return
    
    # The rest of the function is kept but disabled
    if False:  # This block is disabled
        last_countdown = ""
        while not stop_event.is_set():
            try:
                jobs = scheduler.get_jobs()
                if not jobs:
                    time.sleep(1)
                    continue
                    
                # Get the next run time from the first job
                job = jobs[0]
                next_run = getattr(job, 'next_run_time', None)
                
                if next_run:
                    now = datetime.now(timezone.utc)
                    delta = next_run - now
                    seconds = max(0, int(delta.total_seconds()))
                    
                    # Only show countdown if next run is within the next hour
                    if seconds <= 3600:  # 1 hour
                        mins, secs = divmod(seconds, 60)
                        time_str = f"{mins:02d}:{secs:02d}"
                        if time_str != last_countdown:  # Only update if changed
                            # Use \r to return to the start of the line and overwrite
                            print(f"\rNext run in: {time_str}   ", end="", flush=True)
                            last_countdown = time_str
                    else:
                        # Clear the line if we were showing a countdown before
                        if last_countdown:
                            print("\r" + " " * 30, end="\r", flush=True)
                            last_countdown = ""
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                # Only log the error if it's different from the last one
                error_msg = str(e)
                if not hasattr(countdown_worker, 'last_error') or countdown_worker.last_error != error_msg:
                    console.log(f"[yellow]Countdown worker: {error_msg}")
                    countdown_worker.last_error = error_msg
                time.sleep(5)  # Sleep longer on error to avoid log spam


def run_job(
    tickers: List[str],
    interval: str = "5m",
    period: str = "20d",
    force: bool = False,
    progress: Optional[Progress] = None
) -> Dict[str, Any]:
    """Run a data download and processing job for the given tickers.
    
    Args:
        tickers: List of ticker symbols to process
        interval: Data interval (e.g., '1m', '5m', '1h')
        period: Data period to download (e.g., '1d', '5d', '1mo')
        force: If True, run even if market is closed
        progress: Optional Rich Progress instance for progress tracking
        
    Returns:
        Dict[str, Any]: Job results
    """
    console.log("[blue]\n=== Starting New Job ===")
    console.log(f"  - Tickers: {', '.join(tickers)}")
    console.log(f"  - Interval: {interval}, Period: {period}, Force: {force}")
    console.log(f"  - Thread: {threading.current_thread().name}")
    
    # Initialize results
    job_id = str(uuid.uuid4())[:8]
    results = {
        'job_id': job_id,
        'start_time': datetime.now(timezone.utc).isoformat(),
        'tickers_processed': 0,
        'total_inserted': 0,
        'total_skipped': 0,
        'errors': [],
        'success': False
    }
    
    # Log job start
    console.log("[blue]Logging job start...")
    log_job_start(
        f"data_download_{job_id}",
        metadata={
            'tickers': tickers,
            'interval': interval,
            'period': period
        }
    )
    
    # Get the global progress instance if none provided
    if progress is None:
        progress = get_global_progress()
    
    try:
        # Check market hours if not forced
        if not force:
            try:
                market_open, next_open = is_market_open()
                if not market_open:
                    error_msg = f'Market is closed. Next open: {next_open}'
                    console.log(f"[yellow]  {error_msg}")
                    results['errors'].append({
                        'ticker': 'all',
                        'error': error_msg
                    })
                    results['end_time'] = datetime.now(timezone.utc).isoformat()
                    log_job_end(
                        f"data_download_{job_id}",
                        'skipped',
                        metadata=results
                    )
                    return results
            except Exception as e:
                error_msg = f"Error checking market hours: {str(e)}"
                console.log(f"[red]  {error_msg}")
                results['errors'].append({
                    'ticker': 'all',
                    'error': error_msg
                })
        
        # Run the job with the provided progress instance
        _run_job_with_progress(progress, tickers, interval, period, force, job_id, results, console)
            
        # Mark job as successful if we processed at least one ticker
        results['success'] = results.get('tickers_processed', 0) > 0
        console.log(f"[blue]Job completed. Success: {results['success']}")
        console.log(f"  - Tickers processed: {results.get('tickers_processed', 0)}")
        console.log(f"  - Records inserted: {results.get('total_inserted', 0)}")
        console.log(f"  - Records skipped: {results.get('total_skipped', 0)}")
        console.log(f"  - Errors: {len(results.get('errors', []))}")
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        console.log(f"[red]  Error in run_job: {error_msg}")
        console.log(f"[red]{error_trace}")
        results['errors'].append({
            'ticker': 'all',
            'error': error_msg,
            'traceback': error_trace
        })
        results['success'] = False
    finally:
        # Finalize results
        results['end_time'] = datetime.now(timezone.utc).isoformat()
        status = 'completed' if results.get('success', False) else 'failed'
        console.log(f"  - Status: {status}")
        console.log("  - Logging job end...")
        log_job_end(
            f"data_download_{job_id}",
            status,
            metadata=results
        )
        console.log("[green]✓ Job finalized\n")
        
        return results

def _run_job_with_progress(
    progress: Progress,
    tickers: List[str],
    interval: str,
    period: str,
    force: bool,
    job_id: str,
    results: Dict[str, Any],
    console
) -> None:
    """Helper function to run the job with an existing progress bar."""
    # Add a task for the overall job
    job_task = progress.add_task(
        f"[cyan]Job {job_id}",
        total=len(tickers),
        visible=True
    )
    
    try:
        # Process each ticker
        for i, ticker in enumerate(tickers):
            # Check for shutdown signal
            if shutdown_event.is_set():
                console.log("[yellow]Shutdown signal received, stopping job...")
                break
                
            # Add a task for this ticker
            ticker_task = progress.add_task(
                f"[green]Processing {ticker}",
                total=100,
                visible=True
            )
            
            try:
                # Process the ticker
                result = process_ticker(
                    ticker=ticker,
                    timestamp=datetime.now(timezone.utc),
                    interval=interval,
                    period=period,
                    progress=progress,
                    task_id=ticker_task
                )
                
                # Update results
                if result.get('success', False):
                    results['tickers_processed'] = results.get('tickers_processed', 0) + 1
                    results['total_inserted'] = results.get('total_inserted', 0) + result.get('records_inserted', 0)
                    results['total_skipped'] = results.get('total_skipped', 0) + result.get('records_skipped', 0)
                    
                    # Update progress for successful processing
                    progress.update(
                        ticker_task,
                        description=f"[green]Processed {ticker}",
                        completed=100,
                        visible=False
                    )
                else:
                    error_msg = result.get('error', 'Unknown error')
                    if 'errors' not in results:
                        results['errors'] = []
                    results['errors'].append({
                        'ticker': ticker,
                        'error': error_msg
                    })
                    
                    # Update progress for failed processing
                    progress.update(
                        ticker_task,
                        description=f"[red]Error: {ticker}",
                        completed=100,
                        visible=False
                    )
                
            except Exception as e:
                error_msg = str(e)
                console.log(f"[red]  Error processing {ticker}: {error_msg}")
                if 'errors' not in results:
                    results['errors'] = []
                results['errors'].append({
                    'ticker': ticker,
                    'error': error_msg
                })
                
                # Update progress for error case
                try:
                    progress.update(
                        ticker_task,
                        description=f"[red]Error: {ticker}",
                        completed=100,
                        visible=False
                    )
                except Exception:
                    pass
            
            # Update the main job progress
            progress.update(job_task, advance=1)
            
    finally:
        # Make sure all tasks are marked as complete
        try:
            progress.update(job_task, visible=False)
        except Exception:
            pass

def create_scheduler() -> BlockingScheduler:
    """Create and return a configured scheduler instance.
    
    Returns:
        BlockingScheduler: A new BlockingScheduler instance
    """
    from rich.console import Console
    console = Console()
    
    console.log("[blue]Creating new BlockingScheduler instance...")
    scheduler = BlockingScheduler()
    console.log("[green]✓ Scheduler instance created")
    
    return scheduler
