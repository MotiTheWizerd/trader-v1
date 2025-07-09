"""
Data cleaning utilities for the trading system.
Handles cleaning and maintenance of data directories.
"""
import shutil
import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel

# Import configuration
from core.config import console, get_ticker_data_path, get_signal_file_path

class DataCleaner:
    """Handles cleaning and maintenance of data directories."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize with the base directory.
        
        Args:
            base_dir: Optional base directory path. Defaults to project root / tickers
        """
        if base_dir is not None:
            self.base_dir = Path(base_dir)
        else:
            # Default to project root / tickers
            project_root = Path(__file__).parent.parent.parent
            self.base_dir = project_root / "tickers"
        
        console.print(f"[yellow]Using base directory: {self.base_dir.absolute()}")
    
    def clean_data_directory(self) -> bool:
        """Remove all files and directories in the tickers directory while preserving the directory itself.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.base_dir.exists():
                console.print(f"[yellow]Directory {self.base_dir.absolute()} does not exist. Nothing to clean.")
                return True
                
            console.print(f"[bold]Cleaning directory: {self.base_dir.absolute()}")
            
            # Get all items in the base directory
            items = list(self.base_dir.iterdir())
            
            if not items:
                console.print("[yellow]Directory is already empty.")
                return True
                
            removed_count = 0
            
            # Remove all files and directories in the base directory
            for item in items:
                try:
                    if item.is_file():
                        item.unlink()
                        console.print(f"[green]✓ Removed file: {item.name}")
                        removed_count += 1
                    elif item.is_dir():
                        # Remove directory and all its contents
                        shutil.rmtree(item)
                        console.print(f"[green]✓ Removed directory: {item.name}")
                        removed_count += 1
                except Exception as e:
                    console.print(f"[red]Error removing {item.name}: {e}")
            
            if removed_count > 0:
                console.print(f"[bold green]✓ Successfully cleaned {removed_count} items from {self.base_dir.absolute()}")
            else:
                console.print("[yellow]No items were removed.")
                
            return True
            
        except Exception as e:
            console.print(f"[red]Error cleaning directory: {e}")
            import traceback
            console.print("[red]" + "".join(traceback.format_exc()))
            return False


def clean_data():
    """CLI function to clean the data directory."""
    cleaner = DataCleaner()
    success = cleaner.clean_data_directory()
    return 0 if success else 1
