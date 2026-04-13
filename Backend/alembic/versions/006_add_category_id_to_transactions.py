"""add category_id FK to transactions

Revision ID: 006
Revises: 005
Create Date: 2026-04-11

Adds a nullable category_id foreign key to the transactions table so users can
manually assign a category from the categories table to each transaction.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("category_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_transactions_category_id_categories"),
        "transactions",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_transactions_category_id"),
        "transactions",
        ["category_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_category_id"), table_name="transactions")
    op.drop_constraint(
        op.f("fk_transactions_category_id_categories"),
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "category_id")
