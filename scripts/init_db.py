from core.db.session import engine
from core.db.base import Base
from core.db.models.user import User  # Ensure model is imported
from core.db.models.tickers_data import TickersData  # Ensure model is imported
from core.db.models.tickers_signals import TickersSignals  # Ensure model is imported
Base.metadata.create_all(bind=engine)
print("✅ Tables created")