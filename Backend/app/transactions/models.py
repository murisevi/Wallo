from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.categories.models import Category


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Unique transaction ID from the bank — some banks omit this
    entry_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Monetary fields — amount is signed (positive = CRDT, negative = DBIT)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", server_default="EUR"
    )

    # Dates
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Narrative fields
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debtor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    creditor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Classification
    credit_debit_indicator: Mapped[str] = mapped_column(
        String(4), nullable=False
    )  # CRDT | DBIT
    bank_transaction_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="BOOK", server_default="BOOK"
    )  # BOOK | PDNG

    # Legacy string placeholder — column kept as-is in DB ("category")
    category_text: Mapped[str | None] = mapped_column(
        "category", String(50), nullable=True
    )

    # Category FK + ML categorization fields
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    categorization_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True  # "merchant_map" | "ml_auto" | "ml_suggested" | "manual"
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float, nullable=True  # 0.0 – 1.0
    )
    is_manually_corrected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ORM relationship (unidirectional: Transaction → Category)
    # Named category_rel to avoid conflicting with the CategoryResponse
    # schema field of the same logical name in TransactionResponse.
    category_rel: Mapped[Category | None] = relationship("Category")

    # Non-unique index — partial unique constraint on
    # (account_id, entry_reference) WHERE entry_reference IS NOT NULL
    # is added as raw DDL in the migration (PostgreSQL).
    __table_args__ = (
        Index("ix_transactions_account_entry_ref", "account_id", "entry_reference"),
    )
