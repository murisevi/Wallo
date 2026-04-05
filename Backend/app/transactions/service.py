"""Transactions domain service — sync from Enable Banking + paginated queries."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.client import EnableBankingClient
from app.banking.models import BankAccount
from app.transactions.models import Transaction
from app.transactions.schemas import TransactionListResponse, TransactionResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str | None) -> date | None:
    """Parse ISO date string to date, return None on failure."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_description(remittance: object) -> str | None:
    """Normalize remittance_information (list or str) to a single string."""
    if remittance is None:
        return None
    if isinstance(remittance, list):
        parts = [str(p) for p in remittance if p]
        return " ".join(parts) or None
    return str(remittance) or None


def _signed_amount(raw: Decimal | None, indicator: str | None) -> Decimal | None:
    """Return amount as positive (CRDT) or negative (DBIT).

    Returns None when the raw amount is missing.
    """
    if raw is None:
        return None
    if indicator == "DBIT":
        return -abs(raw)
    return abs(raw)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


async def sync_transactions(
    db: AsyncSession,
    eb_client: EnableBankingClient,
    account: BankAccount,
) -> int:
    """Fetch all transactions for an account and upsert into the DB.

    Transactions that already have a matching (account_id, entry_reference)
    are skipped.  Transactions without an entry_reference are always inserted.

    Returns the number of newly inserted transactions.
    """
    raw_txns = await eb_client.get_all_transactions(account.external_uid)
    inserted = 0

    for raw in raw_txns:
        entry_ref: str | None = raw.get("entry_reference")
        amount_raw: Decimal | None = raw.get("amount")

        # Must have a monetary amount to be useful
        if amount_raw is None:
            continue

        indicator: str = raw.get("credit_debit_indicator") or "CRDT"
        signed = _signed_amount(amount_raw, indicator)
        if signed is None:
            continue

        # Resolve booking date — fall back through transaction_date → value_date → today
        booking_date = (
            _parse_date(raw.get("booking_date"))
            or _parse_date(raw.get("transaction_date"))
            or _parse_date(raw.get("value_date"))
            or date.today()
        )

        # Skip duplicates when entry_reference is present
        if entry_ref is not None:
            exists = await db.execute(
                select(Transaction.id).where(
                    Transaction.account_id == account.id,
                    Transaction.entry_reference == entry_ref,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

        txn = Transaction(
            account_id=account.id,
            user_id=account.user_id,
            entry_reference=entry_ref,
            amount=signed,
            currency=raw.get("currency") or account.currency,
            date=booking_date,
            value_date=_parse_date(raw.get("value_date")),
            description=_parse_description(raw.get("remittance_information")),
            debtor_name=raw.get("debtor_name"),
            creditor_name=raw.get("creditor_name"),
            credit_debit_indicator=indicator,
            bank_transaction_code=raw.get("bank_transaction_code"),
            status=raw.get("status") or "BOOK",
        )
        db.add(txn)
        inserted += 1

    await db.flush()
    logger.info(
        "Synced transactions for account %s: %d new, %d total fetched",
        account.external_uid,
        inserted,
        len(raw_txns),
    )
    return inserted


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


async def get_transactions(
    db: AsyncSession,
    user_id: object,  # uuid.UUID — avoid re-import at module level
    page: int = 1,
    page_size: int = 20,
    account_id: object | None = None,  # uuid.UUID | None
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> TransactionListResponse:
    """Return a paginated, filtered list of transactions for a user."""
    import uuid as _uuid

    uid = _uuid.UUID(str(user_id)) if not isinstance(user_id, _uuid.UUID) else user_id
    aid = (
        _uuid.UUID(str(account_id))
        if account_id is not None and not isinstance(account_id, _uuid.UUID)
        else account_id
    )

    # Build base filter predicate
    filters = [Transaction.user_id == uid]
    if aid is not None:
        filters.append(Transaction.account_id == aid)
    if date_from is not None:
        filters.append(Transaction.date >= date_from)
    if date_to is not None:
        filters.append(Transaction.date <= date_to)
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                Transaction.description.ilike(term),
                Transaction.debtor_name.ilike(term),
                Transaction.creditor_name.ilike(term),
            )
        )

    # Count query
    count_stmt = select(func.count()).select_from(Transaction).where(*filters)
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Data query — join BankAccount to get IBAN
    offset = (page - 1) * page_size
    stmt = (
        select(Transaction, BankAccount.iban)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .where(*filters)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()

    items: list[TransactionResponse] = []
    for txn, iban in rows:
        resp = TransactionResponse.model_validate(txn)
        resp.account_iban = iban
        items.append(resp)

    return TransactionListResponse(
        transactions=items,
        total=total,
        page=page,
        page_size=page_size,
    )
