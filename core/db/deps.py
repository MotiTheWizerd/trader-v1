from contextlib import contextmanager
from core.db.session import SessionLocal

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
