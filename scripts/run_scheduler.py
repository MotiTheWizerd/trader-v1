#!/usr/bin/env python
"""
Entry point script for running the real-time stock signal scheduler.

This script provides a simple command-line interface to start the scheduler
that runs every 5 minutes during market hours.
"""
import argparse
import sys
from pathlib import Path
from rich.console import Console

# Add project root to path for absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.scheduler.scheduler import run_scheduler

# Initialize rich console
console = Console()


def main():
    """Parse command-line arguments and run the scheduler."""
    parser = argparse.ArgumentParser(
        description="Run the real-time stock signal scheduler."
    )
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Run the job once without starting the scheduler (for testing)"
    )
    
    args = parser.parse_args()
    
    if args.test_run:
        from core.scheduler.scheduler import scheduler_job as scheduled_job
        console.print("[bold blue]Running a single test job without starting the scheduler...[/bold blue]")
        scheduled_job()
        console.print("[bold green]Test job completed. Exiting.[/bold green]")
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
