"""
Test script to verify signal insertion into the database.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db.deps import get_db
from core.db.crud.tickers_signals_db import insert_signal, get_signals_for_ticker

def test_signal_insertion():
    """Test inserting a signal into the database."""
    test_ticker = "TEST"
    
    # Create a test signal
    test_signal = {
        'ticker': test_ticker,
        'timestamp': datetime.utcnow(),
        'signal': 'BUY',
        'signal_type': 'test',
        'confidence': 0.95,
        'reasoning': 'Test signal insertion'
    }
    
    print("Testing signal insertion...")
    try:
        # Insert the test signal
        with get_db() as db:
            inserted = insert_signal(db, test_signal)
            print(f"Inserted signal with ID: {inserted.id}")
            
            # Verify the signal was inserted
            signals = get_signals_for_ticker(db, test_ticker)
            print(f"Found {len(signals)} signals for {test_ticker}")
            
            # Print the most recent signals
            for i, sig in enumerate(signals[:5], 1):
                print(f"{i}. {sig.ticker} {sig.signal} at {sig.timestamp} (confidence: {sig.confidence:.2f})")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_signal_insertion()
