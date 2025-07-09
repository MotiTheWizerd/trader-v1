"""Signal operations for the trading system dashboard."""
import typer
from typing import Optional
from pathlib import Path
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def regenerate_signals(
    use_dynamic: bool = typer.Option(
        None,
        "--dynamic/--fixed",
        help="Use dynamic (default) or fixed confidence threshold"
    ),
    threshold: float = typer.Option(
        0.005,
        "--threshold",
        "-t",
        help="Confidence threshold for fixed mode (default: 0.005)",
    ),
    short_window: int = typer.Option(
        5,
        "--short-window",
        "-s",
        help="Short moving average window (default: 5)",
    ),
    long_window: int = typer.Option(
        20,
        "--long-window",
        "-l",
        help="Long moving average window (default: 20)",
    ),
    date: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Date in YYYYMMDD format (default: today)",
    ),
    no_delete: bool = typer.Option(
        False,
        "--no-delete",
        help="Don't delete existing signals before regeneration",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Run in interactive mode with prompts for all options",
    ),
):
    """Regenerate all signal files with specified confidence threshold type."""
    if interactive:
        console.print("\n[bold]Signal Regeneration Settings[/bold]")
        use_dynamic = typer.confirm(
            "Use dynamic confidence threshold?",
            default=True if use_dynamic is None else use_dynamic
        )
        if not use_dynamic:
            threshold = float(typer.prompt(
                "Enter fixed confidence threshold",
                default=str(threshold)
            ))
        short_window = int(typer.prompt(
            "Short moving average window",
            default=str(short_window)
        ))
        long_window = int(typer.prompt(
            "Long moving average window",
            default=str(long_window)
        ))
        date = typer.prompt(
            "Date (YYYYMMDD) or leave empty for today",
            default=date or ""
        )
        no_delete = typer.confirm(
            "Keep existing signal files?",
            default=no_delete
        )
    
    # Build the command
    cmd = [sys.executable, "scripts/regenerate_signals.py"]
    
    if use_dynamic is not None:
        cmd.append("--dynamic" if use_dynamic else "--fixed")
    
    cmd.extend(["--threshold", str(threshold)])
    cmd.extend(["--short-window", str(short_window)])
    cmd.extend(["--long-window", str(long_window)])
    
    if date:
        cmd.extend(["--date", date])
    if no_delete:
        cmd.append("--no-delete")
    
    # Show confirmation
    console.print(Panel.fit(
        "[bold yellow]Signal Regeneration[/bold yellow]\n"
        f"• Mode: {'Dynamic' if use_dynamic else 'Fixed'} confidence\n"
        f"• Threshold: {threshold}\n"
        f"• Windows: {short_window}/{long_window}\n"
        f"• Date: {date or 'Today'}\n"
        f"• Delete existing: {'No' if no_delete else 'Yes'}",
        border_style="yellow"
    ))
    
    if not typer.confirm("\nDo you want to continue?"):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return
    
    # Run the command with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Regenerating signals...", total=None)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(Path(__file__).parent.parent.parent),
                check=True,
                capture_output=True,
                text=True
            )
            console.print("\n[green]✓ Signal regeneration completed successfully![/green]")
            if result.stdout:
                console.print("\n" + result.stdout)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Error regenerating signals:[/red]")
            if e.stderr:
                console.print(e.stderr)
            raise typer.Exit(1)
