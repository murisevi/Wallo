import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

_TZ = DateTime(timezone=True)  # TIMESTAMP WITH TIME ZONE throughout


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_country: Mapped[str] = mapped_column(String(2), nullable=False)
    bank_logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    authorization_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    session_valid_until: Mapped[datetime | None] = mapped_column(_TZ, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(_TZ, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        _TZ, server_default=func.now(), onupdate=func.now()
    )


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_connections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    external_uid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), default="EUR", server_default="EUR", nullable=False
    )
    balance_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    balance_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    balance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(_TZ, nullable=True)
    created_at: Mapped[datetime] = mapped_column(_TZ, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        _TZ, server_default=func.now(), onupdate=func.now()
    )
