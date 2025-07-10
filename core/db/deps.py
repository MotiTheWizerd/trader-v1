from contextlib import contextmanager
from sqlalchemy.orm import Session
from core.db.session import SessionLocal
from typing import Generator

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context-managed database session provider.

    This function is used across the signal generation and data processing modules
    to provide a consistent, safe way to access the database using SQLAlchemy sessions.

    Why it is written this way:
    ---------------------------
    - `@contextmanager` allows using `with get_db() as db:` syntax which is more Pythonic,
      readable, and less error-prone.
    - It handles `commit()` on success and `rollback()` on exceptions automatically.
    - This prevents the detached session errors and guarantees that sessions are always
      properly closed even in case of failure.
    - The older pattern using `db_gen = get_db(); db = next(db_gen)` was invalid for
      context managers, resulting in `_GeneratorContextManager is not an iterator` errors.
    - Using this version aligns with production-grade patterns and avoids session leak bugs.

    Returns:
        Generator[Session, None, None]: SQLAlchemy session object
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
