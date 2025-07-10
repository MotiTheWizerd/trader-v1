"""
Terminal layouts and screen management for Rich-based interfaces.
This module provides reusable layout components for organizing terminal UI.
"""
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

# Initialize Rich console
console = Console()

def clear_screen():
    """Clear the terminal screen"""
    console.clear()

def create_header_layout(title, subtitle=None, style="bold green"):
    """
    Create a header layout with title and optional subtitle
    
    Args:
        title: Main title text
        subtitle: Optional subtitle text
        style: Text style for the title
        
    Returns:
        Layout object with configured header
    """
    layout = Layout()
    layout.split(
        Layout(name="header"),
        Layout(name="body")
    )
    
    header_text = Text(title, justify="center", style=style)
    header_panel = Panel(
        header_text,
        subtitle=subtitle
    )
    
    layout["header"].update(header_panel)
    return layout

def create_split_screen(top_content, bottom_content, top_ratio=2, bottom_ratio=3):
    """
    Create a split screen layout with content in top and bottom sections
    
    Args:
        top_content: Content for the top section
        bottom_content: Content for the bottom section
        top_ratio: Relative size of top section
        bottom_ratio: Relative size of bottom section
        
    Returns:
        Layout object with configured split screen
    """
    layout = Layout()
    layout.split(
        Layout(name="top", ratio=top_ratio),
        Layout(name="bottom", ratio=bottom_ratio)
    )
    
    layout["top"].update(top_content)
    layout["bottom"].update(bottom_content)
    
    return layout
