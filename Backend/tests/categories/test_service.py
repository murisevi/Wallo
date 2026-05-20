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
        hashed_password="hashed_pw",  # noqa: S106 - test-only fixture value
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
async def bank_account(
    db: AsyncSession,
    user: User,
    bank_connection: BankConnection,
) -> BankAccount:
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
    m.predict_with_margin.return_value = (predicted_name, confidence, 1.0)
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
        """Layer 4: ML score ≥ 0.70 → category assigned as ml_auto.

        Both the merchant dictionary and keyword rules are stubbed out so the
        transaction reaches the ML layer.
        """
        mock_cat = _mock_categorizer("Alimentación", 0.85)

        with (
            patch("app.categories.service.get_categorizer", return_value=mock_cat),
            patch("app.categories.service.match_known_merchant", return_value=None),
            patch("app.categories.service.match_keyword_rule", return_value=None),
        ):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id == category.id
        assert result.confidence_score == pytest.approx(0.85)
        assert result.categorization_method == "ml_auto"

    async def test_ml_suggested_between_thresholds_sets_suggestion_only(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Layer 4: ML score between 0.40 and 0.70 creates a suggestion only.

        Both the merchant dictionary and keyword rules are stubbed out so the
        transaction reaches the ML layer.
        """
        mock_cat = _mock_categorizer("Alimentación", 0.55)

        with (
            patch("app.categories.service.get_categorizer", return_value=mock_cat),
            patch("app.categories.service.match_known_merchant", return_value=None),
            patch("app.categories.service.match_keyword_rule", return_value=None),
        ):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id is None
        assert result.confidence_score == pytest.approx(0.0)
        assert result.categorization_method is None
        assert result.suggested_category_id == category.id
        assert result.suggested_confidence_score == pytest.approx(0.55)
        assert result.suggested_categorization_method == "ml_suggested"

    async def test_ml_below_suggest_threshold_leaves_uncategorised(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Layer 4: ML score below 0.40 creates no category and no suggestion."""
        mock_cat = _mock_categorizer("Alimentación", 0.25)

        with (
            patch("app.categories.service.get_categorizer", return_value=mock_cat),
            patch("app.categories.service.match_known_merchant", return_value=None),
            patch("app.categories.service.match_keyword_rule", return_value=None),
        ):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id is None
        assert result.categorization_method is None
        assert result.confidence_score == pytest.approx(0.0)
        assert result.suggested_category_id is None
        assert result.suggested_confidence_score is None

    async def test_ml_incompatible_income_expense_prediction_is_discarded(
        self,
        db: AsyncSession,
        user: User,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """A debit transaction must not receive an income category."""
        income_category = Category(
            name="Nómina",
            icon="banknote",
            color="#10B981",
            type="income",
            is_custom=False,
        )
        db.add(income_category)
        await db.flush()
        mock_cat = _mock_categorizer("Nómina", 0.95)

        with (
            patch("app.categories.service.get_categorizer", return_value=mock_cat),
            patch("app.categories.service.match_known_merchant", return_value=None),
            patch("app.categories.service.match_keyword_rule", return_value=None),
        ):
            result = await categorize_transaction(db, transaction, user.id)

        assert result.category_id is None
        assert result.suggested_category_id is None

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

    async def test_keyword_strong_assigns_category(
        self,
        db: AsyncSession,
        user: User,
        bank_account: BankAccount,
    ) -> None:
        restaurant = Category(
            name="Restaurantes y Bares",
            icon="utensils",
            color="#F97316",
            type="expense",
            is_custom=False,
        )
        db.add(restaurant)
        txn = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-9.50"),
            currency="EUR",
            date=date(2026, 1, 20),
            description="PAGO MOVIL EN KEBAB, CORIA DEL RIOES, TARJ. :*428024",
            credit_debit_indicator="DBIT",
            status="BOOK",
        )
        db.add(txn)
        await db.flush()

        result = await categorize_transaction(db, txn, user.id)

        assert result.category_id == restaurant.id
        assert result.categorization_method == "keyword_rule"

    async def test_keyword_ambiguous_creates_suggestion_only(
        self,
        db: AsyncSession,
        user: User,
        bank_account: BankAccount,
    ) -> None:
        restaurant = Category(
            name="Restaurantes y Bares",
            icon="utensils",
            color="#F97316",
            type="expense",
            is_custom=False,
        )
        db.add(restaurant)
        txn = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-12.00"),
            currency="EUR",
            date=date(2026, 1, 20),
            description="PAGO MOVIL EN OLIVARES BAR, SEVILLA ES",
            credit_debit_indicator="DBIT",
            status="BOOK",
        )
        db.add(txn)
        await db.flush()

        result = await categorize_transaction(db, txn, user.id)

        assert result.category_id is None
        assert result.suggested_category_id == restaurant.id
        assert result.suggested_categorization_method == "keyword_suggested"

    async def test_mcc_assigns_before_ml(
        self,
        db: AsyncSession,
        user: User,
        bank_account: BankAccount,
    ) -> None:
        restaurant = Category(
            name="Restaurantes y Bares",
            icon="utensils",
            color="#F97316",
            type="expense",
            is_custom=False,
        )
        db.add(restaurant)
        txn = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-18.00"),
            currency="EUR",
            date=date(2026, 1, 20),
            description="UNKNOWN LOCAL",
            credit_debit_indicator="DBIT",
            merchant_category_code="5812",
            status="BOOK",
        )
        db.add(txn)
        await db.flush()

        mock_cat = _mock_categorizer("Alimentación", 0.99)
        with patch("app.categories.service.get_categorizer", return_value=mock_cat):
            result = await categorize_transaction(db, txn, user.id)

        assert result.category_id == restaurant.id
        assert result.categorization_method == "mcc"
        mock_cat.predict_with_margin.assert_not_called()


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
        transaction.suggested_category_id = category.id
        transaction.suggested_confidence_score = 0.55
        transaction.suggested_categorization_method = "ml_suggested"
        result, _also_updated = await correct_category(
            db, user.id, transaction.id, category.id
        )

        assert result.category_id == category.id
        assert result.categorization_method == "manual"
        assert result.confidence_score == pytest.approx(1.0)
        assert result.is_manually_corrected is True
        assert result.suggested_category_id is None
        assert result.suggested_confidence_score is None
        assert result.suggested_categorization_method is None

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

    async def test_blocked_merchant_key_does_not_create_mapping(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
    ) -> None:
        """Generic location-like keys are not learned as merchant mappings."""
        txn = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-12.00"),
            currency="EUR",
            date=date(2026, 1, 16),
            description="PAGO MOVIL EN SAN JUAN DE AZN, SAN JUAN DE AES",
            credit_debit_indicator="DBIT",
            status="BOOK",
        )
        db.add(txn)
        await db.flush()

        await correct_category(db, user.id, txn.id, category.id)
        mappings = (
            await db.execute(
                select(MerchantMapping).where(MerchantMapping.user_id == user.id)
            )
        ).scalars().all()

        assert mappings == []

    async def test_conflicting_correction_marks_mapping_ambiguous(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Conflicting corrections disable merchant-map propagation."""
        other_category = Category(
            name="Otros gastos",
            icon="circle-dot",
            color="#6B7280",
            type="expense",
            is_custom=False,
        )
        db.add(other_category)
        await db.flush()

        await correct_category(db, user.id, transaction.id, category.id)

        txn2 = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-20.00"),
            currency="EUR",
            date=date(2026, 1, 17),
            description="MERCADONA SEVILLA",
            credit_debit_indicator="DBIT",
            status="BOOK",
        )
        txn3 = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-21.00"),
            currency="EUR",
            date=date(2026, 1, 18),
            description="MERCADONA SEVILLA",
            credit_debit_indicator="DBIT",
            status="BOOK",
        )
        db.add_all([txn2, txn3])
        await db.flush()

        _result, also_updated = await correct_category(
            db, user.id, txn2.id, other_category.id
        )
        mapping = (
            await db.execute(
                select(MerchantMapping).where(
                    MerchantMapping.user_id == user.id,
                    MerchantMapping.merchant_name == "MERCADONA SEVILLA",
                )
            )
        ).scalar_one()
        await db.refresh(txn3)

        assert also_updated == 0
        assert mapping.is_ambiguous is True
        assert txn3.category_id is None

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

    async def test_same_merchant_propagation_clears_suggestions(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Same-merchant propagation assigns category and removes stale suggestions."""
        txn2 = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-32.00"),
            currency="EUR",
            date=date(2026, 1, 16),
            description="MERCADONA SEVILLA",
            credit_debit_indicator="DBIT",
            status="BOOK",
            suggested_category_id=category.id,
            suggested_confidence_score=0.55,
            suggested_categorization_method="ml_suggested",
        )
        db.add(txn2)
        await db.flush()

        _result, also_updated = await correct_category(
            db, user.id, transaction.id, category.id
        )
        await db.refresh(txn2)

        assert also_updated == 1
        assert txn2.category_id == category.id
        assert txn2.categorization_method == "merchant_map"
        assert txn2.suggested_category_id is None
        assert txn2.suggested_confidence_score is None

    async def test_same_merchant_propagation_does_not_overwrite_manual(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
        bank_account: BankAccount,
        transaction: Transaction,
    ) -> None:
        """Manual corrections on other transactions are never overwritten."""
        txn2 = Transaction(
            user_id=user.id,
            account_id=bank_account.id,
            amount=Decimal("-32.00"),
            currency="EUR",
            date=date(2026, 1, 16),
            description="MERCADONA SEVILLA",
            credit_debit_indicator="DBIT",
            status="BOOK",
            is_manually_corrected=True,
        )
        db.add(txn2)
        await db.flush()

        _result, also_updated = await correct_category(
            db, user.id, transaction.id, category.id
        )
        await db.refresh(txn2)

        assert also_updated == 0
        assert txn2.category_id is None
        assert txn2.categorization_method is None

    async def test_raises_on_missing_transaction(
        self,
        db: AsyncSession,
        user: User,
        category: Category,
    ) -> None:
        """ValueError is raised when the transaction ID does not exist."""
        with pytest.raises(ValueError, match="not found"):
            await correct_category(db, user.id, uuid.uuid4(), category.id)
