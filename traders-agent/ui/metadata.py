"""
Metadata display components for terminal interfaces.
This module provides reusable components for displaying metadata in terminal applications.
"""
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Initialize Rich console
console = Console()

def create_metadata_table(event):
    """
    Create a table with event metadata including ID, author, status and timestamp
    
    Args:
        event: The event object
        
    Returns:
        Panel containing a table with event metadata
    """
    table = Table(box=box.SIMPLE)
    table.add_column("Property", style="bold")
    table.add_column("Value")
    
    table.add_row("Event ID", str(event.id))
    table.add_row("Author", str(event.author))
    table.add_row("Final", str(event.is_final_response()))
    table.add_row("Timestamp", time.strftime("%H:%M:%S"))
    
    return Panel(table, title="[bold white]Event Metadata[/]", border_style="white")
