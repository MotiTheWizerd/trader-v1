"""baseline

Revision ID: 44a1a37820ef
Revises: 77e5b9c74f3f
Create Date: 2025-07-10 12:52:58.550421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44a1a37820ef'
down_revision: Union[str, Sequence[str], None] = '77e5b9c74f3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
