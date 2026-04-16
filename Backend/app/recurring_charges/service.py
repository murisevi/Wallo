"""Recurring charges service — detection orchestration + CRUD operations."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category
from app.categories.text_cleaner import clean_bank_description, extract_merchant_key
from app.recurring_charges.detector import detect_recurring
from app.recurring_charges.models import RecurringCharge
from app.recurring_charges.schemas import RecurringChargeResponse
from app.transactions.models import Transaction

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _compute_status(
    occurrence_count: int,
    is_subscription: bool,
    user_confirmed: bool,
) -> str:
    """Derive status from occurrence data. Never downgrades a user-confirmed charge."""
    if user_confirmed:
        return "confirmed"
    if occurrence_count >= 4:
        return "confirmed"
    if occurrence_count >= 2 and is_subscription:
        return "confirmed"
    return "possible"


async def detect_and_upsert(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Run detection on all user DBIT transactions and upsert recurring_charges.

    Called at the end of each banking sync. Skips charges with status=dismissed.
    """
    # Resolve subscription category id for boost signal
    sub_stmt = select(Category.id).where(
        Category.name == "Suscripciones",
        Category.user_id.is_(None),
        Category.is_custom.is_(False),
    )
    sub_category_id: uuid.UUID | None = (
        await db.execute(sub_stmt)
    ).scalar_one_or_none()

    # Fetch all user debit transactions with a usable text field
    txn_stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.credit_debit_indicator == "DBIT",
        or_(
            Transaction.description.isnot(None),
            Transaction.creditor_name.isnot(None),
        ),
    )
    transactions = (await db.execute(txn_stmt)).scalars().all()

    # Build tuples for the pure detector
    tuples = []
    for txn in transactions:
        raw_text = txn.creditor_name or txn.description or ""
        cleaned = clean_bank_description(raw_text)
        merchant_key = extract_merchant_key(cleaned)
        if not merchant_key:
            continue
        display_name = cleaned.title() if cleaned else merchant_key.title()
        is_sub = sub_category_id is not None and txn.category_id == sub_category_id
        tuples.append(
            (
                merchant_key,
                display_name,
                abs(txn.amount),
                txn.currency,
                txn.date,
                is_sub,
            )
        )

    detected = detect_recurring(tuples)

    # Load all existing charges for this user (including dismissed)
    existing_stmt = select(RecurringCharge).where(RecurringCharge.user_id == user_id)
    existing: dict[str, RecurringCharge] = {
        rc.merchant_key: rc for rc in (await db.execute(existing_stmt)).scalars().all()
    }

    for charge in detected:
        rc = existing.get(charge.merchant_key)

        if rc is not None and rc.status == "dismissed":
            continue  # User dismissed this — never touch it again

        new_status = _compute_status(
            occurrence_count=charge.occurrence_count,
            is_subscription=charge.is_subscription,
            user_confirmed=rc.user_confirmed if rc else False,
        )

        if rc is None:
            rc = RecurringCharge(
                user_id=user_id,
                merchant_key=charge.merchant_key,
                display_name=charge.display_name,
                amount=charge.amount,
                currency=charge.currency,
                periodicity=charge.periodicity,
                status=new_status,
                occurrence_count=charge.occurrence_count,
                next_predicted_date=charge.next_predicted_date,
                last_seen_date=charge.last_seen_date,
            )
            db.add(rc)
        else:
            rc.occurrence_count = charge.occurrence_count
            rc.next_predicted_date = charge.next_predicted_date
            rc.last_seen_date = charge.last_seen_date
            rc.amount = charge.amount
            rc.display_name = charge.display_name
            rc.periodicity = charge.periodicity

            if not rc.user_confirmed:
                rc.status = new_status

            # Installment progress: sync paid count from total occurrences seen
            if rc.is_installment and rc.installment_total is not None:
                rc.installment_paid = charge.occurrence_count
                if rc.installment_paid >= rc.installment_total:
                    await db.delete(rc)
                    continue

    await db.flush()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


async def get_upcoming(
    db: AsyncSession, user_id: uuid.UUID
) -> list[RecurringChargeResponse]:
    """Return active (possible + confirmed) charges ordered by next_predicted_date."""
    stmt = (
        select(RecurringCharge)
        .where(
            RecurringCharge.user_id == user_id,
            RecurringCharge.status.in_(["possible", "confirmed"]),
        )
        .order_by(RecurringCharge.next_predicted_date.asc())
    )
    charges = (await db.execute(stmt)).scalars().all()
    return [RecurringChargeResponse.model_validate(rc) for rc in charges]


async def get_by_id(
    db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID
) -> RecurringCharge | None:
    """Fetch a single charge owned by user_id, or None."""
    stmt = select(RecurringCharge).where(
        RecurringCharge.id == charge_id,
        RecurringCharge.user_id == user_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


def _require_charge(rc: RecurringCharge | None) -> RecurringCharge:
    if rc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring charge not found",
        )
    return rc


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


async def confirm(
    db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID
) -> RecurringChargeResponse:
    """User manually confirms a possible charge."""
    rc = _require_charge(await get_by_id(db, user_id, charge_id))
    rc.status = "confirmed"
    rc.user_confirmed = True
    await db.flush()
    return RecurringChargeResponse.model_validate(rc)


async def dismiss(db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID) -> None:
    """User dismisses a charge (e.g. unsubscribed). Detection will skip it."""
    rc = _require_charge(await get_by_id(db, user_id, charge_id))
    rc.status = "dismissed"
    await db.flush()


async def set_installment(
    db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID, total: int
) -> RecurringChargeResponse:
    """Mark a charge as a fixed-term installment plan."""
    rc = _require_charge(await get_by_id(db, user_id, charge_id))
    rc.is_installment = True
    rc.installment_total = total
    # Seed installment_paid from how many we've already seen
    rc.installment_paid = rc.occurrence_count
    await db.flush()
    return RecurringChargeResponse.model_validate(rc)


async def delete(db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID) -> None:
    """User denies a charge — permanently remove the row."""
    rc = _require_charge(await get_by_id(db, user_id, charge_id))
    await db.delete(rc)
    await db.flush()
