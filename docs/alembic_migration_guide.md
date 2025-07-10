# Alembic Migration Guide for Trader Project

This guide explains how to use Alembic to manage database schema changes in your Trader AI project using SQLAlchemy and PostgreSQL.

---

## 🔧 Why Use Alembic?

Alembic tracks changes to your SQLAlchemy models and generates migration scripts that can update your database schema safely and consistently over time.

Benefits:

* **Version control** for DB schema
* **Safe upgrades and rollbacks**
* Easily **apply new fields, tables, constraints** without manual SQL
* Sync **collaborative changes** across environments

---

## 🧱 Project Setup Assumptions

* SQLAlchemy models are defined in `core/db/models/`
* Your declarative `Base` is in `core/db/base.py`
* Alembic is initialized and configured to use that metadata

---

## ✅ Standard Migration Process

### 1. **Update or Add a Model Field**

Edit the appropriate model in `core/db/models/...`

```python
# Example: core/db/models/signals.py
from sqlalchemy import Column, String

class TickersSignals(Base):
    ...
    signal_type = Column(String)  # New field
```

### 2. **Generate the Migration Script**

Run the Alembic `--autogenerate` command to detect changes:

```bash
poetry run alembic revision --autogenerate -m "Add signal_type to tickers_signals"
```

Alembic creates a migration file in:

```
alembic/versions/xxxxxxxxxxxx_add_signal_type_to_tickers_signals.py
```

Inside, it will contain something like:

```python
def upgrade():
    op.add_column('tickers_signals', sa.Column('signal_type', sa.String(), nullable=True))

def downgrade():
    op.drop_column('tickers_signals', 'signal_type')
```

### 3. **Apply the Migration to the DB**

Run the upgrade to apply changes:

```bash
poetry run alembic upgrade head
```

This updates the schema in PostgreSQL.

### 4. **(Optional) Verify the Change in pgAdmin**

* Open pgAdmin
* Refresh the table structure
* Verify the new field exists

---

## 🔁 Common Operations

| Action                      | Command                                               |
| --------------------------- | ----------------------------------------------------- |
| Generate migration          | `poetry run alembic revision --autogenerate -m "msg"` |
| Apply all pending upgrades  | `poetry run alembic upgrade head`                     |
| Rollback last migration     | `poetry run alembic downgrade -1`                     |
| View current revision       | `poetry run alembic current`                          |
| Stamp DB to current version | `poetry run alembic stamp head`                       |

---

## ⚠️ Notes

* Alembic needs to see your models. Always import them in `alembic/env.py`:

```python
from core.db.base import Base
import core.db.models.price_data
import core.db.models.signals

target_metadata = Base.metadata
```

* Never edit database tables manually unless you know what you're doing. Let Alembic handle structure changes.

---

## ✅ You're Set

This process keeps your DB consistent, versioned, and easy to evolve. Now every model change is safely tracked and reproducible.

Let me know if you want to auto-run migrations in production boot scripts or Docker startup.
