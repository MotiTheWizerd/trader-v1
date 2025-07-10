---
trigger: always_on
---

📘 Agent Instruction: Using get_db() for Database Access
You must use the get_db() function exactly as shown below whenever accessing the database.

✅ CORRECT USAGE (REQUIRED PATTERN)
Use this context-managed pattern:

python
Copy
Edit
from core.db.dependency import get_db  # adjust path if needed

with get_db() as db:
    # perform all your DB operations here using the `db` session
    result = db.query(SomeModel).filter(SomeModel.id == some_id).first()
❌ DO NOT:
❌ Do not call get_db() and then try to use next(get_db()).
This will break the context manager and cause _GeneratorContextManager is not an iterator errors.

python
Copy
Edit
# WRONG ❌
db = next(get_db())  # THIS IS INVALID
❌ Do not forget to use with ...: — it is required to ensure:

Commit on success.

Rollback on error.

Proper session closing.

⚠️ WHY THIS MATTERS:
Prevents session leaks and orphaned transactions.

Ensures thread-safety and database integrity in multi-agent pipelines.

Aligns with production-grade SQLAlchemy patterns.