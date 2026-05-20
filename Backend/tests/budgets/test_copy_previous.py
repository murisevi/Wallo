"""Tests for copy_previous_month service function."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.budgets.models  # noqa: F401 — ensure Budget + Category metadata is registered
from app.budgets.service import copy_previous_month, create_budget
from app.budgets.schemas import BudgetCreate
from app.budgets.models import Category
from app.auth.models import User


async def _seed_user_and_category(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a test user and a test category, return (user_id, category_id)."""
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",
        name="Test User",
    )
    db.add(user)
    await db.flush()

    category = Category(
        name="Alimentación",
        icon="shopping-cart",
        color="#16a34a",
        type="expense",
        user_id=None,  # system category
    )
    db.add(category)
    await db.flush()

    return user.id, category.id


@pytest.mark.asyncio
async def test_copy_previous_month_creates_budgets():
    """copy_previous_month should clone budgets from M-1 into M."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, category_id = await _seed_user_and_category(db)

        # Create a budget in month 3/2025
        await create_budget(
            db=db,
            user_id=user_id,
            data=BudgetCreate(
                category_id=category_id,
                amount_limit=Decimal("500"),
                month=3,
                year=2025,
            ),
        )

        # Copy to month 4/2025
        summary = await copy_previous_month(db=db, user_id=user_id, month=4, year=2025)

    assert len(summary.budgets) == 1
    assert summary.month == 4
    assert summary.year == 2025
    assert summary.budgets[0].amount_limit == Decimal("500")


@pytest.mark.asyncio
async def test_copy_previous_month_skips_duplicates():
    """copy_previous_month must not fail if some budgets already exist for the target month."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, category_id = await _seed_user_and_category(db)

        # Create budget in month 3 and also in month 4 (duplicate)
        for m in (3, 4):
            await create_budget(
                db=db,
                user_id=user_id,
                data=BudgetCreate(
                    category_id=category_id,
                    amount_limit=Decimal("500"),
                    month=m,
                    year=2025,
                ),
            )

        # Copying again to month 4 should not raise
        summary = await copy_previous_month(db=db, user_id=user_id, month=4, year=2025)

    assert len(summary.budgets) == 1


@pytest.mark.asyncio
async def test_copy_previous_month_returns_empty_when_previous_empty():
    """If M-1 has no budgets, the result for M is also empty."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, _ = await _seed_user_and_category(db)
        summary = await copy_previous_month(db=db, user_id=user_id, month=4, year=2025)

    assert summary.budgets == []


@pytest.mark.asyncio
async def test_copy_previous_month_wraps_january_to_december():
    """Copying from January should look at December of the previous year."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id, category_id = await _seed_user_and_category(db)

        await create_budget(
            db=db,
            user_id=user_id,
            data=BudgetCreate(
                category_id=category_id,
                amount_limit=Decimal("300"),
                month=12,
                year=2024,
            ),
        )

        # Copy to January 2025
        summary = await copy_previous_month(db=db, user_id=user_id, month=1, year=2025)

    assert len(summary.budgets) == 1
    assert summary.month == 1
    assert summary.year == 2025
    assert summary.budgets[0].amount_limit == Decimal("300")
