---
trigger: always_on
---

Always start with DB Emojy

Trader DB Infrastructure Manual

This document explains the structure, usage, and best practices for working with the PostgreSQL database in the Trader project using SQLAlchemy.

📂 Directory Structure

trader-v1/
├── core/
│   ├── db/
│   │   ├── base.py               → SQLAlchemy Base
│   │   ├── session.py            → DB engine + SessionLocal
│   │   ├── deps.py               → get_db() context manager
│   │   ├── models/
│   │   │   ├── price_data.py
│   │   │   └── signals.py
│   │   └── crud/
│   │       ├── price_data.py
│   │       └── signals.py
├── scripts/
│   └── init_db.py              → Creates DB tables
├── .env                         → Contains DATABASE_URL

🔐 DB Connection

.env:

DATABASE_URL=postgresql://postgres:<password>@localhost:5432/mydb

session.py:

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

🔍 Using get_db()

deps.py:

from contextlib import contextmanager
from core.db.session import SessionLocal

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Use in code:

from core.db.deps import get_db
with get_db() as db:
    ...

🔄 Model Definitions

price_data.py:

class PriceData(Base):
    __tablename__ = "price_data"
    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    dividends = Column(Float)
    stock_splits = Column(Float)

signals.py:

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    signal = Column(String)
    confidence = Column(Float)
    reasoning = Column(String)

🏢 Table Creation

scripts/init_db.py:

from core.db.session import engine
from core.db.base import Base
from core.db.models import price_data, signals

Base.metadata.create_all(bind=engine)

Run with:

poetry run python scripts/init_db.py

✅ CRUD Examples

Insert One:

entry = Signal(ticker="AAPL", timestamp=..., signal="BUY", confidence=0.9, reasoning="MA cross")
db.add(entry)
db.commit()

Bulk Insert:

db.bulk_save_objects([Signal(...), Signal(...)])
db.commit()

Query:

db.query(Signal).filter(Signal.ticker == "AAPL").all()

Delete:

db.query(Signal).filter(Signal.ticker == "AAPL").delete()
db.commit()

📚 Summary

Define models in core/db/models/

Add logic in core/db/crud/

Use get_db() from deps.py

Register models in init_db.py

Load .env for DB connection

This setup is modular, testable, and scalable.