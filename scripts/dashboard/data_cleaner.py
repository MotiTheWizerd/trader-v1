"""
Database cleaning utilities for the trading system.
Handles clearing of ticker data and signals from the database.
"""
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from sqlalchemy import text

# Import database dependencies
from core.db.deps import get_db
from core.db.session import engine
from core.db.base import Base

# Import configuration
from core.config import console

class DataCleaner:
    """Handles cleaning of database tables."""
    
    def _log_error(self, error_msg: str, exc: Exception = None):
        """Log error to console and file."""
        from datetime import datetime
        import traceback
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Log to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"database_clean_{timestamp}.log"
        
        with open(log_file, "w") as f:
            f.write(f"{timestamp} - ERROR: {error_msg}\n")
            if exc:
                f.write(f"Exception: {str(exc)}\n")
                f.write("Traceback:\n")
                traceback.print_exc(file=f)
        
        # Print to console
        console.print(f"[red]ERROR: {error_msg}[/red]")
        if exc:
            console.print(f"[red]Details logged to: {log_file.absolute()}[/red]")
        
        return str(log_file.absolute())

    def clear_tables(self) -> bool:
        """Clear all data from tickers_data and tickers_signals tables."""
        try:
            print("\n=== Starting database cleanup ===")
            
            # First, just test the database connection
            try:
                print("\nTesting database connection...")
                with get_db() as db:
                    result = db.execute(text("SELECT 1")).scalar()
                    print(f"Database connection test result: {result}")
            except Exception as e:
                print(f"\n[ERROR] Database connection failed: {str(e)}")
                import traceback
                print("\nError details:")
                traceback.print_exc()
                return False
                
            # If we got here, the connection works
            print("\nDatabase connection successful!")
            
            # Now try to get table counts
            try:
                print("\nGetting table counts...")
                with get_db() as db:
                    count = db.execute(text("SELECT COUNT(*) FROM tickers_data")).scalar()
                    print(f"Rows in tickers_data: {count}")
                    
                    count = db.execute(text("SELECT COUNT(*) FROM tickers_signals")).scalar()
                    print(f"Rows in tickers_signals: {count}")
            except Exception as e:
                print(f"\n[ERROR] Failed to get table counts: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
            # Try to clear the tables
            try:
                print("\nClearing tables...")
                with get_db() as db:
                    print("Clearing tickers_data...")
                    db.execute(text("TRUNCATE TABLE tickers_data RESTART IDENTITY CASCADE"))
                    print("Clearing tickers_signals...")
                    db.execute(text("TRUNCATE TABLE tickers_signals RESTART IDENTITY CASCADE"))
                    db.commit()
                    print("Tables cleared successfully!")
                    
                    # Verify tables are empty
                    print("\nVerifying tables are empty...")
                    count = db.execute(text("SELECT COUNT(*) FROM tickers_data")).scalar()
                    print(f"Rows in tickers_data after clear: {count}")
                    
                    count = db.execute(text("SELECT COUNT(*) FROM tickers_signals")).scalar()
                    print(f"Rows in tickers_signals after clear: {count}")
                    
                print("\n=== Database cleanup completed successfully! ===")
                return True
                
            except Exception as e:
                print(f"\n[ERROR] Failed to clear tables: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _confirm_deletion(self) -> bool:
        """Ask for confirmation before clearing tables.
        
        Returns:
            bool: True if user confirms, False otherwise
        """
        print("\n" + "="*80)
        print("WARNING: This will delete ALL data from tickers_data and tickers_signals tables!")
        print("This action cannot be undone!")
        print("="*80 + "\n")
        
        try:
            confirm = input("Type 'YES' (in uppercase) to confirm, or anything else to cancel: ")
            if confirm != 'YES':
                print("\nOperation cancelled by user.")
                return False
            return True
        except Exception as e:
            print(f"Error reading input: {e}")
            return False


def clean_data():
    """CLI function to clear database tables.
    
    Returns:
        bool: True if successful, False if error, None if user cancelled
    """
    try:
        cleaner = DataCleaner()
        if not cleaner._confirm_deletion():
            return None  # User cancelled
            
        print("\nStarting database cleanup...")
        success = cleaner.clear_tables()
        if success:
            print("\nDatabase cleared successfully!")
        else:
            print("\nFailed to clear database. See error messages above.")
        return success
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
