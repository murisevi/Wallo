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
from app.recurring_charges import service as svc
from app.recurring_charges.models import RecurringCharge
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
        hashed_password="hashed",  # noqa: S106
    )
    db.add(u)
    await db.flush()
    return u


@pytest.fixture
async def connection(db: AsyncSession, user: User) -> BankConnection:
    conn = BankConnection(
        user_id=user.id,
        bank_name="Test Bank",
        bank_country="ES",
        session_id=str(uuid.uuid4()),
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest.fixture
async def account(
    db: AsyncSession, user: User, connection: BankConnection
) -> BankAccount:
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


def make_txn(
    account: BankAccount,
    user: User,
    d: date,
    amount: str = "-9.99",
    description: str = "NETFLIX",
) -> Transaction:
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
            make_txn(account, user, BASE + timedelta(days=30 * i)) for i in range(4)
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

        # Add more transactions
        txns = [
            make_txn(account, user, BASE + timedelta(days=30 * i)) for i in range(4)
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

    async def test_dismiss_possible_charge_blocks_future_detection(
        self, db: AsyncSession, user: User, account: BankAccount
    ):
        """A false positive marked as dismissed should not be recreated."""
        txns = [
            make_txn(account, user, BASE + timedelta(days=30 * i)) for i in range(3)
        ]
        for txn in txns:
            db.add(txn)
        await db.flush()

        await svc.detect_and_upsert(db, user.id)
        charges = await svc.get_upcoming(db, user.id)
        assert len(charges) == 1
        assert charges[0].status == "possible"

        await svc.dismiss(db, user.id, charges[0].id)
        await svc.detect_and_upsert(db, user.id)

        assert await svc.get_upcoming(db, user.id) == []
        dismissed = await svc.get_by_id(db, user.id, charges[0].id)
        assert dismissed is not None
        assert dismissed.status == "dismissed"

    async def test_dismiss_missing_charge_is_noop(
        self, db: AsyncSession, user: User
    ):
        await svc.dismiss(db, user.id, uuid.uuid4())


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
        # occurrence_count becomes installment_paid
        assert updated.installment_paid == 3


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

    async def test_delete_missing_charge_is_noop(self, db: AsyncSession, user: User):
        await svc.delete(db, user.id, uuid.uuid4())
