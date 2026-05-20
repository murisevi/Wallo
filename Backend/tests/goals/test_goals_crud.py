# Backend/tests/goals/test_goals_crud.py
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.goals.models  # noqa: F401 — register metadata with Base
from app.auth.models import User
from app.banking.models import BankAccount, BankConnection
from app.goals.models import GoalContribution, SavingsGoal
from app.goals.schemas import ContributionCreate, GoalCreate, GoalUpdate
from app.goals.service import (
    add_contribution,
    create_goal,
    delete_goal,
    get_goal,
    list_goals,
    update_goal,
)


async def _seed_user(db: AsyncSession) -> uuid.UUID:
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",  # noqa: S106 - test fixture password hash
        name="Test User",
    )
    db.add(user)
    await db.flush()
    return user.id


async def _seed_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    balance: Decimal = Decimal("1000"),
) -> None:
    connection = BankConnection(
        user_id=user_id,
        bank_name="Banco Test",
        bank_country="ES",
        status="active",
    )
    db.add(connection)
    await db.flush()
    db.add(
        BankAccount(
            connection_id=connection.id,
            user_id=user_id,
            external_uid=f"acc_{uuid.uuid4().hex}",
            currency="EUR",
            balance_amount=balance,
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_create_goal_full():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(
                name="Vacaciones",
                target_amount=Decimal("2000"),
                icon="plane",
                color="#F59E0B",
                monthly_contribution=Decimal("200"),
                deadline=None,
                priority=1,
            ),
        )

    assert goal.name == "Vacaciones"
    assert goal.target_amount == Decimal("2000")
    assert goal.current_amount == Decimal("0")
    assert goal.icon == "plane"
    assert goal.color == "#F59E0B"
    assert goal.status == "active"
    assert goal.percentage == 0.0
    assert goal.motivational_message == "¡Empieza a ahorrar hoy!"
    assert goal.recent_contributions == []


@pytest.mark.asyncio
async def test_create_goal_minimal():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        goal = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Fondo de emergencia", target_amount=Decimal("1000")),
        )

    assert goal.name == "Fondo de emergencia"
    assert goal.icon == "piggy-bank"
    assert goal.color == "#3B82F6"
    assert goal.monthly_contribution is None
    assert goal.deadline is None
    assert goal.priority == 0


@pytest.mark.asyncio
async def test_list_goals_ownership_isolation():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_a = await _seed_user(db)
        user_b = await _seed_user(db)
        await create_goal(
            db=db,
            user_id=user_a,
            data=GoalCreate(name="Goal A", target_amount=Decimal("500")),
        )
        await create_goal(
            db=db,
            user_id=user_b,
            data=GoalCreate(name="Goal B", target_amount=Decimal("500")),
        )
        summary_a = await list_goals(db=db, user_id=user_a)
        summary_b = await list_goals(db=db, user_id=user_b)

    assert len(summary_a.goals) == 1
    assert summary_a.goals[0].name == "Goal A"
    assert len(summary_b.goals) == 1
    assert summary_b.goals[0].name == "Goal B"


@pytest.mark.asyncio
async def test_get_goal_detail():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        created = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Coche nuevo", target_amount=Decimal("15000")),
        )
        fetched = await get_goal(db=db, goal_id=created.id, user_id=user_id)

    assert fetched.id == created.id
    assert fetched.name == "Coche nuevo"


@pytest.mark.asyncio
async def test_update_goal():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        created = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Original", target_amount=Decimal("1000")),
        )
        updated = await update_goal(
            db=db,
            goal_id=created.id,
            user_id=user_id,
            data=GoalUpdate(name="Updated", target_amount=Decimal("2000")),
        )

    assert updated.name == "Updated"
    assert updated.target_amount == Decimal("2000")


@pytest.mark.asyncio
async def test_mark_completed_sets_completed_at():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        created = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Completado", target_amount=Decimal("500")),
        )
        updated = await update_goal(
            db=db,
            goal_id=created.id,
            user_id=user_id,
            data=GoalUpdate(status="completed"),
        )

    assert updated.status == "completed"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_delete_goal_cascade():
    from sqlalchemy import select

    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
        await _seed_account(db, user_id)
        created = await create_goal(
            db=db,
            user_id=user_id,
            data=GoalCreate(name="Para borrar", target_amount=Decimal("1000")),
        )
        await add_contribution(
            db=db,
            goal_id=created.id,
            user_id=user_id,
            data=ContributionCreate(amount=Decimal("100")),
        )
        await delete_goal(db=db, goal_id=created.id, user_id=user_id)
        remaining_goals = (
            await db.execute(select(SavingsGoal).where(SavingsGoal.id == created.id))
        ).scalar_one_or_none()
        remaining_contributions = (
            await db.execute(
                select(GoalContribution).where(
                    GoalContribution.goal_id == created.id
                )
            )
        ).scalars().all()

    assert remaining_goals is None
    assert len(remaining_contributions) == 0


@pytest.mark.asyncio
async def test_create_goal_rejects_zero_target():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GoalCreate(name="Invalido", target_amount=Decimal("0"))

    with pytest.raises(ValidationError):
        GoalCreate(name="Invalido", target_amount=Decimal("-100"))
