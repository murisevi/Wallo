"""add performance indexes

Revision ID: 008
Revises: 479f64e97a2f
Create Date: 2026-04-15

Composite indexes on the most frequent query patterns:
  - transactions filtered/sorted by user + date
  - transactions filtered by user + category
  - bank_accounts and bank_connections filtered by user
"""

from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "479f64e97a2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index: transaction list filtered + ordered by date (most used query)
    op.create_index(
        "idx_transactions_user_date",
        "transactions",
        ["user_id", "date"],
        postgresql_using="btree",
    )
    # Composite index: transaction list filtered by category (category filter UI)
    op.create_index(
        "idx_transactions_user_category",
        "transactions",
        ["user_id", "category_id"],
        postgresql_using="btree",
    )
    # Bank accounts by user (dashboard + accounts list)
    op.create_index(
        "idx_bank_accounts_user",
        "bank_accounts",
        ["user_id"],
        postgresql_using="btree",
    )
    # Bank connections by user (banking settings + dashboard join)
    op.create_index(
        "idx_bank_connections_user",
        "bank_connections",
        ["user_id"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("idx_transactions_user_date", table_name="transactions")
    op.drop_index("idx_transactions_user_category", table_name="transactions")
    op.drop_index("idx_bank_accounts_user", table_name="bank_accounts")
    op.drop_index("idx_bank_connections_user", table_name="bank_connections")
