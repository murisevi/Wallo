"""Unit / integration tests for app.categories.service.

DB-level tests run against an in-memory SQLite database (same engine as all
other service tests).  The ML model is always mocked so tests are fast and
don't depend on trained model artefacts being present on disk.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.banking.models import BankAccount, BankConnection
from app.categories.merchant_mapping import MerchantMapping
from app.categories.models import Category, CategoryCorrection
from app.categories.service import categorize_transaction, correct_category
from app.transactions.models import Transaction

# ── Re-use the in-memory SQLite engine defined in the root conftest ────────────

from tests.conftest import TestSessionLocal


# ── Session fixture ────────────────────────────────────────────────────────────


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Async session backed by the test SQLite engine.

    The autouse *setup_db* fixture (root conftest) has already run
    Base.metadata.create_all, so all tables exist.
    Rolls back at the end to keep tests isolated.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── Model fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
async def user(db: AsyncSession) -> User:
    u = User(
        email=f"svc-test-{uuid.uuid4()}@example.com",
        name="Service Test User",
        hashed_password="hashed_pw",
    )
    db.add(u)
    await db.flush()
    return u


@pytest.fixture
async def category(db: AsyncSession) -> Category:
    c = Category(
        name="Alimentación",
        icon="shopping-cart",
        color="#F97316",
        type="expense",
        is_custom=False,
    )
    db.add(c)
    await db.flush()
    return c


@pytest.fixture
async def bank_connection(db: AsyncSession, user: User) -> BankConnection:
    conn = BankConnection(
        user_id=user.id,
        bank_name="Mock Bank",
        bank_country="ES",
        authorization_id=f"auth-{uuid.uuid4()}",
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest.fixture
async def bank_account(db: AsyncSession, user: User, bank_connection: BankConnection) -> BankAccount:
    acc = BankAccount(
        user_id=user.id,
        connection_id=bank_connection.id,
        external_uid=f"acc-{uuid.uuid4()}",
        currency="EUR",
    )
    db.add(acc)
    await db.flush()
    return acc


@pytest.fixture
async def transaction(
    db: AsyncSession, user: User, bank_account: BankAccount
) -> Transaction:
    txn = Transaction(
        user_id=user.id,
        account_id=bank_account.id,
        amount=Decimal("-45.00"),
        currency="EUR",
        date=date(2026, 1, 15),
        description="MERCADONA SEVILLA",
        credit_debit_indicator="DBIT",
        status="BOOK",
    )
    db.add(txn)
    await db.flush()
    return txn


# ── Helper: a mock categorizer that is_trained and returns a given prediction ──


def _mock_categorizer(predicted_name: str, confidence: float) -> MagicMock:
    m = MagicMock()
    m.is_trained = True
    m.predict.return_value = (predicted_name, confidence)
    return m


# ── categorize_transaction ─────────────────────────────────────────────────────


class TestCategorizeTransaction:

    async def test_merchant_mapping_hit(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Layer 1: merchant mapping exists → direct assignment, confidence 1.0."""
        # "MERCADONA SEVILLA" cleans to "MERCADONA SEVILLA"; extract_merchant_key
        # returns the first two significant (len > 2) words: "MERCADONA SEVILLA".
        db.add(MerchantMapping(
            user_id=user.id,
            merchant_name="MERCADONA SEVILLA",
            category_id=category.id,
        ))
        await db.flush()

        result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id == category.id
        assert result.confidence_score == pytest.approx(1.0)
        assert result.categorization_method == "merchant_map"

    async def test_ml_auto_above_threshold(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Layer 2+3: ML score ≥ 0.70 → category assigned as ml_auto."""
        mock_cat = _mock_categorizer("Alimentación", 0.85)

        with patch("app.categories.service.get_categorizer", return_value=mock_cat):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id == category.id
        assert result.confidence_score == pytest.approx(0.85)
        assert result.categorization_method == "ml_auto"

    async def test_ml_suggested_between_thresholds(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Layer 2+3: ML score between 0.40 and 0.70 → ml_suggested."""
        mock_cat = _mock_categorizer("Alimentación", 0.55)

        with patch("app.categories.service.get_categorizer", return_value=mock_cat):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id == category.id
        assert result.confidence_score == pytest.approx(0.55)
        assert result.categorization_method == "ml_suggested"

    async def test_untrained_model_leaves_uncategorised(
        self,
        db: AsyncSession,
        user: User,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Fallback: model not trained → transaction left uncategorised."""
        mock_cat = MagicMock()
        mock_cat.is_trained = False

        with patch("app.categories.service.get_categorizer", return_value=mock_cat):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id is None
        assert result.categorization_method is None
        assert result.confidence_score == pytest.approx(0.0)

    async def test_merchant_mapping_takes_priority_over_ml(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Layer 1 fires before Layer 2: ML predict is never called when mapping hit."""
        db.add(MerchantMapping(
            user_id=user.id,
            merchant_name="MERCADONA SEVILLA",
            category_id=category.id,
        ))
        await db.flush()

        mock_cat = _mock_categorizer("Transporte", 0.99)  # would win if called

        with patch("app.categories.service.get_categorizer", return_value=mock_cat):
            result = await categorize_transaction(db, transaction, user.id)

        mock_cat.predict.assert_not_called()
        assert result.categorization_method == "merchant_map"


# ── correct_category ───────────────────────────────────────────────────────────


class TestCorrectCategory:

    async def test_transaction_fields_updated(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Transaction is marked manual, is_manually_corrected=True, confidence=1."""
        result = await correct_category(db, user.id, transaction.id, category.id)

        assert result.category_id == category.id
        assert result.categorization_method == "manual"
        assert result.confidence_score == pytest.approx(1.0)
        assert result.is_manually_corrected is True

    async def test_category_correction_row_created(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """A CategoryCorrection row is persisted for future ML retraining."""
        await correct_category(db, user.id, transaction.id, category.id)

        rows = (
            await db.execute(
                select(CategoryCorrection).where(
                    CategoryCorrection.transaction_id == transaction.id,
                    CategoryCorrection.corrected_category_id == category.id,
                )
            )
        ).scalars().all()

        assert len(rows) == 1
        assert rows[0].user_id == user.id
        assert rows[0].original_description == transaction.description

    async def test_merchant_mapping_created(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """A MerchantMapping is upserted so next sync auto-categorises the merchant."""
        await correct_category(db, user.id, transaction.id, category.id)

        mapping = (
            await db.execute(
                select(MerchantMapping).where(
                    MerchantMapping.user_id == user.id,
                    MerchantMapping.category_id == category.id,
                )
            )
        ).scalar_one_or_none()

        assert mapping is not None
        assert mapping.merchant_name == "MERCADONA SEVILLA"

    async def test_second_correction_increments_confidence(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Correcting the same merchant twice increments the mapping confidence."""
        await correct_category(db, user.id, transaction.id, category.id)

        # Second correction (re-fetch the transaction to avoid stale state)
        txn2 = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-32.00"),
            currency="EUR",
            date=date(2026, 1, 16),
            description="MERCADONA SEVILLA",
            credit_debit_indicator="DBIT",
            status="BOOK",
        )
        db.add(txn2)
        await db.flush()

        await correct_category(db, user.id, txn2.id, category.id)

        mapping = (
            await db.execute(
                select(MerchantMapping).where(
                    MerchantMapping.user_id == user.id,
                    MerchantMapping.merchant_name == "MERCADONA SEVILLA",
                )
            )
        ).scalar_one()

        assert mapping.confidence == 2  # started at 1, incremented once

    async def test_raises_on_missing_transaction(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
    ) -> None:
        """ValueError is raised when the transaction ID does not exist."""
        with pytest.raises(ValueError, match="not found"):
            await correct_category(db, user.id, uuid.uuid4(), category.id)
