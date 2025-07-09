"""
Test script for the real-time scheduler module.

This script runs a single iteration of the scheduler job for testing purposes,
without starting the actual scheduler.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console

# Add project root to path for absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import scheduler components
from scripts.scheduler import scheduler_job, is_market_open, ensure_directories
from ui.scheduler_display import display


def main():
    """Run a test of the scheduler job."""
    parser = argparse.ArgumentParser(
        description="Test the real-time stock signal scheduler."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force job execution even if market is closed"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="Test with a specific ticker only (e.g., AAPL)"
    )
    
    args = parser.parse_args()
    
    # Display test header
    console = Console()
    console.print("[bold blue]===== SCHEDULER TEST MODE =====[/bold blue]")
    
    # Ensure directories exist
    ensure_directories()
    
    # Check if market is open
    market_open, next_open_time = is_market_open()
    if not market_open and not args.force:
        console.print("[yellow]Market is currently closed.[/yellow]")
        console.print(f"[cyan]Next market open: {next_open_time.strftime('%Y-%m-%d %H:%M')}[/cyan]")
        console.print("[yellow]Use --force to run the job anyway for testing purposes.[/yellow]")
        return
    
    if not market_open and args.force:
        console.print("[yellow]Market is closed but test is being forced to run.[/yellow]")
        console.print(f"[cyan]Next market open would be: {next_open_time.strftime('%Y-%m-%d %H:%M')}[/cyan]")
    
    # If testing a specific ticker, temporarily modify the load_tickers function
    if args.ticker:
        import core.data.downloader
        original_load_tickers = core.data.downloader.load_tickers
        
        def mock_load_tickers():
            return [args.ticker]
        
        core.data.downloader.load_tickers = mock_load_tickers
        console.print(f"[blue]Testing with ticker: {args.ticker}[/blue]")
    
    try:
        # If force flag is used, temporarily patch the is_market_open function
        if args.force:
            import scripts.scheduler
            original_is_market_open = scripts.scheduler.is_market_open
            
            def mock_is_market_open():
                # Return both market open status and next open time
                from datetime import datetime, timedelta
                now = datetime.now()
                # Return market is open and next open time is now (since we're forcing it)
                return True, now
            
            scripts.scheduler.is_market_open = mock_is_market_open
            console.print("[blue]Forcing job execution by bypassing market hours check[/blue]")
        
        # Run a single job execution
        scheduler_job(force=args.force)
        
        console.print("[bold green]Test completed successfully![/bold green]")
    except Exception as e:
        display.show_error(f"Test failed: {str(e)}")
    finally:
        # Restore original functions if modified
        if args.ticker:
            core.data.downloader.load_tickers = original_load_tickers
            
        # Restore market open function if modified
        if args.force and 'original_is_market_open' in locals():
            scripts.scheduler.is_market_open = original_is_market_open


if __name__ == "__main__":
    main()
