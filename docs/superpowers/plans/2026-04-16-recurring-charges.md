# Recurring Charges Detection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement automatic recurring charge detection that surfaces upcoming charges (subscriptions, installments, etc.) in the dashboard "Próximos cobros" widget with user actions to confirm, dismiss, or manage installments.

**Architecture:** New `recurring_charges` domain (model + detector + service + router). Detection runs after each sync in `transactions/service.py`. Dashboard response embeds `upcoming_charges`. Frontend widget in `dashboard/page.tsx`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Next.js 14 App Router, TanStack Query, Tailwind CSS.

---

## File Map

**Create (backend):**
- `Backend/app/recurring_charges/__init__.py`
- `Backend/app/recurring_charges/models.py` — RecurringCharge SQLAlchemy model
- `Backend/app/recurring_charges/detector.py` — pure detection algorithm (no DB)
- `Backend/app/recurring_charges/schemas.py` — Pydantic request/response schemas
- `Backend/app/recurring_charges/service.py` — DB operations + orchestration
- `Backend/app/recurring_charges/router.py` — FastAPI endpoints
- `Backend/tests/recurring_charges/__init__.py`
- `Backend/tests/recurring_charges/test_detector.py` — pure unit tests
- `Backend/tests/recurring_charges/test_service.py` — DB integration tests

**Create (alembic):**
- `Backend/alembic/versions/009_add_recurring_charges.py` — auto-generated migration

**Modify:**
- `Backend/alembic/env.py` — import RecurringCharge model
- `Backend/app/main.py` — register router
- `Backend/app/transactions/service.py` — call detect_and_upsert after categorize_batch
- `Backend/app/dashboard/schemas.py` — add upcoming_charges field
- `Backend/app/dashboard/service.py` — fetch upcoming_charges concurrently

**Create (frontend):**
- `frontend/src/hooks/useRecurringCharges.ts` — standalone hook for future use

**Modify (frontend):**
- `frontend/src/types/index.ts` — add RecurringCharge + update Dashboard
- `frontend/src/lib/api.ts` — add recurringApi
- `frontend/src/app/(dashboard)/dashboard/page.tsx` — fill "Próximos cobros" widget

---

## Task 1: RecurringCharge model + migration

**Files:**
- Create: `Backend/app/recurring_charges/__init__.py`
- Create: `Backend/app/recurring_charges/models.py`
- Modify: `Backend/alembic/env.py`
- Create (auto-generated): `Backend/alembic/versions/009_add_recurring_charges.py`

- [ ] **Step 1.1: Create package init**

Create `Backend/app/recurring_charges/__init__.py` with empty content:
```python
```

- [ ] **Step 1.2: Create the model**

Create `Backend/app/recurring_charges/models.py`:
```python
"""RecurringCharge SQLAlchemy model — detected recurring payments."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecurringCharge(Base):
    """A recurring payment pattern detected from transaction history."""

    __tablename__ = "recurring_charges"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Normalised merchant key from text_cleaner.extract_merchant_key
    merchant_key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Human-readable name shown in the UI
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", server_default="EUR"
    )
    # WEEKLY | MONTHLY | ANNUAL
    periodicity: Mapped[str] = mapped_column(String(10), nullable=False)
    # possible | confirmed | dismissed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="possible", server_default="'possible'"
    )
    user_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_predicted_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_seen_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_installment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    installment_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installment_paid: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "merchant_key",
            name="uq_recurring_charges_user_merchant",
        ),
    )
```

- [ ] **Step 1.3: Register model in Alembic env.py**

In `Backend/alembic/env.py`, add after the existing model imports (around line 19):
```python
from app.recurring_charges.models import RecurringCharge  # noqa: F401
```

- [ ] **Step 1.4: Generate migration**

From `Backend/`:
```bash
alembic revision --autogenerate -m "add_recurring_charges"
```

The generated file will create a `recurring_charges` table. Verify the generated file contains `op.create_table("recurring_charges", ...)` with the correct columns.

- [ ] **Step 1.5: Apply migration**

```bash
alembic upgrade head
```
Expected output ends with: `Running upgrade ... -> ..., add_recurring_charges`

- [ ] **Step 1.6: Commit**

```bash
git add Backend/app/recurring_charges/__init__.py \
        Backend/app/recurring_charges/models.py \
        Backend/alembic/env.py \
        Backend/alembic/versions/
git commit -m "feat(recurring): add RecurringCharge model and migration"
```

---

## Task 2: Detection algorithm + unit tests

**Files:**
- Create: `Backend/app/recurring_charges/detector.py`
- Create: `Backend/tests/recurring_charges/__init__.py`
- Create: `Backend/tests/recurring_charges/test_detector.py`

- [ ] **Step 2.1: Write failing tests first**

Create `Backend/tests/recurring_charges/__init__.py` (empty).

Create `Backend/tests/recurring_charges/test_detector.py`:
```python
"""Unit tests for the recurring charge detection algorithm.

No database required — detector is a pure function.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.recurring_charges.detector import DetectedCharge, detect_recurring


def _txns(
    merchant_key: str,
    dates: list[date],
    amount: str = "9.99",
    currency: str = "EUR",
    is_subscription: bool = False,
) -> list[tuple]:
    """Build transaction tuples for the detector."""
    display = merchant_key.title()
    return [
        (merchant_key, display, Decimal(amount), currency, d, is_subscription)
        for d in dates
    ]


BASE = date(2024, 1, 15)


class TestMonthlyDetection:
    def test_three_monthly_charges_detected(self):
        txns = _txns("NETFLIX", [BASE, BASE + timedelta(days=31), BASE + timedelta(days=62)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].periodicity == "MONTHLY"
        assert result[0].occurrence_count == 3
        assert result[0].merchant_key == "NETFLIX"

    def test_two_monthly_charges_detected(self):
        """Two occurrences are enough to trigger detection."""
        txns = _txns("SPOTIFY", [BASE, BASE + timedelta(days=30)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].occurrence_count == 2

    def test_next_predicted_date_is_last_plus_30(self):
        last = BASE + timedelta(days=60)
        txns = _txns("AMAZON", [BASE, BASE + timedelta(days=30), last])
        result = detect_recurring(txns)
        assert result[0].next_predicted_date == last + timedelta(days=30)

    def test_last_seen_date_is_most_recent(self):
        last = BASE + timedelta(days=60)
        txns = _txns("AMAZON", [BASE, BASE + timedelta(days=30), last])
        result = detect_recurring(txns)
        assert result[0].last_seen_date == last


class TestWeeklyDetection:
    def test_three_weekly_charges_detected(self):
        txns = _txns("GYM", [BASE, BASE + timedelta(days=7), BASE + timedelta(days=14)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].periodicity == "WEEKLY"

    def test_next_predicted_date_is_last_plus_7(self):
        last = BASE + timedelta(days=14)
        txns = _txns("GYM", [BASE, BASE + timedelta(days=7), last])
        result = detect_recurring(txns)
        assert result[0].next_predicted_date == last + timedelta(days=7)


class TestAnnualDetection:
    def test_annual_pattern_detected(self):
        txns = _txns("INSURANCE", [BASE, BASE + timedelta(days=365)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].periodicity == "ANNUAL"


class TestIrregularPatterns:
    def test_single_occurrence_not_detected(self):
        txns = _txns("ONEOFF", [BASE])
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_irregular_intervals_not_detected(self):
        """Very different intervals don't form a pattern."""
        dates = [BASE, BASE + timedelta(days=5), BASE + timedelta(days=45)]
        txns = _txns("RANDOM", dates)
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_mixed_intervals_not_detected(self):
        """Mix of weekly and monthly intervals → no pattern."""
        dates = [BASE, BASE + timedelta(days=7), BASE + timedelta(days=37)]
        txns = _txns("MIXED", dates)
        result = detect_recurring(txns)
        assert len(result) == 0


class TestSubscriptionFlag:
    def test_subscription_flag_propagated(self):
        txns = [
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE, True),
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE + timedelta(days=30), True),
        ]
        result = detect_recurring(txns)
        assert result[0].is_subscription is True

    def test_any_subscription_occurrence_sets_flag(self):
        """Even one occurrence with is_subscription=True sets the flag."""
        txns = [
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE, False),
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE + timedelta(days=30), True),
        ]
        result = detect_recurring(txns)
        assert result[0].is_subscription is True

    def test_no_subscription_flag_when_not_categorised(self):
        txns = _txns("AMZN", [BASE, BASE + timedelta(days=30)], is_subscription=False)
        result = detect_recurring(txns)
        assert result[0].is_subscription is False


class TestMultipleMerchants:
    def test_two_merchants_detected_independently(self):
        txns = (
            _txns("NETFLIX", [BASE, BASE + timedelta(days=30)])
            + _txns("SPOTIFY", [BASE, BASE + timedelta(days=30)])
        )
        result = detect_recurring(txns)
        assert len(result) == 2
        keys = {r.merchant_key for r in result}
        assert keys == {"NETFLIX", "SPOTIFY"}
```

- [ ] **Step 2.2: Run tests — expect failure**

From `Backend/`:
```bash
pytest tests/recurring_charges/test_detector.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.recurring_charges.detector'`

- [ ] **Step 2.3: Write the detector**

Create `Backend/app/recurring_charges/detector.py`:
```python
"""Pure recurring-charge detection algorithm — no database dependencies.

Given a list of transaction tuples (merchant_key, display_name, amount,
currency, date, is_subscription), groups them by merchant_key, checks for a
consistent WEEKLY / MONTHLY / ANNUAL periodicity across ≥ 2 occurrences, and
returns a DetectedCharge dataclass for each confirmed pattern.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

# Periodicity tolerances (days)
_WEEKLY_TARGET = 7
_MONTHLY_TARGET = 30
_ANNUAL_TARGET = 365

_WEEKLY_TOL = 2
_MONTHLY_TOL = 4
_ANNUAL_TOL = 15

_PERIODICITY_SPECS = [
    (_WEEKLY_TARGET, _WEEKLY_TOL, "WEEKLY"),
    (_MONTHLY_TARGET, _MONTHLY_TOL, "MONTHLY"),
    (_ANNUAL_TARGET, _ANNUAL_TOL, "ANNUAL"),
]

_PERIODICITY_ADVANCE: dict[str, timedelta] = {
    "WEEKLY": timedelta(days=7),
    "MONTHLY": timedelta(days=30),
    "ANNUAL": timedelta(days=365),
}


@dataclass
class DetectedCharge:
    merchant_key: str
    display_name: str
    amount: Decimal
    currency: str
    periodicity: str
    occurrence_count: int
    last_seen_date: date
    next_predicted_date: date
    is_subscription: bool


def _classify_periodicity(intervals: list[int]) -> str | None:
    """Return the periodicity label if all intervals are consistent, else None."""
    if not intervals:
        return None
    avg = sum(intervals) / len(intervals)
    for target, tol, label in _PERIODICITY_SPECS:
        if abs(avg - target) <= tol:
            # Every individual interval must also be within 2× tolerance
            if all(abs(iv - target) <= tol * 2 for iv in intervals):
                return label
    return None


def detect_recurring(
    transactions: list[tuple[str, str, Decimal, str, date, bool]],
) -> list[DetectedCharge]:
    """Detect recurring charge patterns from transaction tuples.

    Args:
        transactions: List of (merchant_key, display_name, amount, currency,
                      date, is_subscription) tuples. Already-cleaned data.

    Returns:
        One DetectedCharge per merchant with ≥ 2 occurrences and a
        consistent periodicity (WEEKLY / MONTHLY / ANNUAL).
    """
    groups: dict[str, list[tuple]] = defaultdict(list)
    for row in transactions:
        groups[row[0]].append(row)

    results: list[DetectedCharge] = []
    for merchant_key, rows in groups.items():
        if len(rows) < 2:
            continue

        rows_sorted = sorted(rows, key=lambda r: r[4])
        dates = [r[4] for r in rows_sorted]
        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]

        periodicity = _classify_periodicity(intervals)
        if periodicity is None:
            continue

        last = rows_sorted[-1]
        display_name: str = last[1]
        amount: Decimal = abs(last[2])
        currency: str = last[3]
        last_seen: date = last[4]
        is_subscription = any(r[5] for r in rows_sorted)

        results.append(
            DetectedCharge(
                merchant_key=merchant_key,
                display_name=display_name,
                amount=amount,
                currency=currency,
                periodicity=periodicity,
                occurrence_count=len(rows_sorted),
                last_seen_date=last_seen,
                next_predicted_date=last_seen + _PERIODICITY_ADVANCE[periodicity],
                is_subscription=is_subscription,
            )
        )

    return results
```

- [ ] **Step 2.4: Run tests — expect pass**

```bash
pytest tests/recurring_charges/test_detector.py -v
```
Expected: all tests `PASSED`

- [ ] **Step 2.5: Commit**

```bash
git add Backend/app/recurring_charges/detector.py \
        Backend/tests/recurring_charges/
git commit -m "feat(recurring): add detection algorithm with unit tests"
```

---

## Task 3: Schemas + service + DB tests

**Files:**
- Create: `Backend/app/recurring_charges/schemas.py`
- Create: `Backend/app/recurring_charges/service.py`
- Create: `Backend/tests/recurring_charges/test_service.py`

- [ ] **Step 3.1: Write failing service tests**

Create `Backend/tests/recurring_charges/test_service.py`:
```python
"""Integration tests for recurring_charges.service using in-memory SQLite."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.banking.models import BankAccount, BankConnection
from app.categories.models import Category
from app.recurring_charges.models import RecurringCharge
from app.recurring_charges import service as svc
from app.transactions.models import Transaction
from tests.conftest import TestSessionLocal


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def user(db: AsyncSession) -> User:
    u = User(
        email=f"rc-test-{uuid.uuid4()}@example.com",
        name="RC Test User",
        hashed_password="hashed",
    )
    db.add(u)
    await db.flush()
    return u


@pytest.fixture
async def connection(db: AsyncSession, user: User) -> BankConnection:
    conn = BankConnection(
        user_id=user.id,
        bank_name="Test Bank",
        session_id=str(uuid.uuid4()),
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest.fixture
async def account(db: AsyncSession, user: User, connection: BankConnection) -> BankAccount:
    acc = BankAccount(
        connection_id=connection.id,
        user_id=user.id,
        external_uid=str(uuid.uuid4()),
        name="Main Account",
        currency="EUR",
    )
    db.add(acc)
    await db.flush()
    return acc


def make_txn(account: BankAccount, user: User, d: date, amount: str = "-9.99", description: str = "NETFLIX") -> Transaction:
    return Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal(amount),
        currency="EUR",
        date=d,
        credit_debit_indicator="DBIT",
        description=description,
        status="BOOK",
    )


BASE = date(2024, 1, 15)


class TestDetectAndUpsert:
    async def test_monthly_pattern_creates_possible_charge(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        """Three monthly transactions → RecurringCharge with status possible."""
        txns = [
            make_txn(account, user, BASE),
            make_txn(account, user, BASE + timedelta(days=30)),
            make_txn(account, user, BASE + timedelta(days=60)),
        ]
        for t in txns:
            db.add(t)
        await db.flush()

        await svc.detect_and_upsert(db, user.id)

        charges = await svc.get_upcoming(db, user.id)
        assert len(charges) == 1
        assert charges[0].status == "possible"
        assert charges[0].occurrence_count == 3
        assert charges[0].periodicity == "MONTHLY"

    async def test_four_occurrences_creates_confirmed_charge(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        """Four monthly transactions → status confirmed."""
        txns = [
            make_txn(account, user, BASE + timedelta(days=30 * i))
            for i in range(4)
        ]
        for t in txns:
            db.add(t)
        await db.flush()

        await svc.detect_and_upsert(db, user.id)

        charges = await svc.get_upcoming(db, user.id)
        assert len(charges) == 1
        assert charges[0].status == "confirmed"

    async def test_dismissed_charge_not_updated(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        """detect_and_upsert skips charges with status=dismissed."""
        # Create dismissed charge first
        rc = RecurringCharge(
            user_id=user.id,
            merchant_key="NETFLIX",
            display_name="Netflix",
            amount=Decimal("9.99"),
            currency="EUR",
            periodicity="MONTHLY",
            status="dismissed",
            occurrence_count=3,
            next_predicted_date=BASE + timedelta(days=90),
            last_seen_date=BASE + timedelta(days=60),
        )
        db.add(rc)
        await db.flush()
        dismissed_id = rc.id

        # Add more transactions
        txns = [
            make_txn(account, user, BASE + timedelta(days=30 * i))
            for i in range(4)
        ]
        for t in txns:
            db.add(t)
        await db.flush()

        await svc.detect_and_upsert(db, user.id)

        # Dismissed charge should still be dismissed
        charges = await svc.get_upcoming(db, user.id)
        assert len(charges) == 0  # dismissed charges not returned by get_upcoming


class TestConfirm:
    async def test_confirm_possible_charge(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        rc = RecurringCharge(
            user_id=user.id,
            merchant_key="SPOTIFY",
            display_name="Spotify",
            amount=Decimal("9.99"),
            currency="EUR",
            periodicity="MONTHLY",
            status="possible",
            occurrence_count=2,
            next_predicted_date=BASE + timedelta(days=30),
            last_seen_date=BASE,
        )
        db.add(rc)
        await db.flush()

        await svc.confirm(db, user.id, rc.id)

        updated = await svc.get_by_id(db, user.id, rc.id)
        assert updated is not None
        assert updated.status == "confirmed"
        assert updated.user_confirmed is True


class TestDismiss:
    async def test_dismiss_charge(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        rc = RecurringCharge(
            user_id=user.id,
            merchant_key="AMAZON",
            display_name="Amazon",
            amount=Decimal("9.99"),
            currency="EUR",
            periodicity="MONTHLY",
            status="confirmed",
            occurrence_count=4,
            next_predicted_date=BASE + timedelta(days=30),
            last_seen_date=BASE,
        )
        db.add(rc)
        await db.flush()

        await svc.dismiss(db, user.id, rc.id)

        charges = await svc.get_upcoming(db, user.id)
        assert len(charges) == 0  # dismissed not in upcoming


class TestInstallment:
    async def test_set_installment(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        rc = RecurringCharge(
            user_id=user.id,
            merchant_key="APPLE",
            display_name="Apple",
            amount=Decimal("50.00"),
            currency="EUR",
            periodicity="MONTHLY",
            status="confirmed",
            occurrence_count=3,
            next_predicted_date=BASE + timedelta(days=30),
            last_seen_date=BASE,
        )
        db.add(rc)
        await db.flush()

        await svc.set_installment(db, user.id, rc.id, total=12)

        updated = await svc.get_by_id(db, user.id, rc.id)
        assert updated is not None
        assert updated.is_installment is True
        assert updated.installment_total == 12
        assert updated.installment_paid == 3  # occurrence_count becomes installment_paid


class TestDelete:
    async def test_delete_charge(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        rc = RecurringCharge(
            user_id=user.id,
            merchant_key="DROPBOX",
            display_name="Dropbox",
            amount=Decimal("9.99"),
            currency="EUR",
            periodicity="MONTHLY",
            status="possible",
            occurrence_count=2,
            next_predicted_date=BASE + timedelta(days=30),
            last_seen_date=BASE,
        )
        db.add(rc)
        await db.flush()
        charge_id = rc.id

        await svc.delete(db, user.id, charge_id)

        result = await svc.get_by_id(db, user.id, charge_id)
        assert result is None
```

- [ ] **Step 3.2: Run tests — expect failure**

```bash
pytest tests/recurring_charges/test_service.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` for `app.recurring_charges.service`

- [ ] **Step 3.3: Create schemas**

Create `Backend/app/recurring_charges/schemas.py`:
```python
"""Pydantic schemas for recurring charges API."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RecurringChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    amount: Decimal
    currency: str
    periodicity: str
    status: str
    user_confirmed: bool
    occurrence_count: int
    next_predicted_date: date
    is_installment: bool
    installment_total: int | None
    installment_paid: int | None


class SetInstallmentRequest(BaseModel):
    installment_total: int
```

- [ ] **Step 3.4: Create service**

Create `Backend/app/recurring_charges/service.py`:
```python
"""Recurring charges service — detection orchestration + CRUD operations."""

from __future__ import annotations

import uuid
from decimal import Decimal

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
    sub_category_id: uuid.UUID | None = (await db.execute(sub_stmt)).scalar_one_or_none()

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
            (merchant_key, display_name, abs(txn.amount), txn.currency, txn.date, is_sub)
        )

    detected = detect_recurring(tuples)

    # Load all existing charges for this user (including dismissed)
    existing_stmt = select(RecurringCharge).where(
        RecurringCharge.user_id == user_id
    )
    existing: dict[str, RecurringCharge] = {
        rc.merchant_key: rc
        for rc in (await db.execute(existing_stmt)).scalars().all()
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
            old_last_seen = rc.last_seen_date

            rc.occurrence_count = charge.occurrence_count
            rc.next_predicted_date = charge.next_predicted_date
            rc.last_seen_date = charge.last_seen_date
            rc.amount = charge.amount

            if not rc.user_confirmed:
                rc.status = new_status

            # Installment progress: new payment detected since last sync
            if rc.is_installment and rc.installment_total is not None:
                if charge.last_seen_date > old_last_seen:
                    rc.installment_paid = (rc.installment_paid or 0) + 1
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


async def dismiss(
    db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID
) -> None:
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


async def delete(
    db: AsyncSession, user_id: uuid.UUID, charge_id: uuid.UUID
) -> None:
    """User denies a charge — permanently remove the row."""
    rc = _require_charge(await get_by_id(db, user_id, charge_id))
    await db.delete(rc)
    await db.flush()
```

- [ ] **Step 3.5: Run tests — expect pass**

```bash
pytest tests/recurring_charges/test_service.py -v
```
Expected: all tests `PASSED`

- [ ] **Step 3.6: Commit**

```bash
git add Backend/app/recurring_charges/schemas.py \
        Backend/app/recurring_charges/service.py \
        Backend/tests/recurring_charges/test_service.py
git commit -m "feat(recurring): add service layer with DB integration tests"
```

---

## Task 4: Router + register in main.py

**Files:**
- Create: `Backend/app/recurring_charges/router.py`
- Modify: `Backend/app/main.py`

- [ ] **Step 4.1: Create the router**

Create `Backend/app/recurring_charges/router.py`:
```python
"""Recurring charges API router."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.recurring_charges import service as svc
from app.recurring_charges.schemas import RecurringChargeResponse, SetInstallmentRequest
from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/recurring-charges", tags=["recurring-charges"])


@router.get("/", response_model=list[RecurringChargeResponse])
async def list_recurring_charges(
    current_user: CurrentUser,
    db: DbSession,
) -> list[RecurringChargeResponse]:
    """List active (possible + confirmed) recurring charges for the authenticated user,
    ordered by next predicted date."""
    return await svc.get_upcoming(db, current_user.id)


@router.patch("/{charge_id}/confirm", response_model=RecurringChargeResponse)
async def confirm_charge(
    charge_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> RecurringChargeResponse:
    """Manually confirm a possible recurring charge."""
    return await svc.confirm(db, current_user.id, charge_id)


@router.patch("/{charge_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_charge(
    charge_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Dismiss a recurring charge (user has unsubscribed).
    The charge will not reappear after future syncs."""
    await svc.dismiss(db, current_user.id, charge_id)


@router.patch("/{charge_id}/installment", response_model=RecurringChargeResponse)
async def set_installment(
    charge_id: uuid.UUID,
    data: SetInstallmentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> RecurringChargeResponse:
    """Mark a recurring charge as a fixed-term installment plan."""
    return await svc.set_installment(db, current_user.id, charge_id, data.installment_total)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_charge(
    charge_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Permanently delete a recurring charge (deny — not a real recurring payment)."""
    await svc.delete(db, current_user.id, charge_id)
```

- [ ] **Step 4.2: Register in main.py**

In `Backend/app/main.py`, add the import after the existing router imports (around line 93):
```python
from app.recurring_charges.router import router as recurring_charges_router  # noqa: E402
```

And add the include after line 101 (after reports_router):
```python
app.include_router(recurring_charges_router, prefix="/api/v1")
```

- [ ] **Step 4.3: Run full test suite to verify nothing broke**

```bash
pytest tests/ -v --tb=short
```
Expected: all existing tests pass, new domain tests pass.

- [ ] **Step 4.4: Commit**

```bash
git add Backend/app/recurring_charges/router.py Backend/app/main.py
git commit -m "feat(recurring): add REST router and register in main app"
```

---

## Task 5: Hook detection into sync

**Files:**
- Modify: `Backend/app/transactions/service.py`

- [ ] **Step 5.1: Add detect_and_upsert call to sync_transactions**

In `Backend/app/transactions/service.py`, after the `await db.flush()` that follows `await categorize_batch(db, new_txns, account.user_id)` (around lines 201–207), add the detection call.

Replace the block:
```python
    # Auto-categorise all newly inserted transactions in one batch.
    if new_txns:
        await categorize_batch(db, new_txns, account.user_id)

    logger.info(
```

With:
```python
    # Auto-categorise all newly inserted transactions in one batch.
    if new_txns:
        await categorize_batch(db, new_txns, account.user_id)
        # Re-detect recurring charges now that new categorised transactions exist
        from app.recurring_charges.service import detect_and_upsert
        await detect_and_upsert(db, account.user_id)

    logger.info(
```

Note: the import is inline to avoid a circular import at module level (transactions → recurring_charges → transactions via models).

- [ ] **Step 5.2: Run tests to confirm no regressions**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests pass.

- [ ] **Step 5.3: Commit**

```bash
git add Backend/app/transactions/service.py
git commit -m "feat(recurring): trigger detection after each banking sync"
```

---

## Task 6: Extend dashboard response

**Files:**
- Modify: `Backend/app/dashboard/schemas.py`
- Modify: `Backend/app/dashboard/service.py`

- [ ] **Step 6.1: Add upcoming_charges to DashboardResponse schema**

In `Backend/app/dashboard/schemas.py`, add the import and field:

Replace the file content with:
```python
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.recurring_charges.schemas import RecurringChargeResponse
from app.transactions.schemas import TransactionResponse


class AccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iban: str | None
    name: str | None
    bank_name: str
    bank_logo: str | None
    balance: Decimal | None
    currency: str


class DashboardResponse(BaseModel):
    total_balance: Decimal
    currency: str
    accounts: list[AccountSummary]
    recent_transactions: list[TransactionResponse]
    last_synced_at: datetime | None
    upcoming_charges: list[RecurringChargeResponse] = []
```

- [ ] **Step 6.2: Fetch upcoming_charges in DashboardService**

In `Backend/app/dashboard/service.py`, add the import and parallel fetch.

At the top, add after the existing imports:
```python
from app.recurring_charges.service import get_upcoming as get_upcoming_charges
```

Replace the `_fetch` inner function inside `get_dashboard` (the part with `asyncio.gather`) with:
```python
        async def _fetch() -> dict[str, object]:
            (accounts, total_balance, last_synced_at), recent_transactions, upcoming_charges = (
                await asyncio.gather(
                    self._fetch_accounts(user_id, user_currency),
                    self._fetch_recent_transactions(user_id),
                    get_upcoming_charges(self._db, user_id),
                )
            )

            response = DashboardResponse(
                total_balance=total_balance,
                currency=user_currency,
                accounts=accounts,
                recent_transactions=recent_transactions,
                last_synced_at=last_synced_at,
                upcoming_charges=upcoming_charges,
            )
            return response.model_dump(mode="json")
```

- [ ] **Step 6.3: Run dashboard tests**

```bash
pytest tests/dashboard/ -v
```
Expected: all pass (upcoming_charges defaults to `[]` so existing assertions aren't broken).

- [ ] **Step 6.4: Run full suite**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests pass.

- [ ] **Step 6.5: Commit**

```bash
git add Backend/app/dashboard/schemas.py Backend/app/dashboard/service.py
git commit -m "feat(recurring): embed upcoming_charges in dashboard response"
```

---

## Task 7: Frontend types + API helper

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useRecurringCharges.ts`

- [ ] **Step 7.1: Add RecurringCharge type and update Dashboard**

In `frontend/src/types/index.ts`, add after the `TransactionList` interface (after line 75) and update `Dashboard`:

```typescript
export interface RecurringCharge {
  id: string;
  display_name: string;
  /** Decimal serialised as string */
  amount: string;
  currency: string;
  periodicity: 'WEEKLY' | 'MONTHLY' | 'ANNUAL';
  status: 'possible' | 'confirmed' | 'dismissed';
  user_confirmed: boolean;
  occurrence_count: number;
  /** ISO date string */
  next_predicted_date: string;
  is_installment: boolean;
  installment_total: number | null;
  installment_paid: number | null;
}
```

And update the `Dashboard` interface to add `upcoming_charges`:
```typescript
export interface Dashboard {
  /** Decimal serialised as string */
  total_balance: string;
  currency: string;
  accounts: AccountSummary[];
  recent_transactions: Transaction[];
  last_synced_at: string | null;
  upcoming_charges: RecurringCharge[];
}
```

- [ ] **Step 7.2: Add recurringApi to api.ts**

In `frontend/src/lib/api.ts`, add at the end of the file (before the `export { ApiError }` line):

```typescript
// ─── Recurring charges endpoints ────────────────────────────────────────────

export const recurringApi = {
  list(): Promise<RecurringCharge[]> {
    return api.get<RecurringCharge[]>('/recurring-charges/');
  },

  confirm(id: string): Promise<RecurringCharge> {
    return api.patch<RecurringCharge>(`/recurring-charges/${id}/confirm`);
  },

  dismiss(id: string): Promise<void> {
    return api.patch<void>(`/recurring-charges/${id}/dismiss`);
  },

  setInstallment(id: string, installment_total: number): Promise<RecurringCharge> {
    return api.patch<RecurringCharge>(`/recurring-charges/${id}/installment`, { installment_total });
  },

  delete(id: string): Promise<void> {
    return api.delete<void>(`/recurring-charges/${id}`);
  },
};
```

Also add the import for `RecurringCharge` at the top of the file (with the other type imports):
```typescript
import type { RecurringCharge } from '@/types';
```

- [ ] **Step 7.3: Create standalone hook**

Create `frontend/src/hooks/useRecurringCharges.ts`:
```typescript
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { recurringApi } from '@/lib/api';

export function useRecurringCharges() {
  return useQuery({
    queryKey: ['recurring-charges'],
    queryFn: () => recurringApi.list(),
    staleTime: 1000 * 60 * 2,
  });
}

export function useRecurringChargeActions() {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['recurring-charges'] });
  };

  const confirm = useMutation({
    mutationFn: (id: string) => recurringApi.confirm(id),
    onSuccess: invalidate,
  });

  const dismiss = useMutation({
    mutationFn: (id: string) => recurringApi.dismiss(id),
    onSuccess: invalidate,
  });

  const setInstallment = useMutation({
    mutationFn: ({ id, total }: { id: string; total: number }) =>
      recurringApi.setInstallment(id, total),
    onSuccess: invalidate,
  });

  const deny = useMutation({
    mutationFn: (id: string) => recurringApi.delete(id),
    onSuccess: invalidate,
  });

  return { confirm, dismiss, setInstallment, deny };
}
```

- [ ] **Step 7.4: Verify TypeScript compiles**

From `frontend/`:
```bash
npm run build 2>&1 | head -40
```
Expected: no type errors related to recurring charges. Build may fail for other pre-existing reasons — only fix recurring-charges related type errors.

- [ ] **Step 7.5: Commit**

```bash
git add frontend/src/types/index.ts \
        frontend/src/lib/api.ts \
        frontend/src/hooks/useRecurringCharges.ts
git commit -m "feat(recurring): add frontend types, API helpers, and hook"
```

---

## Task 8: Dashboard widget

**Files:**
- Modify: `frontend/src/app/(dashboard)/dashboard/page.tsx`

- [ ] **Step 8.1: Update the "Próximos cobros" widget**

In `frontend/src/app/(dashboard)/dashboard/page.tsx`, replace the entire `{/* Próximos cobros */}` block (from line 219 to 228) with the following. Also add the necessary imports and mutation hooks.

First, add imports at the top of the file after the existing imports:
```typescript
import { useQueryClient } from '@tanstack/react-query';
import { CheckCircle, XCircle, X, CreditCard } from 'lucide-react';
import { recurringApi } from '@/lib/api';
import type { RecurringCharge } from '@/types';
```
(Note: `useQueryClient` is already imported — don't duplicate it.)

Add mutation state inside the component function, after `const [isSyncing, setIsSyncing] = useState(false);`:
```typescript
  const [installmentTarget, setInstallmentTarget] = useState<string | null>(null);
  const [installmentInput, setInstallmentInput] = useState('');

  async function handleConfirm(id: string) {
    await recurringApi.confirm(id);
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  }

  async function handleDismiss(id: string) {
    await recurringApi.dismiss(id);
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  }

  async function handleDeny(id: string) {
    await recurringApi.delete(id);
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  }

  async function handleSetInstallment(id: string) {
    const total = parseInt(installmentInput, 10);
    if (!total || total < 1) return;
    await recurringApi.setInstallment(id, total);
    setInstallmentTarget(null);
    setInstallmentInput('');
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  }
```

Replace the `{/* Próximos cobros */}` block (the entire second `<div>` inside the two-column grid) with:
```tsx
          {/* Próximos cobros */}
          <div className="rounded-2xl bg-white p-6 shadow-[0_4px_16px_rgba(48,51,51,0.06)]">
            <h2 className="mb-5 text-base font-bold text-[#303333]">Próximos cobros</h2>

            {(data?.upcoming_charges.length ?? 0) === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f3f4f3]">
                  <Calendar size={22} className="text-[#5d605f]" />
                </div>
                <p className="mt-3 text-sm text-[#5d605f]">No hay cobros próximos detectados.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data?.upcoming_charges.map((charge: RecurringCharge) => (
                  <div
                    key={charge.id}
                    className="rounded-xl border border-[#f0f1f0] p-3"
                  >
                    {/* Row: name + date + amount */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <CreditCard size={13} className="shrink-0 text-[#5d605f]" />
                          <span className="truncate text-sm font-semibold text-[#303333]">
                            {charge.display_name}
                          </span>
                          {/* Status badge */}
                          {charge.status === 'possible' ? (
                            <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                              Posible
                            </span>
                          ) : (
                            <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-bold text-green-700">
                              Confirmado
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-[#5d605f]">
                          {new Date(charge.next_predicted_date).toLocaleDateString('es-ES', {
                            day: 'numeric',
                            month: 'short',
                          })}
                          {' · '}
                          {charge.periodicity === 'MONTHLY'
                            ? 'mensual'
                            : charge.periodicity === 'WEEKLY'
                              ? 'semanal'
                              : 'anual'}
                        </p>
                        {/* Installment progress */}
                        {charge.is_installment &&
                          charge.installment_total != null &&
                          charge.installment_paid != null && (
                            <p className="mt-0.5 text-xs font-medium text-[#0060ad]">
                              {charge.installment_paid} / {charge.installment_total} pagos
                            </p>
                          )}
                      </div>
                      <span className="shrink-0 text-sm font-bold tabular-nums text-[#303333]">
                        {new Intl.NumberFormat('es-ES', {
                          style: 'currency',
                          currency: charge.currency,
                        }).format(parseFloat(charge.amount))}
                      </span>
                    </div>

                    {/* Installment input (shown when setting installment) */}
                    {installmentTarget === charge.id && (
                      <div className="mt-2 flex items-center gap-2">
                        <input
                          type="number"
                          min={1}
                          placeholder="Nº de plazos"
                          value={installmentInput}
                          onChange={(e) => setInstallmentInput(e.target.value)}
                          className="w-28 rounded-lg border border-[#d0d1d0] px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-[#0060ad]"
                        />
                        <button
                          onClick={() => handleSetInstallment(charge.id)}
                          className="rounded-lg bg-[#0060ad] px-2 py-1 text-xs font-semibold text-white hover:opacity-90"
                        >
                          Guardar
                        </button>
                        <button
                          onClick={() => { setInstallmentTarget(null); setInstallmentInput(''); }}
                          className="text-xs text-[#5d605f] hover:text-[#303333]"
                        >
                          Cancelar
                        </button>
                      </div>
                    )}

                    {/* Action buttons */}
                    {!charge.is_installment && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {charge.status === 'possible' && (
                          <>
                            <button
                              onClick={() => handleConfirm(charge.id)}
                              className="flex items-center gap-1 rounded-lg bg-green-50 px-2 py-1 text-xs font-semibold text-green-700 hover:bg-green-100 transition-colors"
                            >
                              <CheckCircle size={11} />
                              Confirmar
                            </button>
                            <button
                              onClick={() => handleDeny(charge.id)}
                              className="flex items-center gap-1 rounded-lg bg-red-50 px-2 py-1 text-xs font-semibold text-red-600 hover:bg-red-100 transition-colors"
                            >
                              <XCircle size={11} />
                              No es recurrente
                            </button>
                          </>
                        )}
                        {charge.status === 'confirmed' && (
                          <>
                            <button
                              onClick={() => handleDismiss(charge.id)}
                              className="flex items-center gap-1 rounded-lg bg-[#f3f4f3] px-2 py-1 text-xs font-semibold text-[#5d605f] hover:bg-[#edeeed] transition-colors"
                            >
                              <X size={11} />
                              Me he dado de baja
                            </button>
                            {installmentTarget !== charge.id && (
                              <button
                                onClick={() => setInstallmentTarget(charge.id)}
                                className="flex items-center gap-1 rounded-lg bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
                              >
                                <CreditCard size={11} />
                                Es un plazo
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
```

- [ ] **Step 8.2: Verify frontend builds**

From `frontend/`:
```bash
npm run build 2>&1 | tail -20
```
Expected: no TypeScript or build errors.

- [ ] **Step 8.3: Run ESLint**

```bash
npm run lint
```
Expected: no new errors.

- [ ] **Step 8.4: Commit**

```bash
git add frontend/src/app/\(dashboard\)/dashboard/page.tsx
git commit -m "feat(recurring): implement Próximos cobros widget with user actions"
```

---

## Task 9: Final verification

- [ ] **Step 9.1: Run full backend test suite**

From `Backend/`:
```bash
pytest tests/ -v --cov=app --cov-report=term-missing 2>&1 | tail -30
```
Expected: all tests pass, coverage includes `app/recurring_charges/`.

- [ ] **Step 9.2: Run backend linter**

```bash
ruff check app/ --fix && ruff format app/
```
Expected: no errors.

- [ ] **Step 9.3: Final commit**

```bash
git add -A
git commit -m "feat(recurring): complete recurring charge detection feature"
```
