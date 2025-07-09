#!/usr/bin/env python
"""
Helper script to display documentation for the download_tickers CLI tool.
Uses rich to display formatted help text in the terminal.
"""
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

def show_quick_reference():
    """Show the quick reference guide for download_tickers CLI."""
    docs_path = Path(__file__).parent.parent / "docs" / "quick_reference.md"
    
    if not docs_path.exists():
        console.print("[bold red]Error:[/] Quick reference documentation not found.")
        return
    
    with open(docs_path, "r") as f:
        content = f.read()
    
    md = Markdown(content)
    console.print(md)


def show_full_docs():
    """Show the full documentation for download_tickers CLI."""
    docs_path = Path(__file__).parent.parent / "docs" / "download_tickers_cli.md"
    
    if not docs_path.exists():
        console.print("[bold red]Error:[/] Full documentation not found.")
        return
    
    with open(docs_path, "r") as f:
        content = f.read()
    
    md = Markdown(content)
    console.print(md)


def main():
    """Main function to display help information."""
    # Check if full docs are requested
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        show_full_docs()
    else:
        # Show quick reference by default
        console.print(Panel.fit(
            "[bold green]Trader-V1[/] [yellow]Download Tickers CLI Help[/]",
            border_style="blue"
        ))
        show_quick_reference()
        console.print("\n[italic]For full documentation, run: [bold]python -m scripts.show_help --full[/][/]")


if __name__ == "__main__":
    main()
