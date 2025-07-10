"""
Output formatting and display components.
This module provides reusable components for formatting and displaying output in terminal applications.
"""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.table import Table
from rich.markdown import Markdown

# Initialize Rich console
console = Console()

def display_message(message, style="green", border_style=None, box_type=box.SIMPLE):
    """
    Display a message in a panel with styling
    
    Args:
        message: Message text to display
        style: Text style for the message
        border_style: Style for the panel border (default: same as text style)
        box_type: Box style to use for the panel
    """
    console.print(Panel(
        Text(message, style=style),
        border_style=border_style or style,
        box=box_type
    ))

def display_markdown(markdown_text):
    """
    Display markdown-formatted text
    
    Args:
        markdown_text: Text in markdown format
    """
    console.print(Markdown(markdown_text))

def display_table(title, columns, rows, caption=None):
    """
    Display data in a table format
    
    Args:
        title: Table title
        columns: List of column names
        rows: List of row data (each row is a list of values)
        caption: Optional table caption
    """
    table = Table(title=title, caption=caption)
    
    # Add columns
    for column in columns:
        table.add_column(column)
    
    # Add rows
    for row in rows:
        table.add_row(*row)
    
    console.print(table)

def display_error(message):
    """
    Display an error message
    
    Args:
        message: Error message text
    """
    console.print(Panel(
        Text(message, style="bold red"),
        border_style="red",
        box=box.SIMPLE
    ))

def display_success(message):
    """
    Display a success message
    
    Args:
        message: Success message text
    """
    console.print(Panel(
        Text(message, style="bold green"),
        border_style="green",
        box=box.SIMPLE
    ))
