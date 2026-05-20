"""add MCC support and ambiguous merchant mappings

Revision ID: 3c4d5e6f7a8b
Revises: 2b7c8d9e0f1a
Create Date: 2026-05-05 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "3c4d5e6f7a8b"
down_revision = "2b7c8d9e0f1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("merchant_category_code", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "merchant_mappings",
        sa.Column(
            "is_ambiguous",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("merchant_mappings", "is_ambiguous")
    op.drop_column("transactions", "merchant_category_code")
