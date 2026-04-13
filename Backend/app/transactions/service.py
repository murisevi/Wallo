"""Transactions domain service — sync from Enable Banking + paginated queries."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.client import EnableBankingClient
from app.banking.models import BankAccount, BankConnection
from app.categories.models import Category
from app.categories.schemas import CategoryResponse
from app.categories.service import categorize_batch
from app.transactions.models import Transaction
from app.transactions.schemas import (
    TransactionCategoryUpdate,
    TransactionListResponse,
    TransactionResponse,
)

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
    psu_ip: str | None = None,
    psu_user_agent: str | None = None,
) -> int:
    """Fetch all transactions for an account and upsert into the DB.

    Transactions that already have a matching (account_id, entry_reference)
    are skipped.  Transactions without an entry_reference are always inserted.

    Pass ``psu_ip`` and ``psu_user_agent`` when the sync is triggered by an
    active user to bypass the Enable Banking 4/day background fetch rate limit.

    Returns the number of newly inserted transactions.
    """
    raw_txns = await eb_client.get_all_transactions(
        account.external_uid,
        psu_ip=psu_ip,
        psu_user_agent=psu_user_agent,
    )
    inserted = 0
    new_txns: list[Transaction] = []

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

        # Compute description early — needed for content-fingerprint deduplication
        description = _parse_description(raw.get("remittance_information"))

        # ── Deduplication ────────────────────────────────────────────────────
        # Content-fingerprint filter shared by both branches below.
        desc_filter = (
            Transaction.description == description
            if description is not None
            else Transaction.description.is_(None)
        )
        _fingerprint = [
            Transaction.account_id == account.id,
            Transaction.date == booking_date,
            Transaction.amount == signed,
            Transaction.credit_debit_indicator == indicator,
            desc_filter,
        ]

        if entry_ref is not None:
            # Bank provides a stable unique reference → use it directly.
            exists = await db.execute(
                select(Transaction.id).where(
                    Transaction.account_id == account.id,
                    Transaction.entry_reference == entry_ref,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

            # The bank may have added an entry_reference to a transaction that
            # was previously stored without one (NULL).  Detect this case via
            # content fingerprint and backfill the reference rather than
            # inserting a third copy.
            orphan_result = await db.execute(
                select(Transaction).where(
                    *_fingerprint,
                    Transaction.entry_reference.is_(None),
                )
            )
            orphan = orphan_result.scalars().first()
            if orphan is not None:
                orphan.entry_reference = entry_ref
                logger.debug(
                    "Backfilled entry_reference %s on existing transaction %s",
                    entry_ref,
                    orphan.id,
                )
                continue
        else:
            # No entry_reference (common in sandbox + some production banks).
            # Deduplicate by content fingerprint: date + signed amount +
            # direction + description.  Two transactions with all four fields
            # identical on the same account on the same day are treated as the
            # same transaction — this is safe for real-world data and prevents
            # re-insertion on every sync call.
            exists = await db.execute(
                select(Transaction.id).where(*_fingerprint)
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
            description=description,
            debtor_name=raw.get("debtor_name"),
            creditor_name=raw.get("creditor_name"),
            credit_debit_indicator=indicator,
            bank_transaction_code=raw.get("bank_transaction_code"),
            status=raw.get("status") or "BOOK",
        )
        db.add(txn)
        new_txns.append(txn)
        inserted += 1

    # Flush first so every new transaction has a DB-assigned id before categorisation.
    await db.flush()

    # Auto-categorise all newly inserted transactions in one batch.
    if new_txns:
        await categorize_batch(db, new_txns, account.user_id)

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
    category_id: str | None = None,  # UUID string or "uncategorized"
) -> TransactionListResponse:
    """Return a paginated, filtered list of transactions for a user."""
    uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    aid = (
        uuid.UUID(str(account_id))
        if account_id is not None and not isinstance(account_id, uuid.UUID)
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
    if category_id is not None:
        if category_id == "uncategorized":
            filters.append(Transaction.category_id.is_(None))
        else:
            filters.append(Transaction.category_id == uuid.UUID(category_id))

    # Exclude transactions from disconnected bank connections
    disconnected_filter = BankConnection.status != "disconnected"

    # Count query — join through to BankConnection to apply status filter
    count_stmt = (
        select(func.count())
        .select_from(Transaction)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .where(*filters, disconnected_filter)
    )
    total: int = (await db.execute(count_stmt)).scalar_one()
    total_pages = max(1, -(-total // page_size))  # ceiling division

    # Data query — join BankAccount + BankConnection + Category (full object)
    offset = (page - 1) * page_size
    stmt = (
        select(Transaction, BankAccount.iban, Category)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(*filters, disconnected_filter)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()

    items: list[TransactionResponse] = []
    for txn, iban, category_obj in rows:
        resp = TransactionResponse.model_validate(txn)
        resp.account_iban = iban
        if category_obj is not None:
            resp.category_name = category_obj.name
            resp.category_icon = category_obj.icon
            resp.category = CategoryResponse.model_validate(category_obj)
        items.append(resp)

    return TransactionListResponse(
        transactions=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------


async def update_transaction_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    data: TransactionCategoryUpdate,
) -> TransactionResponse:
    """Assign or clear the category for a single transaction.

    Validates that the requested category exists and belongs to the user or
    is a system category (user_id IS NULL).
    """
    # Fetch the transaction owned by this user
    txn_stmt = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    )
    txn = (await db.execute(txn_stmt)).scalar_one_or_none()
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    if data.category_id is not None:
        # Validate category exists and is accessible by this user
        cat_stmt = select(Category).where(
            Category.id == data.category_id,
            or_(Category.user_id.is_(None), Category.user_id == user_id),
        )
        category = (await db.execute(cat_stmt)).scalar_one_or_none()
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        txn.category_id = data.category_id
    else:
        txn.category_id = None
        category = None

    await db.flush()

    # Build the response with IBAN from BankAccount
    iban_stmt = select(BankAccount.iban).where(BankAccount.id == txn.account_id)
    iban: str | None = (await db.execute(iban_stmt)).scalar_one_or_none()

    resp = TransactionResponse.model_validate(txn)
    resp.account_iban = iban
    if category is not None:
        resp.category_name = category.name
        resp.category_icon = category.icon
    return resp
