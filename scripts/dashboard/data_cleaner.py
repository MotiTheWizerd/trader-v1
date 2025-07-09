"""
Data cleaning utilities for the trading system.
Handles cleaning and maintenance of data directories.
"""
import shutil
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Initialize console for rich output
console = Console()

class DataCleaner:
    """Handles cleaning and maintenance of data directories."""
    
    def __init__(self, data_dir: str = "tickers/data"):
        """Initialize with the path to the data directory.
        
        Args:
            data_dir: Path to the data directory to clean
        """
        self.data_dir = Path(data_dir)
    
    def clean_data_directory(self) -> bool:
        """Remove all files and subdirectories within the data directory.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.data_dir.exists():
                console.print(f"[yellow]Directory {self.data_dir} does not exist. Nothing to clean.")
                return True
                
            console.print(f"[bold]Cleaning data directory: {self.data_dir}")
            
            # Remove all files and subdirectories
            for item in self.data_dir.glob('*'):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            
            console.print("[green]✓ Data directory cleaned successfully!")
            return True
            
        except Exception as e:
            console.print(f"[red]Error cleaning data directory: {e}")
            return False


def clean_data():
    """CLI function to clean the data directory."""
    cleaner = DataCleaner()
    success = cleaner.clean_data_directory()
    return 0 if success else 1
