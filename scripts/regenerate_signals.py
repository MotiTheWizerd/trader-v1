"""
Signal Regeneration Utility

This script allows you to delete all existing signal files and regenerate them
using either fixed or dynamic confidence thresholds.
"""
import argparse
import shutil
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Add project root to path to allow imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import pipeline components
from core.data.downloader import load_tickers
from core.signals.moving_average import generate_ma_signals, generate_all_ma_signals
from core.config.constants import USE_DYNAMIC_CONFIDENCE

# Initialize console
console = Console()

def delete_all_signals() -> None:
    """Delete all signal files from the tickers directory."""
    tickers_dir = Path("tickers")
    if not tickers_dir.exists():
        console.print("[yellow]No tickers directory found.[/yellow]")
        return
    
    deleted_count = 0
    for ticker_dir in tickers_dir.iterdir():
        signals_dir = ticker_dir / "signals"
        if signals_dir.exists() and signals_dir.is_dir():
            shutil.rmtree(signals_dir)
            signals_dir.mkdir()  # Recreate empty directory
            deleted_count += 1
    
    console.print(f"[green]✓ Deleted signal files for {deleted_count} tickers[/green]")

def regenerate_signals(
    use_dynamic: bool = None,
    confidence_threshold: float = 0.005,
    short_window: int = 5,
    long_window: int = 20,
    date: str = None
) -> None:
    """
    Regenerate all signal files with the specified confidence threshold type.
    
    Args:
        use_dynamic: Whether to use dynamic confidence threshold. If None, uses current setting.
        confidence_threshold: Fixed threshold to use if use_dynamic is False.
        short_window: Short moving average window size.
        long_window: Long moving average window size.
        date: Date in YYYYMMDD format. If None, uses current date.
    """
    from core.config import constants
    
    # Update the dynamic confidence setting if specified
    if use_dynamic is not None:
        constants.USE_DYNAMIC_CONFIDENCE = use_dynamic
    
    # Format date string
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    console.print(f"\n[bold]Regenerating signals with {'dynamic' if constants.USE_DYNAMIC_CONFIDENCE else 'fixed'} confidence")
    if not constants.USE_DYNAMIC_CONFIDENCE:
        console.print(f"Using fixed confidence threshold: {confidence_threshold:.3f}")
    
    # Generate signals for all tickers
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Generating signals...", total=None)
        
        try:
            results = generate_all_ma_signals(
                date=date,
                short_window=short_window,
                long_window=long_window,
                confidence_threshold=confidence_threshold,
                progress=progress,
                task_id=task
            )
            
            success_count = len([r for r in results.values() if r is not None])
            console.print(f"\n[green]✓ Successfully generated signals for {success_count} tickers[/green]")
            
        except Exception as e:
            console.print(f"[red]✗ Error generating signals: {str(e)}[/red]")
            raise

def main():
    parser = argparse.ArgumentParser(description="Regenerate all signal files with specified confidence threshold type.")
    
    threshold_group = parser.add_mutually_exclusive_group()
    threshold_group.add_argument(
        "--fixed",
        action="store_true",
        help="Use fixed confidence threshold (default: dynamic)"
    )
    threshold_group.add_argument(
        "--dynamic",
        action="store_true",
        help="Use dynamic confidence threshold (default: True)"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.005,
        help="Confidence threshold for fixed mode (default: 0.005)"
    )
    parser.add_argument(
        "--short-window",
        type=int,
        default=5,
        help="Short moving average window (default: 5)"
    )
    parser.add_argument(
        "--long-window",
        type=int,
        default=20,
        help="Long moving average window (default: 20)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date in YYYYMMDD format (default: today)"
    )
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Don't delete existing signals before regeneration"
    )
    
    args = parser.parse_args()
    
    try:
        # Delete existing signals unless --no-delete is specified
        if not args.no_delete:
            console.print("[yellow]Deleting existing signals...[/yellow]")
            delete_all_signals()
        
        # Determine threshold type
        use_dynamic = not args.fixed if (args.fixed or args.dynamic) else None
        
        # Regenerate signals
        regenerate_signals(
            use_dynamic=use_dynamic,
            confidence_threshold=args.threshold,
            short_window=args.short_window,
            long_window=args.long_window,
            date=args.date
        )
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
