from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import pytz
import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from core.db.models.tickers_data import TickersData
from core.db.deps import get_db

def insert_price(db, data: dict):
    """Insert a single price record into the database."""
    obj = TickersData(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def save_ticker_data(db, ticker: str, df: pd.DataFrame, batch_size: int = 100, base_time: datetime = None) -> int:
    """
    Save ticker data to the database in batches to avoid SQL parameter limits.
    
    Args:
        db: Database session
        ticker: Ticker symbol
        df: DataFrame with OHLCV data and timestamp index (can be datetime or integer bar index)
        batch_size: Number of records to process in each batch
        base_time: If timestamps are integer bar indices, this is the base time to which they'll be added
                 (e.g., market open time for the day)
        
    Returns:
        int: Number of records saved
    """
    if df.empty:
        return 0
    
    # Convert index to datetime if it's not already
    if not df.empty and not isinstance(df.index, pd.DatetimeIndex):
        if base_time is None:
            # If no base_time provided, use current time as reference
            base_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            print(f"Warning: Using default base_time of {base_time} for integer timestamps")
        
        # Convert integer indices to timestamps
        if pd.api.types.is_integer_dtype(df.index):
            # Assuming indices are minutes from base_time
            df.index = pd.to_datetime([base_time + pd.Timedelta(minutes=int(x)) for x in df.index])
        else:
            # Try to infer datetime from index values
            df.index = pd.to_datetime(df.index)
    
    total_saved = 0
    
    try:
        # Process in batches to avoid SQL parameter limits
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i + batch_size]
            
            # Convert DataFrame to list of dictionaries
            records = []
            for timestamp, row in batch_df.iterrows():
                try:
                    # Ensure timestamp is a timezone-aware datetime
                    if hasattr(timestamp, 'to_pydatetime'):
                        ts = timestamp.to_pydatetime()
                    else:
                        ts = pd.to_datetime(timestamp).to_pydatetime()
                    
                    # Ensure timezone awareness (convert to UTC if needed)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=pytz.UTC)
                    else:
                        ts = ts.astimezone(pytz.UTC)
                    
                    records.append({
                        'ticker': ticker.upper(),
                        'timestamp': ts,
                        'open': float(row.get('open', 0.0)),
                        'high': float(row.get('high', 0.0)),
                        'low': float(row.get('low', 0.0)),
                        'close': float(row.get('close', 0.0)),
                        'volume': int(float(row.get('volume', 0))),
                        'dividends': float(row.get('dividends', 0.0)),
                        'stock_splits': float(row.get('stock_splits', 0.0)),
                    })
                except Exception as e:
                    print(f"Error processing row {timestamp}: {str(e)}")
                    continue
            
            if not records:
                continue
                
            try:
                # Execute the insert/update operation
                stmt = insert(TickersData.__table__).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker', 'timestamp'],
                    set_={
                        'open': stmt.excluded.open,
                        'high': stmt.excluded.high,
                        'low': stmt.excluded.low,
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                        'dividends': stmt.excluded.dividends,
                        'stock_splits': stmt.excluded.stock_splits,
                    }
                )
                
                result = db.execute(stmt)
                batch_saved = result.rowcount
                total_saved += batch_saved
                
                # Commit after each successful batch
                db.commit()
                
                print(f"Saved {batch_saved} records for {ticker} in batch {i//batch_size + 1}")
                
            except Exception as e:
                db.rollback()
                print(f"Error saving batch {i//batch_size + 1} for {ticker}: {str(e)}")
                
                # If batch size is already small, try to continue with next batch
                if batch_size <= 10:
                    print("Batch size already at minimum, skipping batch")
                    continue
                    
                # Otherwise, try with a smaller batch size
                print(f"Retrying with smaller batch size: {batch_size//2}")
                return save_ticker_data(db, ticker, df, batch_size // 2, base_time)
        
        return total_saved
        
    except Exception as e:
        db.rollback()
        print(f"Error in save_ticker_data for {ticker}: {str(e)}")
        return 0

def get_prices_for_ticker(db, ticker: str):
    return db.query(TickersData).filter(TickersData.ticker == ticker).all()

def delete_old_prices(db, before_timestamp):
    """Delete price records older than the specified timestamp."""
    db.query(TickersData).filter(TickersData.timestamp < before_timestamp).delete()
    db.commit()

def get_latest_timestamp(db: Session, ticker: str) -> Optional[datetime]:
    """
    Get the most recent timestamp for a ticker from the database.
    
    Args:
        db: Database session
        ticker: Ticker symbol
        
    Returns:
        Optional[datetime]: Most recent timestamp for the ticker, or None if no data exists
    """
    result = db.query(TickersData.timestamp)\
        .filter(TickersData.ticker == ticker)\
        .order_by(TickersData.timestamp.desc())\
        .first()
    
    if result:
        return result[0]  # Return just the timestamp
    return None