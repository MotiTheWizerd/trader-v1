"""
CRUD operations for tickers_signals table.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from core.db.models.tickers_signals import TickersSignals


def insert_signal(db: Session, signal_data: dict) -> int:
    """
    Insert a new signal into the database.
    
    Args:
        db: Database session
        signal_data: Dictionary containing signal data
        
    Returns:
        The ID of the created signal record
    """
    db_signal = TickersSignals(**signal_data)
    db.add(db_signal)
    db.flush()  # Assigns the ID without committing
    signal_id = db_signal.id
    db.commit()
    return signal_id


def get_signals_for_ticker(db: Session, ticker: str, limit: int = 100) -> List[TickersSignals]:
    """
    Get signals for a specific ticker, most recent first.
    
    Args:
        db: Database session
        ticker: Ticker symbol to filter by
        limit: Maximum number of records to return
        
    Returns:
        List of signal records
    """
    return (
        db.query(TickersSignals)
        .filter(TickersSignals.ticker == ticker.upper())
        .order_by(TickersSignals.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_latest_signal(db: Session, ticker: str) -> Optional[TickersSignals]:
    """
    Get the latest signal for a specific ticker.
    
    Args:
        db: Database session
        ticker: Ticker symbol to filter by
        
    Returns:
        The latest signal record or None if no signals exist
    """
    return (
        db.query(TickersSignals)
        .filter(TickersSignals.ticker == ticker.upper())
        .order_by(TickersSignals.timestamp.desc())
        .first()
    )


def save_signals_batch(db: Session, signals: List[Dict[str, Any]], batch_size: int = 100) -> int:
    """
    Save multiple signals to the database in batches to avoid SQL parameter limits.
    
    Args:
        db: Database session
        signals: List of signal dictionaries with keys:
            - ticker: str
            - timestamp: datetime
            - signal: str (BUY/SELL/STAY)
            - confidence: float
            - reasoning: Optional[str]
            - created_at: datetime
        batch_size: Number of records to process in each batch
            
    Returns:
        int: Number of records saved/updated
    """
    if not signals:
        return 0
        
    total_saved = 0
    
    # Process in batches to avoid SQL parameter limits
    for i in range(0, len(signals), batch_size):
        # Start a new transaction for each batch
        try:
            batch = signals[i:i + batch_size]
            
            # Prepare the data for bulk insert
            values = []
            for sig in batch:
                try:
                    values.append({
                        'ticker': sig['ticker'],
                        'timestamp': sig['timestamp'],
                        'signal': sig['signal'],
                        'confidence': float(sig.get('confidence', 0.0)),
                        'reasoning': str(sig.get('reasoning', '')),
                        'created_at': sig.get('created_at', datetime.utcnow())
                    })
                except Exception as e:
                    print(f"Error processing signal {sig.get('ticker', 'unknown')}: {str(e)}")
                    continue
            
            if not values:
                continue
                
            # Execute in a savepoint to isolate batch operations
            with db.begin_nested():
                stmt = insert(TickersSignals.__table__).values(values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker', 'timestamp', 'signal'],
                    set_={
                        'confidence': stmt.excluded.confidence,
                        'reasoning': stmt.excluded.reasoning,
                        'created_at': stmt.excluded.created_at,
                    }
                )
                
                result = db.execute(stmt)
                total_saved += result.rowcount
                
            # Commit the savepoint
            db.commit()
            
        except Exception as e:
            # Rollback the failed transaction
            db.rollback()
            print(f"Error saving signals batch {i//batch_size + 1}: {str(e)}")
            
            # If batch size is already small, try to continue with next batch
            if batch_size <= 10:
                continue
                
            # Otherwise, try with a smaller batch size
            return save_signals_batch(db, signals, batch_size // 2)
    
    return total_saved


def delete_old_signals(db: Session, before_timestamp: datetime) -> int:
    """
    Delete signals older than the specified timestamp.
    
    Args:
        db: Database session
        before_timestamp: Delete signals older than this timestamp
        
    Returns:
        Number of deleted rows
    """
    result = (
        db.query(TickersSignals)
        .filter(TickersSignals.timestamp < before_timestamp)
        .delete()
    )
    db.commit()
    return result