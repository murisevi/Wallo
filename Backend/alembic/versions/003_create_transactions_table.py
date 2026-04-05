"""create transactions table

Revision ID: 003
Revises: 002
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entry_reference", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), server_default="EUR", nullable=False
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("debtor_name", sa.String(length=200), nullable=True),
        sa.Column("creditor_name", sa.String(length=200), nullable=True),
        sa.Column("credit_debit_indicator", sa.String(length=4), nullable=False),
        sa.Column("bank_transaction_code", sa.String(length=50), nullable=True),
        sa.Column(
            "status", sa.String(length=10), server_default="BOOK", nullable=False
        ),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["bank_accounts.id"],
            name=op.f("fk_transactions_account_id_bank_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_transactions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    op.create_index(op.f("ix_transactions_account_id"), "transactions", ["account_id"])
    op.create_index(op.f("ix_transactions_user_id"), "transactions", ["user_id"])
    # Composite index for duplicate detection
    op.create_index(
        "ix_transactions_account_entry_ref",
        "transactions",
        ["account_id", "entry_reference"],
    )
    # Partial unique index: one entry_reference per account (NULL values are exempt)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_transactions_account_entry_ref
        ON transactions (account_id, entry_reference)
        WHERE entry_reference IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_transactions_account_entry_ref")
    op.drop_index("ix_transactions_account_entry_ref", table_name="transactions")
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_account_id"), table_name="transactions")
    op.drop_table("transactions")
