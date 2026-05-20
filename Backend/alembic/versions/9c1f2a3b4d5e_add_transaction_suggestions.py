"""add transaction category suggestions

Revision ID: 9c1f2a3b4d5e
Revises: 7a216d32206a
Create Date: 2026-05-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c1f2a3b4d5e"
down_revision: str | None = "7a216d32206a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("suggested_category_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("suggested_confidence_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "suggested_categorization_method",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        op.f("fk_transactions_suggested_category_id_categories"),
        "transactions",
        "categories",
        ["suggested_category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_transactions_suggested_category_id"),
        "transactions",
        ["suggested_category_id"],
        unique=False,
    )
    op.execute(
        """
        DELETE FROM merchant_mappings mm
        USING (
            SELECT id
            FROM (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY user_id, merchant_name
                        ORDER BY confidence DESC, updated_at DESC, id
                    ) AS rn
                FROM merchant_mappings
            ) ranked
            WHERE ranked.rn > 1
        ) duplicates
        WHERE mm.id = duplicates.id
        """
    )
    op.create_unique_constraint(
        "uq_merchant_mappings_user_merchant",
        "merchant_mappings",
        ["user_id", "merchant_name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_merchant_mappings_user_merchant",
        "merchant_mappings",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_transactions_suggested_category_id"),
        table_name="transactions",
    )
    op.drop_constraint(
        op.f("fk_transactions_suggested_category_id_categories"),
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "suggested_categorization_method")
    op.drop_column("transactions", "suggested_confidence_score")
    op.drop_column("transactions", "suggested_category_id")
