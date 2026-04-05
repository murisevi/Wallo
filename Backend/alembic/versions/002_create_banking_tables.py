"""create banking tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_connections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=False),
        sa.Column("bank_country", sa.String(length=2), nullable=False),
        sa.Column("bank_logo", sa.String(length=500), nullable=True),
        sa.Column("authorization_id", sa.String(length=100), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("session_valid_until", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_bank_connections_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bank_connections")),
        sa.UniqueConstraint("session_id", name=op.f("uq_bank_connections_session_id")),
    )
    op.create_index(op.f("ix_bank_connections_user_id"), "bank_connections", ["user_id"])

    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_uid", sa.String(length=100), nullable=False),
        sa.Column("iban", sa.String(length=34), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("account_type", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="EUR", nullable=False),
        sa.Column("balance_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("balance_type", sa.String(length=30), nullable=True),
        sa.Column("balance_date", sa.Date(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["bank_connections.id"], name=op.f("fk_bank_accounts_connection_id_bank_connections"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_bank_accounts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bank_accounts")),
        sa.UniqueConstraint("external_uid", name=op.f("uq_bank_accounts_external_uid")),
    )
    op.create_index(op.f("ix_bank_accounts_connection_id"), "bank_accounts", ["connection_id"])
    op.create_index(op.f("ix_bank_accounts_user_id"), "bank_accounts", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_bank_accounts_user_id"), table_name="bank_accounts")
    op.drop_index(op.f("ix_bank_accounts_connection_id"), table_name="bank_accounts")
    op.drop_table("bank_accounts")
    op.drop_index(op.f("ix_bank_connections_user_id"), table_name="bank_connections")
    op.drop_table("bank_connections")
