"""convert all timestamp columns to TIMESTAMP WITH TIME ZONE

Revision ID: 004
Revises: 003
Create Date: 2026-04-07

Fixes TypeError: can't subtract offset-naive and offset-aware datetimes
when storing timezone-aware datetimes returned by Enable Banking API.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columns to migrate: (table, column)
_TIMESTAMPTZ_COLUMNS = [
    ("users", "created_at"),
    ("users", "updated_at"),
    ("bank_connections", "session_valid_until"),
    ("bank_connections", "created_at"),
    ("bank_connections", "updated_at"),
    ("bank_accounts", "last_synced_at"),
    ("bank_accounts", "created_at"),
    ("bank_accounts", "updated_at"),
    ("transactions", "created_at"),
    ("transactions", "updated_at"),
]


def upgrade() -> None:
    for table, column in _TIMESTAMPTZ_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(timezone=False),
            existing_nullable=column in ("session_valid_until", "last_synced_at"),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in reversed(_TIMESTAMPTZ_COLUMNS):
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=column in ("session_valid_until", "last_synced_at"),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
