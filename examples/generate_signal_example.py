"""
Example script demonstrating how to use the SignalGenerator to process a single data point.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.signals.signal_generator import SignalGenerator

def main():
    # Example data point (this would typically come from your data pipeline)
    data_point = {
        'ticker': 'AAPL',  # Replace with your ticker
        'timestamp': datetime.utcnow().isoformat(),
        'open': 175.50,
        'high': 176.20,
        'low': 175.10,
        'close': 175.80,
        'volume': 5000000
    }
    
    # Get database session
    from core.db.deps import get_db
    
    with get_db() as db:
        try:
            # Create signal generator with the database session
            generator = SignalGenerator(db_session=db)
            
            # Process the data point and generate signal
            signal_data = generator.process_single_data_point(data_point)
            
            if signal_data:
                print(f"Generated signal: {signal_data['signal']} for {signal_data['ticker']}")
                print(f"Confidence: {signal_data['confidence']:.2%}")
                print(f"Reasoning: {signal_data['reasoning']}")
                
                # Save the signal to database
                saved_signal = generator.save_signal(signal_data)
                if saved_signal and 'id' in saved_signal:
                    print(f"Successfully saved signal with ID: {saved_signal['id']}")
                    print(f"Signal details: {saved_signal}")
                    return
                
            print("Failed to generate or save signal")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
