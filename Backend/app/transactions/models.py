import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


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

    # Future ML placeholder — null in MVP
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Non-unique index — partial unique constraint on
    # (account_id, entry_reference) WHERE entry_reference IS NOT NULL
    # is added as raw DDL in the migration (PostgreSQL).
    __table_args__ = (
        Index("ix_transactions_account_entry_ref", "account_id", "entry_reference"),
    )
