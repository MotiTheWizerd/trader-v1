"""
Console output configuration using Rich.

This module provides a configured Rich console instance for consistent
styling and formatting across the application.
"""
from rich.console import Console
from rich.theme import Theme

# Define a custom theme for consistent styling
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "green",
    "highlight": "bold blue",
    "dim": "dim",
})

# Create a console instance with the custom theme
console = Console(theme=custom_theme)
