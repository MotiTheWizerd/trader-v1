from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from core.db.base import Base

class TickersSignals(Base):
    __tablename__ = "tickers_signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    signal = Column(String)            # BUY / SELL / STAY
    signal_type = Column(String)       # Type of signal (e.g., 'ma_dynamic', 'ma_fixed')
    confidence = Column(Float)         # 0.0 – 1.0
    reasoning = Column(String)         # Optional explanation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # When the signal was created