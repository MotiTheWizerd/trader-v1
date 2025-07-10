"""
List all signals in the database.
"""
import sys
from pathlib import Path

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db.deps import get_db
from core.db.crud.tickers_signals_db import get_signals_for_ticker

def list_signals(ticker: str = None, limit: int = 10):
    """List signals from the database."""
    try:
        with get_db() as db:
            if ticker:
                print(f"Fetching signals for {ticker}...")
                signals = get_signals_for_ticker(db, ticker, limit=limit)
            else:
                print("Fetching all signals...")
                # We'll need to use a raw query to get all signals
                from sqlalchemy import text
                query = text("SELECT * FROM tickers_signals ORDER BY timestamp DESC LIMIT :limit")
                result = db.execute(query, {"limit": limit})
                signals = [dict(row) for row in result.mappings()]
            
            if not signals:
                print("No signals found in the database.")
                return
                
            print(f"\nFound {len(signals)} signals:")
            print("-" * 80)
            for i, sig in enumerate(signals, 1):
                if isinstance(sig, dict):
                    # Handle raw query result
                    print(f"{i}. {sig['ticker']} {sig['signal']} at {sig['timestamp']} (confidence: {sig.get('confidence', 0):.2f})")
                    print(f"   Type: {sig.get('signal_type', 'N/A')}, Reason: {sig.get('reasoning', 'N/A')}")
                else:
                    # Handle ORM object
                    print(f"{i}. {sig.ticker} {sig.signal} at {sig.timestamp} (confidence: {sig.confidence:.2f})")
                    print(f"   Type: {sig.signal_type}, Reason: {sig.reasoning}")
                print("-" * 80)
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='List signals from the database')
    parser.add_argument('--ticker', type=str, help='Filter by ticker symbol')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of signals to show')
    args = parser.parse_args()
    
    list_signals(args.ticker, args.limit)
