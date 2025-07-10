"""
Signal Generator Module

This module provides functionality to generate trading signals from a single data point
by retrieving historical data and applying signal generation logic.
"""
from typing import Dict, Optional, List
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session

from core.db.deps import get_db
from core.db.models.tickers_data import TickersData
from core.db.models.tickers_signals import TickersSignals
from core.db.crud.tickers_data_db import get_prices_for_ticker
from core.db.crud.tickers_signals_db import insert_signal, get_latest_signal
from core.signals.moving_average import generate_ma_signals
import logging

# Configure logger
logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    Handles the generation of trading signals from price data.
    
    This class provides methods to generate trading signals based on the most recent
    price data and historical context from the database.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the SignalGenerator.
        
        Args:
            db_session: Optional database session. If not provided, one will be created when needed.
        """
        self.db_session = db_session
        self.owns_session = db_session is None
        self.use_context_manager = db_session is None
        
    def get_historical_data(self, ticker: str, limit: int = 150) -> pd.DataFrame:
        """
        Get historical data for a ticker from the database.
        
        Args:
            ticker: Ticker symbol
            limit: Maximum number of records to return (most recent first)
            
        Returns:
            DataFrame with historical price data
        """
        try:
            # If we have a session and it's not closed, use it
            if self.db_session is not None and not self.db_session.bind.pool.checkedout():
                return self._get_historical_data_with_session(self.db_session, ticker, limit)
            
            # Otherwise, create a new session
            with get_db() as db:
                return self._get_historical_data_with_session(db, ticker, limit)
                
        except Exception as e:
            logger.error(f"Error in get_historical_data for {ticker}: {str(e)}", exc_info=True)
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ticker'])
                    
    def _get_historical_data_with_session(self, db: Session, ticker: str, limit: int) -> pd.DataFrame:
        """
        Get historical data for a ticker using the provided database session.
        
        Args:
            db: Database session
            ticker: Ticker symbol
            limit: Maximum number of records to return (most recent first)
            
        Returns:
            DataFrame with historical price data, indexed by timestamp
        """
        try:
            # Get all prices for the ticker (ordered by timestamp desc)
            prices = (
                db.query(TickersData)
                .filter(TickersData.ticker == ticker.upper())
                .order_by(TickersData.timestamp.desc())
                .all()
            )
            
            if not prices:
                logger.warning(f"No price data found for {ticker}")
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ticker'])
                
            # Apply limit in memory
            prices = prices[:limit]
            
            # Convert to DataFrame with ticker included
            data = []
            for price in prices:
                # Convert timestamp to timezone-naive
                timestamp = pd.to_datetime(price.timestamp).tz_localize(None)
                
                data.append({
                    'timestamp': timestamp,
                    'open': price.open,
                    'high': price.high,
                    'low': price.low,
                    'close': price.close,
                    'volume': price.volume,
                    'ticker': price.ticker
                })
            
            # Create DataFrame and set timestamp as index
            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values('timestamp')
                df = df.set_index('timestamp')
                
            return df
            
        except Exception as e:
            logger.error(f"Error in _get_historical_data_with_session for {ticker}: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
    def process_single_data_point(self, data_point: Dict) -> Optional[Dict]:
        """
        Process a single data point and generate a signal.
        
        Args:
            data_point: Dictionary containing price data with keys:
                       - ticker: str
                       - timestamp: datetime or ISO format string
                       - open: float
                       - high: float
                       - low: float
                       - close: float
                       - volume: int
                       
        Returns:
            Dictionary containing the generated signal or None if generation failed
        """
        try:
            ticker = data_point.get('ticker')
            if not ticker:
                logger.error("No ticker provided in data point")
                return None
                
            logger.info(f"Processing signal for {ticker} at {data_point.get('timestamp')}")
            
            # Get historical data (already has timestamp as index)
            historical_df = self.get_historical_data(ticker)
            
            # Prepare the new data point as a DataFrame
            timestamp = pd.to_datetime(data_point['timestamp']).tz_localize(None)
            new_data = {
                'open': data_point['open'],
                'high': data_point['high'],
                'low': data_point['low'],
                'close': data_point['close'],
                'volume': data_point['volume'],
                'ticker': ticker
            }
            
            # Create a new row with the timestamp as index
            new_row = pd.DataFrame([new_data], index=[timestamp])
            
            # Combine with historical data
            if not historical_df.empty:
                combined_df = pd.concat([historical_df, new_row])
            else:
                combined_df = new_row
            
            # Log the current state before processing
            logger.debug(f"Combined df columns before timestamp handling: {combined_df.columns.tolist()}")
            logger.debug(f"Index name: {combined_df.index.name}, Index type: {type(combined_df.index)}")
            
            # Ensure timestamp column exists and is correct
            if 'timestamp' not in combined_df.columns:
                if combined_df.index.name == 'timestamp':
                    combined_df = combined_df.reset_index()
                elif isinstance(combined_df.index, pd.DatetimeIndex):
                    combined_df['timestamp'] = combined_df.index
                else:
                    raise ValueError("No timestamp column or index found in combined_df")
            
            # Ensure timestamp is in the correct format and sort
            combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], utc=False)
            combined_df = combined_df.sort_values('timestamp')
            
            # Log the final data structure
            logger.debug(f"Final columns before signal generation: {combined_df.columns.tolist()}")
            logger.debug(f"Sample data: {combined_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail() if not combined_df.empty else 'Empty DataFrame'}")
            
            # Generate signals using existing MA logic with the combined data
            signals_df = generate_ma_signals(ticker=ticker, df=combined_df)
            
            if signals_df is None or signals_df.empty:
                logger.info(f"No signals generated for {ticker}")
                return None
                
            # Get the most recent signal
            latest_signal = signals_df.iloc[-1].to_dict()
            
            # Prepare signal data for database
            signal_data = {
                'ticker': ticker,
                'timestamp': pd.to_datetime(latest_signal['timestamp']),
                'signal': latest_signal['signal'],
                'signal_type': 'ma_dynamic',
                'confidence': latest_signal.get('confidence', 0.0),
                'reasoning': latest_signal.get('reasoning', '')
            }
            
            return signal_data
            
        except Exception as e:
            logger.error(f"Error processing data point: {str(e)}", exc_info=True)
            return None
    
    def save_signal(self, signal_data: Dict) -> Optional[Dict]:
        """
        Save a signal to the database.
        
        Args:
            signal_data: Dictionary containing signal data
            
        Returns:
            Dictionary with signal info if successful, None if failed
        """
        try:
            # If we have a session and it's not closed, use it
            if self.db_session is not None and not self.db_session.bind.pool.checkedout():
                return self._save_signal_with_session(self.db_session, signal_data)
            
            # Otherwise, create a new session
            with get_db() as db:
                return self._save_signal_with_session(db, signal_data)
                
        except Exception as e:
            logger.error(f"Error saving signal to database: {str(e)}", exc_info=True)
            return None
            
    def _save_signal_with_session(self, db: Session, signal_data: Dict) -> Optional[Dict]:
        """
        Internal method to save signal with an existing session.
        
        Args:
            db: Database session
            signal_data: Dictionary containing signal data
            
        Returns:
            Dictionary with signal info if successful, None if failed
        """
        try:
            # Ensure timestamp is a datetime object
            if isinstance(signal_data.get('timestamp'), str):
                signal_data['timestamp'] = pd.to_datetime(signal_data['timestamp'])
            
            # Check if signal already exists for this timestamp and ticker
            existing = (
                db.query(TickersSignals)
                .filter(
                    TickersSignals.ticker == signal_data['ticker'],
                    TickersSignals.timestamp == signal_data['timestamp']
                )
                .first()
            )
            
            if existing:
                logger.info(f"Signal already exists for {signal_data['ticker']} at {signal_data['timestamp']}")
                return {
                    'id': existing.id,
                    'ticker': existing.ticker,
                    'timestamp': existing.timestamp,
                    'signal': existing.signal,
                    'signal_type': existing.signal_type,
                    'confidence': float(existing.confidence) if existing.confidence is not None else 0.0,
                    'reasoning': existing.reasoning or ''
                }
            
            from core.db.crud.tickers_signals_db import insert_signal
                
            # Create signal data dictionary
            signal_dict = {
                'ticker': signal_data['ticker'],
                'timestamp': signal_data['timestamp'],
                'signal': signal_data.get('signal', 'STAY'),
                'signal_type': signal_data.get('signal_type', 'ma_dynamic'),
                'confidence': float(signal_data.get('confidence', 0.0)),
                'reasoning': signal_data.get('reasoning', '')
            }
            
            # Insert the signal and get the ID
            signal_id = insert_signal(db, signal_dict)
            
            if signal_id is None:
                logger.error("Failed to get signal ID after insert")
                return None
                
            logger.info(f"Saved new {signal_dict['signal']} signal for {signal_dict['ticker']} "
                       f"at {signal_dict['timestamp']} with ID {signal_id}")
            
            # Return the signal data with the new ID
            return {
                'id': signal_id,
                **signal_dict
            }
            
        except Exception as e:
            logger.error(f"Error in _save_signal_with_session: {str(e)}", exc_info=True)
            if 'db' in locals():
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {str(rollback_error)}")
            return None

def generate_signal_for_data_point(data_point: Dict) -> Optional[Dict]:
    """
    Convenience function to generate and save a signal for a single data point.
    
    Args:
        data_point: Dictionary containing price data
        
    Returns:
        Dictionary containing the saved signal data or None if generation/save failed
    """
    try:
        # Create a new SignalGenerator with its own session management
        generator = SignalGenerator()
        
        # Process the data point and get the signal data
        signal_data = generator.process_single_data_point(data_point)
        
        if not signal_data:
            logger.warning("No signal data generated")
            return None
            
        # Save the signal (this will create its own session if needed)
        saved_signal = generator.save_signal(signal_data)
        
        if not saved_signal:
            logger.warning("Failed to save signal to database")
            return None
            
        # Ensure timestamp is in ISO format if it's a datetime object
        if 'timestamp' in saved_signal and hasattr(saved_signal['timestamp'], 'isoformat'):
            saved_signal['timestamp'] = saved_signal['timestamp'].isoformat()
            
        # Ensure confidence is a float
        if 'confidence' in saved_signal and saved_signal['confidence'] is not None:
            saved_signal['confidence'] = float(saved_signal['confidence'])
            
        return saved_signal
        
    except Exception as e:
        logger.error(f"Error in generate_signal_for_data_point: {str(e)}", exc_info=True)
        return None
