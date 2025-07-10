"""
Core UI components using Rich library for terminal interfaces.
This module provides reusable Rich-based UI components for terminal applications.
"""
import random
import time
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.live import Live
from rich.columns import Columns

# Initialize Rich console
console = Console()

# Matrix-style characters
MATRIX_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?/"

def matrix_effect(duration=1.0):
    """Display a brief matrix-style rain effect"""
    width = console.width
    height = 5  # Number of rows for the effect
    
    with Live(auto_refresh=True, refresh_per_second=20) as live:
        start_time = time.time()
        while time.time() - start_time < duration:
            # Create columns of random characters
            columns_data = []
            for _ in range(width // 2):  # Use half width for better spacing
                column = Text()
                for _ in range(height):
                    char = random.choice(MATRIX_CHARS)
                    column.append(char, style=f"green bold")
                columns_data.append(column)
            
            # Display the matrix rain
            live.update(Columns(columns_data))
            time.sleep(0.05)

class MatrixPrompt(Prompt):
    """A Matrix-themed prompt for user input"""
    
    def make_prompt(self, default=""):
        prompt_text = Text()
        prompt_text.append("[MATRIX] > ", style="bold green")
        return prompt_text

def display_welcome_header():
    """Display the welcome header with Matrix theme"""
    console.print(Panel(
        Text("MATRIX NEURAL INTERFACE ACTIVATED", justify="center", style="bold green"),
        box=box.DOUBLE,
        border_style="green",
        title="[bold white]SYSTEM ONLINE[/]",
        subtitle="[bold green]v1.0.0[/]"
    ))

def display_connection_ready():
    """Display connection established message"""
    console.print(Panel(
        Text("Neural interface ready. The Oracle awaits your questions.", style="green"),
        border_style="green",
        box=box.SIMPLE
    ))

def display_exit_message():
    """Display exit sequence message"""
    console.print(Panel(
        Text("Disconnecting from the Matrix...", justify="center", style="bold red"),
        border_style="red",
        box=box.SIMPLE
    ))
    matrix_effect(1.0)  # Final matrix effect
    console.print("[bold red]Connection terminated.[/]")
