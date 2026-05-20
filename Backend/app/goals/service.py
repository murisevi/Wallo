# Backend/app/goals/service.py
from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.models import BankAccount, BankConnection
from app.goals.models import GoalContribution, SavingsGoal
from app.goals.schemas import (
    ContributionCreate,
    ContributionResponse,
    GoalCreate,
    GoalResponse,
    GoalSummaryResponse,
    GoalUpdate,
)

# ---------------------------------------------------------------------------
# Computed field helpers
# ---------------------------------------------------------------------------


def _compute_percentage(current: Decimal, target: Decimal) -> float:
    if target <= 0:
        return 0.0
    return round(float((current / target) * 100), 2)


def _compute_days_remaining(deadline: date | None) -> int | None:
    if deadline is None:
        return None
    return (deadline - date.today()).days


def _compute_estimated_completion(
    current: Decimal, target: Decimal, monthly: Decimal | None
) -> date | None:
    if monthly is None or monthly <= 0:
        return None
    remaining = target - current
    if remaining <= 0:
        return None
    months_needed = math.ceil(float(remaining / monthly))
    return date.today() + timedelta(days=months_needed * 30)


def _compute_pace_status(
    current: Decimal,
    target: Decimal,
    monthly: Decimal | None,
    deadline: date | None,
) -> str | None:
    if monthly is None or deadline is None:
        return None
    if current >= target:
        return "on_track"
    days_left = (deadline - date.today()).days
    months_until_deadline = max(days_left / 30, 0.1)
    required_monthly = float(target - current) / months_until_deadline
    mc = float(monthly)
    if mc >= required_monthly * 1.1:
        return "ahead"
    if mc >= required_monthly * 0.9:
        return "on_track"
    return "at_risk"


def _compute_motivational_message(percentage: float) -> str:
    if percentage >= 100:
        return "¡Objetivo cumplido! 🎉"
    if percentage >= 75:
        return "¡Ya casi lo tienes!"
    if percentage >= 50:
        return "¡Más de la mitad! Sigue así"
    if percentage >= 25:
        return "Vas por buen camino"
    if percentage > 0:
        return "¡Buen comienzo!"
    return "¡Empieza a ahorrar hoy!"


def _build_goal_response(
    goal: SavingsGoal,
    contributions: list[GoalContribution],
) -> GoalResponse:
    current = Decimal(str(goal.current_amount))
    target = Decimal(str(goal.target_amount))
    monthly = (
        Decimal(str(goal.monthly_contribution))
        if goal.monthly_contribution is not None
        else None
    )
    pct = _compute_percentage(current, target)

    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        icon=goal.icon,
        color=goal.color,
        target_amount=target,
        current_amount=current,
        monthly_contribution=monthly,
        deadline=goal.deadline,
        priority=goal.priority,
        status=goal.status,
        completed_at=goal.completed_at,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        percentage=pct,
        days_remaining=_compute_days_remaining(goal.deadline),
        estimated_completion_date=_compute_estimated_completion(
            current, target, monthly
        ),
        pace_status=_compute_pace_status(current, target, monthly, goal.deadline),
        motivational_message=_compute_motivational_message(pct),
        recent_contributions=[
            ContributionResponse.model_validate(c) for c in contributions
        ],
    )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def _get_goal_or_404(
    db: AsyncSession, goal_id: uuid.UUID, user_id: uuid.UUID
) -> SavingsGoal:
    stmt = select(SavingsGoal).where(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == user_id,
    )
    goal = (await db.execute(stmt)).scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found"
        )
    return goal


async def _get_recent_contributions(
    db: AsyncSession, goal_id: uuid.UUID, limit: int = 5
) -> list[GoalContribution]:
    stmt = (
        select(GoalContribution)
        .where(GoalContribution.goal_id == goal_id)
        .order_by(desc(GoalContribution.created_at))
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_reserved_for_goals(db: AsyncSession, user_id: uuid.UUID) -> Decimal:
    stmt = select(
        func.coalesce(func.sum(SavingsGoal.current_amount), Decimal("0"))
    ).where(
        SavingsGoal.user_id == user_id,
        SavingsGoal.status == "active",
    )
    result = (await db.execute(stmt)).scalar_one()
    return Decimal(str(result or "0"))


async def get_total_bank_balance(
    db: AsyncSession, user_id: uuid.UUID, user_currency: str
) -> Decimal:
    stmt = (
        select(func.coalesce(func.sum(BankAccount.balance_amount), Decimal("0")))
        .select_from(BankAccount)
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .where(
            BankAccount.user_id == user_id,
            BankAccount.currency == user_currency,
            BankAccount.balance_amount.is_not(None),
            BankConnection.status != "disconnected",
        )
    )
    result = (await db.execute(stmt)).scalar_one()
    return Decimal(str(result or "0"))


async def get_available_to_reserve(
    db: AsyncSession, user_id: uuid.UUID, user_currency: str
) -> Decimal:
    total_balance = await get_total_bank_balance(db, user_id, user_currency)
    reserved = await get_reserved_for_goals(db, user_id)
    return total_balance - reserved


async def list_goals(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_currency: str = "EUR",
    status_filter: str = "all",
) -> GoalSummaryResponse:
    stmt = select(SavingsGoal).where(SavingsGoal.user_id == user_id)
    if status_filter != "all":
        stmt = stmt.where(SavingsGoal.status == status_filter)
    stmt = stmt.order_by(desc(SavingsGoal.priority), desc(SavingsGoal.created_at))
    goals = list((await db.execute(stmt)).scalars().all())

    goal_responses: list[GoalResponse] = []
    total_saved = Decimal("0")
    total_target = Decimal("0")
    active_count = 0
    completed_count = 0

    for goal in goals:
        contributions = await _get_recent_contributions(db, goal.id)
        goal_responses.append(_build_goal_response(goal, contributions))
        if goal.status == "active":
            total_saved += Decimal(str(goal.current_amount))
            total_target += Decimal(str(goal.target_amount))
            active_count += 1
        elif goal.status == "completed":
            completed_count += 1

    total_balance = await get_total_bank_balance(db, user_id, user_currency)
    reserved_for_goals = await get_reserved_for_goals(db, user_id)

    return GoalSummaryResponse(
        goals=goal_responses,
        total_saved=total_saved,
        total_target=total_target,
        total_balance=total_balance,
        reserved_for_goals=reserved_for_goals,
        available_to_reserve=total_balance - reserved_for_goals,
        active_count=active_count,
        completed_count=completed_count,
    )


async def get_goal(
    db: AsyncSession, goal_id: uuid.UUID, user_id: uuid.UUID
) -> GoalResponse:
    goal = await _get_goal_or_404(db, goal_id, user_id)
    stmt = (
        select(GoalContribution)
        .where(GoalContribution.goal_id == goal_id)
        .order_by(desc(GoalContribution.created_at))
    )
    contributions = list((await db.execute(stmt)).scalars().all())
    return _build_goal_response(goal, contributions)


async def create_goal(
    db: AsyncSession, user_id: uuid.UUID, data: GoalCreate
) -> GoalResponse:
    goal = SavingsGoal(
        user_id=user_id,
        name=data.name,
        icon=data.icon,
        color=data.color,
        target_amount=data.target_amount,
        current_amount=Decimal("0"),
        monthly_contribution=data.monthly_contribution,
        deadline=data.deadline,
        priority=data.priority,
    )
    db.add(goal)
    await db.flush()
    return _build_goal_response(goal, [])


async def update_goal(
    db: AsyncSession, goal_id: uuid.UUID, user_id: uuid.UUID, data: GoalUpdate
) -> GoalResponse:
    goal = await _get_goal_or_404(db, goal_id, user_id)
    updates = data.model_dump(exclude_unset=True)

    completing = (
        "status" in updates
        and updates["status"] == "completed"
        and goal.status != "completed"
    )
    if completing:
        goal.completed_at = datetime.now(tz=timezone.utc)

    for field, value in updates.items():
        setattr(goal, field, value)

    await db.flush()
    await db.refresh(goal)
    contributions = await _get_recent_contributions(db, goal.id)
    return _build_goal_response(goal, contributions)


async def delete_goal(db: AsyncSession, goal_id: uuid.UUID, user_id: uuid.UUID) -> None:
    goal = await _get_goal_or_404(db, goal_id, user_id)
    # Explicitly delete child contributions before the goal so the cascade
    # works correctly across both PostgreSQL (FK ON DELETE CASCADE) and
    # SQLite in-memory (which ignores FK constraints without PRAGMA foreign_keys=ON).
    contributions_stmt = select(GoalContribution).where(
        GoalContribution.goal_id == goal_id
    )
    contributions = list((await db.execute(contributions_stmt)).scalars().all())
    for contrib in contributions:
        await db.delete(contrib)
    await db.delete(goal)
    await db.flush()


async def add_contribution(
    db: AsyncSession,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ContributionCreate,
    user_currency: str = "EUR",
) -> GoalResponse:
    goal = await _get_goal_or_404(db, goal_id, user_id)

    if goal.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot contribute to a goal that is not active",
        )

    current = Decimal(str(goal.current_amount))
    new_amount = current + data.amount
    if new_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El importe acumulado no puede ser negativo",
        )
    if data.amount > 0:
        available = await get_available_to_reserve(db, user_id, user_currency)
        if data.amount > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No hay suficiente dinero disponible para reservar "
                    f"{data.amount:.2f} €"
                ),
            )

    contribution = GoalContribution(
        goal_id=goal_id,
        user_id=user_id,
        amount=data.amount,
        note=data.note,
    )
    db.add(contribution)
    goal.current_amount = new_amount  # type: ignore[assignment]
    await db.flush()
    await db.refresh(goal)

    contributions = await _get_recent_contributions(db, goal.id)
    return _build_goal_response(goal, contributions)


async def list_contributions(
    db: AsyncSession, goal_id: uuid.UUID, user_id: uuid.UUID
) -> list[ContributionResponse]:
    await _get_goal_or_404(db, goal_id, user_id)
    stmt = (
        select(GoalContribution)
        .where(GoalContribution.goal_id == goal_id)
        .order_by(desc(GoalContribution.created_at))
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [ContributionResponse.model_validate(c) for c in rows]


async def get_active_goal_for_dashboard(
    db: AsyncSession, user_id: uuid.UUID
) -> GoalResponse | None:
    stmt = (
        select(SavingsGoal)
        .where(SavingsGoal.user_id == user_id, SavingsGoal.status == "active")
        .order_by(desc(SavingsGoal.priority), desc(SavingsGoal.created_at))
        .limit(1)
    )
    goal = (await db.execute(stmt)).scalar_one_or_none()
    if goal is None:
        return None
    contributions = await _get_recent_contributions(db, goal.id)
    return _build_goal_response(goal, contributions)
