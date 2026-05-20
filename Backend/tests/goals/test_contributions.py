# Backend/tests/goals/test_contributions.py
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.goals.models  # noqa: F401
from app.auth.models import User
from app.banking.models import BankAccount, BankConnection
from app.goals.schemas import ContributionCreate, GoalCreate, GoalUpdate
from app.goals.service import (
    add_contribution,
    create_goal,
    list_contributions,
    update_goal,
)


async def _seed_user(db: AsyncSession) -> uuid.UUID:
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",  # noqa: S106 - test fixture password hash
        name="Test",
    )
    db.add(user)
    await db.flush()
    return user.id


async def _seed_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    balance: Decimal = Decimal("1000"),
    currency: str = "EUR",
    status: str = "active",
) -> None:
    connection = BankConnection(
        user_id=user_id,
        bank_name="Banco Test",
        bank_country="ES",
        status=status,
    )
    db.add(connection)
    await db.flush()
    db.add(
        BankAccount(
            connection_id=connection.id,
            user_id=user_id,
            external_uid=f"acc_{uuid.uuid4().hex}",
            currency=currency,
            balance_amount=balance,
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_add_deposit():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Ahorro", target_amount=Decimal("1000")),
        )
        updated = await add_contribution(
            db=db,
            goal_id=goal.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("200"), note="Paga extra"),
        )

    assert updated.current_amount == Decimal("200")
    assert len(updated.recent_contributions) == 1
    assert updated.recent_contributions[0].amount == Decimal("200")
    assert updated.recent_contributions[0].note == "Paga extra"


@pytest.mark.asyncio
async def test_add_withdrawal():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Ahorro", target_amount=Decimal("1000")),
        )
        await add_contribution(
            db=db,
            goal_id=goal.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("500")),
        )
        updated = await add_contribution(
            db=db,
            goal_id=goal.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("-100")),
        )

    assert updated.current_amount == Decimal("400")


@pytest.mark.asyncio
async def test_withdrawal_below_zero_rejected():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Ahorro", target_amount=Decimal("1000")),
        )
        with pytest.raises(HTTPException) as exc_info:
            await add_contribution(
                db=db,
                goal_id=goal.id,
                user_id=user_id,
                data=ContributionCreate(amount=Decimal("-1")),
            )

    assert exc_info.value.status_code == 400
    assert "negativo" in exc_info.value.detail


@pytest.mark.asyncio
async def test_contribute_to_non_active_rejected():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Completado", target_amount=Decimal("500")),
        )
        await update_goal(
            db=db,
            goal_id=goal.id,
            user_id=user_id,
            data=GoalUpdate(status="completed"),
        )
        with pytest.raises(HTTPException) as exc_info:
            await add_contribution(
                db=db,
                goal_id=goal.id,
                user_id=user_id,
                data=ContributionCreate(amount=Decimal("100")),
            )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_list_contributions_ordered_desc():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Ahorro", target_amount=Decimal("1000")),
        )
        for amount in [Decimal("100"), Decimal("200"), Decimal("300")]:
            await add_contribution(
                db=db,
                goal_id=goal.id,
                user_id=user_id,
                data=ContributionCreate(amount=amount),
            )
        contributions = await list_contributions(
            db=db, goal_id=goal.id, user_id=user_id
        )

    assert len(contributions) == 3
    # Verify all expected amounts are present regardless of ordering
    amounts = {c.amount for c in contributions}
    assert amounts == {Decimal("100"), Decimal("200"), Decimal("300")}
    # Verify result is sorted DESC by created_at: no contribution should appear
    # after one with an earlier timestamp (stable check that works even when
    # timestamps tie at sub-second resolution in SQLite in-memory tests)
    for i in range(len(contributions) - 1):
        assert contributions[i].created_at >= contributions[i + 1].created_at


@pytest.mark.asyncio
async def test_deposit_above_available_balance_rejected():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id, balance=Decimal("100"))
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Viaje", target_amount=Decimal("500")),
        )
        with pytest.raises(HTTPException) as exc_info:
            await add_contribution(
                db=db,
                goal_id=goal.id,
                user_id=user_id,
                data=ContributionCreate(amount=Decimal("101")),
            )

    assert exc_info.value.status_code == 400
    assert "disponible" in exc_info.value.detail


@pytest.mark.asyncio
async def test_user_without_accounts_cannot_reserve_money():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Viaje", target_amount=Decimal("500")),
        )
        with pytest.raises(HTTPException) as exc_info:
            await add_contribution(
                db=db,
                goal_id=goal.id,
                user_id=user_id,
                data=ContributionCreate(amount=Decimal("1")),
            )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_other_user_reservations_do_not_reduce_available_balance():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_a = await _seed_user(db)
        user_b = await _seed_user(db)
        await _seed_account(db, user_a, balance=Decimal("100"))
        await _seed_account(db, user_b, balance=Decimal("100"))

        goal_a = await create_goal(
            db=db,
            user_id=user_a,
            data=GoalCreate(name="A", target_amount=Decimal("500")),
        )
        goal_b = await create_goal(
            db=db,
            user_id=user_b,
            data=GoalCreate(name="B", target_amount=Decimal("500")),
        )
        await add_contribution(
            db=db,
            goal_id=goal_b.id,
            user_id=user_b,
            data=ContributionCreate(amount=Decimal("100")),
        )
        updated = await add_contribution(
            db=db,
            goal_id=goal_a.id,
            user_id=user_a,
            data=ContributionCreate(amount=Decimal("100")),
        )

    assert updated.current_amount == Decimal("100")


@pytest.mark.asyncio
async def test_completed_and_cancelled_goals_do_not_count_as_active_reserves():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id, balance=Decimal("100"))
        completed = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Completado", target_amount=Decimal("500")),
        )
        cancelled = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Cancelado", target_amount=Decimal("500")),
        )
        active = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Activo", target_amount=Decimal("500")),
        )

        await add_contribution(
            db=db,
            goal_id=completed.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("80")),
        )
        await update_goal(
            db=db,
            goal_id=completed.id,
            user_id=user_id,
            data=GoalUpdate(status="completed"),
        )
        await add_contribution(
            db=db,
            goal_id=cancelled.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("80")),
        )
        await update_goal(
            db=db,
            goal_id=cancelled.id,
            user_id=user_id,
            data=GoalUpdate(status="cancelled"),
        )
        updated = await add_contribution(
            db=db,
            goal_id=active.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("100")),
        )

    assert updated.current_amount == Decimal("100")
