"""add categories and budgets tables

Revision ID: 005
Revises: 004
Create Date: 2026-04-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── categories ──────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=False),
        sa.Column(
            "type",
            sa.Enum("expense", "income", name="category_type"),
            server_default="expense",
            nullable=False,
        ),
        sa.Column("is_custom", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_categories_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"])

    # ── budgets ─────────────────────────────────────────────────────────────
    op.create_table(
        "budgets",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("amount_limit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_budgets_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_budgets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budgets")),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "month",
            "year",
            name="uq_budgets_user_category_month_year",
        ),
    )
    op.create_index(op.f("ix_budgets_user_id"), "budgets", ["user_id"])

    # ── seed default system categories ──────────────────────────────────────
    op.execute(
        """
        INSERT INTO categories (name, icon, type, is_custom) VALUES
          ('Alimentación',     'shopping-cart', 'expense', false),
          ('Ocio y Cenas',     'utensils',      'expense', false),
          ('Transporte',       'car',            'expense', false),
          ('Hogar y Servicios','home',            'expense', false),
          ('Salud',            'heart',           'expense', false),
          ('Ropa',             'shirt',           'expense', false),
          ('Educación',        'book',            'expense', false),
          ('Suscripciones',    'repeat',          'expense', false)
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_budgets_user_id"), table_name="budgets")
    op.drop_table("budgets")
    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_table("categories")
    op.execute("DROP TYPE IF EXISTS category_type")
