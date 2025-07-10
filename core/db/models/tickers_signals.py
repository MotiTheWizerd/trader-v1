from sqlalchemy import Column, String, Float, Integer, DateTime
from core.db.base import Base

class TickersSignals(Base):
    __tablename__ = "tickers_signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    signal = Column(String)            # BUY / SELL / STAY
    confidence = Column(Float)         # 0.0 – 1.0
    reasoning = Column(String)         # Optional explanation