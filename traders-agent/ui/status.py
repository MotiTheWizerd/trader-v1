"""
Status and loading animations for terminal interfaces.
This module provides reusable status indicators and loading animations.
"""
import asyncio
from rich.console import Console

# Initialize Rich console
console = Console()

async def show_initialization_sequence(status_messages):
    """
    Show a sequence of initialization status messages with animations.
    
    Args:
        status_messages: List of (message, delay) tuples to display in sequence
    """
    with console.status("[bold green]Initializing...", spinner="dots") as status:
        for message, delay in status_messages:
            status.update(f"[bold green]{message}")
            await asyncio.sleep(delay)

# Pre-defined initialization sequences
NEURAL_INTERFACE_SEQUENCE = [
    ("Initializing neural connection...", 0.5),
    ("Establishing secure channel...", 0.5),
    ("Calibrating neural pathways...", 0.5),
]
