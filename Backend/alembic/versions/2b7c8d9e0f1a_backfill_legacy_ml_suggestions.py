"""Backfill legacy ml_suggested transactions into suggestion fields.

Revision ID: 2b7c8d9e0f1a
Revises: 9c1f2a3b4d5e
Create Date: 2026-05-05 00:00:00.000000
"""

from alembic import op

revision = "2b7c8d9e0f1a"
down_revision = "9c1f2a3b4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Move legacy medium-confidence ML assignments into suggestion columns."""
    op.execute(
        """
        UPDATE transactions
        SET
            categorization_method = 'ml_auto',
            suggested_category_id = NULL,
            suggested_confidence_score = NULL,
            suggested_categorization_method = NULL
        WHERE categorization_method = 'ml_suggested'
          AND category_id IS NOT NULL
          AND confidence_score >= 0.70
        """
    )

    op.execute(
        """
        UPDATE transactions
        SET
            suggested_category_id = category_id,
            suggested_confidence_score = confidence_score,
            suggested_categorization_method = 'ml_suggested',
            category_id = NULL,
            confidence_score = 0.0,
            categorization_method = NULL
        WHERE categorization_method = 'ml_suggested'
          AND category_id IS NOT NULL
          AND confidence_score >= 0.40
          AND confidence_score < 0.70
        """
    )

    op.execute(
        """
        UPDATE transactions
        SET
            category_id = NULL,
            confidence_score = 0.0,
            categorization_method = NULL,
            suggested_category_id = NULL,
            suggested_confidence_score = NULL,
            suggested_categorization_method = NULL
        WHERE categorization_method = 'ml_suggested'
          AND (
              category_id IS NULL
              OR confidence_score IS NULL
              OR confidence_score < 0.40
          )
        """
    )

    op.execute(
        """
        UPDATE transactions AS t
        SET
            category_id = NULL,
            confidence_score = 0.0,
            categorization_method = NULL,
            suggested_category_id = NULL,
            suggested_confidence_score = NULL,
            suggested_categorization_method = NULL
        FROM categories AS c
        WHERE t.category_id = c.id
          AND (
              (t.amount > 0 AND c.type != 'income')
              OR (t.amount < 0 AND c.type != 'expense')
          )
        """
    )

    op.execute(
        """
        UPDATE transactions AS t
        SET
            suggested_category_id = NULL,
            suggested_confidence_score = NULL,
            suggested_categorization_method = NULL
        FROM categories AS c
        WHERE t.suggested_category_id = c.id
          AND (
              (t.amount > 0 AND c.type != 'income')
              OR (t.amount < 0 AND c.type != 'expense')
          )
        """
    )


def downgrade() -> None:
    """Best-effort restore of medium-confidence suggestions to legacy shape."""
    op.execute(
        """
        UPDATE transactions
        SET
            category_id = suggested_category_id,
            confidence_score = suggested_confidence_score,
            categorization_method = 'ml_suggested',
            suggested_category_id = NULL,
            suggested_confidence_score = NULL,
            suggested_categorization_method = NULL
        WHERE category_id IS NULL
          AND suggested_categorization_method = 'ml_suggested'
          AND suggested_category_id IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE transactions
        SET categorization_method = 'ml_suggested'
        WHERE categorization_method = 'ml_auto'
          AND confidence_score >= 0.70
        """
    )
