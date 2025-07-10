from sqlalchemy import Column, String, Float, Integer, DateTime, UniqueConstraint
from core.db.base import Base

class TickersData(Base):
    __tablename__ = "tickers_data"
    __table_args__ = (
        # Add unique constraint on ticker and timestamp
        UniqueConstraint('ticker', 'timestamp', name='uq_ticker_timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    dividends = Column(Float)
    stock_splits = Column(Float)
