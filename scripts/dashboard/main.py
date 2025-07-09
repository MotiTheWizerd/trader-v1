"""Trading System Dashboard.

A command-line interface for managing and executing trading system tasks.
"""
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import dashboard modules
from scripts.dashboard.data_cleaner import clean_data
from scripts.dashboard.pipeline_operations import run_complete_pipeline, get_pipeline_status

# Initialize CLI app and console
app = typer.Typer(help="Trading System Dashboard")
console = Console()

# Add commands
app.command(name="clean-data", help="Clean all data from the tickers/data directory")(clean_data)

# Main menu
def show_menu():
    """Display the main dashboard menu."""
    console.print(
        Panel.fit(
            "[bold blue]Trading System Dashboard[/bold blue]",
            border_style="blue"
        )
    )
    
    # Create a table for the menu options
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Option", style="cyan", width=15)
    table.add_column("Command", style="magenta")
    table.add_column("Description", style="white")
    
    # Add menu items
    menu_items = [
        ("1. Clean Data", "clean-data", "Remove all files from tickers/data"),
        ("2. Run Complete Pipeline", "run-pipeline", "Download data and generate signals"),
        ("3. Exit", "exit", "Exit the dashboard")
    ]
    
    for item in menu_items:
        table.add_row(item[0], f"[bold]{item[1]}[/bold]", item[2])
    
    console.print(table)

# Main command
@app.command()
def dashboard():
    """Start the interactive dashboard."""
    while True:
        show_menu()
        choice = input("\nEnter your choice (or 'exit' to quit): ").strip().lower()
        
        if choice in ['1', 'clean-data']:
            clean_data()
        elif choice in ['2', 'run-pipeline']:
            console.print("\n[bold blue]Running complete pipeline...[/bold blue]")
            success = run_complete_pipeline()
            if success:
                console.print("\n[green]✓ Pipeline completed successfully![/green]")
            else:
                console.print("\n[red]✗ Pipeline failed. Check logs for details.[/red]")
        elif choice in ['3', 'exit']:
            console.print("\n[bold blue]Exiting dashboard. Goodbye![/bold blue]")
            break
        else:
            console.print("\n[red]Invalid choice. Please try again.[/red]")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    app()
