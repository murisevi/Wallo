# Savings Goals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full "Objetivos de Ahorro" (Savings Goals) feature — backend domain + REST API + frontend page + dashboard integration.

**Architecture:** Domain-per-folder pattern (`app/goals/`) following the existing `app/budgets/` structure. Backend: SQLAlchemy 2.0 models → Pydantic v2 schemas → service logic → FastAPI router. Frontend: TypeScript types → `goalsApi` in `lib/api.ts` → `useGoals` hook → 8 feature components → goals page.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 async / Pydantic v2 / Alembic / Next.js App Router / TypeScript strict / TanStack React Query v5 / Tailwind CSS v4 / lucide-react

---

## File Map

**Create:**
- `Backend/app/goals/__init__.py`
- `Backend/app/goals/models.py`
- `Backend/app/goals/schemas.py`
- `Backend/app/goals/service.py`
- `Backend/app/goals/router.py`
- `Backend/tests/goals/__init__.py`
- `Backend/tests/goals/test_goals_crud.py`
- `Backend/tests/goals/test_contributions.py`
- `Backend/tests/goals/test_computed_fields.py`
- `frontend/src/types/goals.ts`
- `frontend/src/hooks/useGoals.ts`
- `frontend/src/components/features/goals/GoalProgressBar.tsx`
- `frontend/src/components/features/goals/GoalEmptyState.tsx`
- `frontend/src/components/features/goals/DeleteGoalDialog.tsx`
- `frontend/src/components/features/goals/ContributionPanel.tsx`
- `frontend/src/components/features/goals/GoalCard.tsx`
- `frontend/src/components/features/goals/GoalSummaryCard.tsx`
- `frontend/src/components/features/goals/NewGoalModal.tsx`
- `frontend/src/components/features/goals/EditGoalModal.tsx`
- `frontend/src/app/(dashboard)/goals/page.tsx`
- `frontend/src/app/(dashboard)/goals/loading.tsx`

**Modify:**
- `Backend/alembic/env.py` — add goals model imports
- `Backend/app/main.py` — register goals router
- `Backend/app/dashboard/schemas.py` — add `active_goal` field
- `Backend/app/dashboard/service.py` — add `_fetch_active_goal`
- `frontend/src/lib/api.ts` — add `goalsApi`
- `frontend/src/types/index.ts` — add `active_goal` to `Dashboard`
- `frontend/src/app/(dashboard)/layout.tsx` — add sidebar link
- `frontend/src/app/(dashboard)/dashboard/page.tsx` — add goal widget
- `PROJECT_STATUS.md` — update status table
- `CLAUDE.md` — add goals to project structure

---

## Task 1: Goals domain models

**Files:**
- Create: `Backend/app/goals/__init__.py`
- Create: `Backend/app/goals/models.py`

- [ ] **Step 1: Create `__init__.py`**

```python
# Backend/app/goals/__init__.py
```
(empty file)

- [ ] **Step 2: Write `models.py`**

```python
# Backend/app/goals/models.py
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="piggy-bank")
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    target_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    monthly_contribution: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_savings_goals_target_positive"),
        CheckConstraint(
            "current_amount >= 0", name="ck_savings_goals_current_nonnegative"
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_savings_goals_status",
        ),
    )


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("savings_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 3: Verify import works**

```bash
cd Backend && python -c "from app.goals.models import SavingsGoal, GoalContribution; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add Backend/app/goals/__init__.py Backend/app/goals/models.py
git commit -m "feat(goals): add SavingsGoal and GoalContribution SQLAlchemy models"
```

---

## Task 2: Alembic env update + migration

**Files:**
- Modify: `Backend/alembic/env.py`
- Generated: `Backend/alembic/versions/<timestamp>_add_savings_goals.py`

- [ ] **Step 1: Add goals imports to `env.py`**

In `Backend/alembic/env.py`, after the existing model imports (line 20), add:

```python
from app.goals.models import GoalContribution, SavingsGoal  # noqa: F401
```

- [ ] **Step 2: Generate migration**

```bash
cd Backend && alembic revision --autogenerate -m "add_savings_goals_and_contributions"
```
Expected: a new file in `Backend/alembic/versions/` containing `create_table("savings_goals", ...)` and `create_table("goal_contributions", ...)`.

- [ ] **Step 3: Run migration**

```bash
cd Backend && alembic upgrade head
```
Expected: `Running upgrade ... -> <rev>` with no errors.

- [ ] **Step 4: Commit**

```bash
git add Backend/alembic/env.py Backend/alembic/versions/
git commit -m "feat(goals): add Alembic migration for savings_goals and goal_contributions tables"
```

---

## Task 3: Goals schemas

**Files:**
- Create: `Backend/app/goals/schemas.py`

- [ ] **Step 1: Write `schemas.py`**

```python
# Backend/app/goals/schemas.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class GoalCreate(BaseModel):
    name: str
    target_amount: Decimal
    icon: str = "piggy-bank"
    color: str = "#3B82F6"
    monthly_contribution: Decimal | None = None
    deadline: date | None = None
    priority: int = 0

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        if len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v.strip()

    @field_validator("target_amount")
    @classmethod
    def target_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("target_amount must be greater than 0")
        return v

    @field_validator("monthly_contribution")
    @classmethod
    def contribution_must_be_positive_or_none(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("monthly_contribution must be greater than 0")
        return v


class GoalUpdate(BaseModel):
    name: str | None = None
    target_amount: Decimal | None = None
    icon: str | None = None
    color: str | None = None
    monthly_contribution: Decimal | None = None
    deadline: date | None = None
    priority: int | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "completed", "cancelled"):
            raise ValueError("status must be 'active', 'completed', or 'cancelled'")
        return v

    @field_validator("target_amount")
    @classmethod
    def target_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("target_amount must be greater than 0")
        return v


class ContributionCreate(BaseModel):
    amount: Decimal
    note: str | None = None

    @field_validator("note")
    @classmethod
    def note_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v


class ContributionResponse(BaseModel):
    id: uuid.UUID
    goal_id: uuid.UUID
    amount: Decimal
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GoalResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    icon: str
    color: str
    target_amount: Decimal
    current_amount: Decimal
    monthly_contribution: Decimal | None
    deadline: date | None
    priority: int
    status: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Computed fields
    percentage: float
    days_remaining: int | None
    estimated_completion_date: date | None
    pace_status: str | None
    motivational_message: str
    recent_contributions: list[ContributionResponse]

    model_config = {"from_attributes": False}


class GoalSummaryResponse(BaseModel):
    goals: list[GoalResponse]
    total_saved: Decimal
    total_target: Decimal
    active_count: int
    completed_count: int
```

- [ ] **Step 2: Verify import**

```bash
cd Backend && python -c "from app.goals.schemas import GoalCreate, GoalResponse, GoalSummaryResponse; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add Backend/app/goals/schemas.py
git commit -m "feat(goals): add Pydantic v2 schemas for goals domain"
```

---

## Task 4: Goals service

**Files:**
- Create: `Backend/app/goals/service.py`

- [ ] **Step 1: Write `service.py`**

```python
# Backend/app/goals/service.py
from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    required_monthly = float((target - current)) / months_until_deadline
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


async def list_goals(
    db: AsyncSession,
    user_id: uuid.UUID,
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

    return GoalSummaryResponse(
        goals=goal_responses,
        total_saved=total_saved,
        total_target=total_target,
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

    if "status" in updates and updates["status"] == "completed" and goal.status != "completed":
        goal.completed_at = datetime.now(tz=timezone.utc)

    for field, value in updates.items():
        setattr(goal, field, value)

    await db.flush()
    contributions = await _get_recent_contributions(db, goal.id)
    return _build_goal_response(goal, contributions)


async def delete_goal(
    db: AsyncSession, goal_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    goal = await _get_goal_or_404(db, goal_id, user_id)
    await db.delete(goal)
    await db.flush()


async def add_contribution(
    db: AsyncSession,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ContributionCreate,
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

    contribution = GoalContribution(
        goal_id=goal_id,
        user_id=user_id,
        amount=data.amount,
        note=data.note,
    )
    db.add(contribution)
    goal.current_amount = new_amount  # type: ignore[assignment]
    await db.flush()

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
```

- [ ] **Step 2: Verify import**

```bash
cd Backend && python -c "from app.goals.service import list_goals, create_goal; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add Backend/app/goals/service.py
git commit -m "feat(goals): add goals service with CRUD, computed fields, and contribution logic"
```

---

## Task 5: Goals router

**Files:**
- Create: `Backend/app/goals/router.py`

- [ ] **Step 1: Write `router.py`**

```python
# Backend/app/goals/router.py
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import CurrentUser, DbSession
from app.goals.schemas import (
    ContributionCreate,
    ContributionResponse,
    GoalCreate,
    GoalResponse,
    GoalSummaryResponse,
    GoalUpdate,
)
from app.goals.service import (
    add_contribution,
    create_goal,
    delete_goal,
    get_goal,
    list_contributions,
    list_goals,
    update_goal,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=GoalSummaryResponse)
async def list_goals_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    status: Annotated[
        str,
        Query(description="Filter by status: active, completed, cancelled, all"),
    ] = "all",
) -> GoalSummaryResponse:
    return await list_goals(db=db, user_id=current_user.id, status_filter=status)


@router.post("/", response_model=GoalResponse, status_code=201)
async def create_goal_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    data: GoalCreate,
) -> GoalResponse:
    return await create_goal(db=db, user_id=current_user.id, data=data)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    goal_id: uuid.UUID,
) -> GoalResponse:
    return await get_goal(db=db, goal_id=goal_id, user_id=current_user.id)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    goal_id: uuid.UUID,
    data: GoalUpdate,
) -> GoalResponse:
    return await update_goal(db=db, goal_id=goal_id, user_id=current_user.id, data=data)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_goal_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    goal_id: uuid.UUID,
) -> None:
    await delete_goal(db=db, goal_id=goal_id, user_id=current_user.id)


@router.post("/{goal_id}/contributions", response_model=GoalResponse)
async def add_contribution_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    goal_id: uuid.UUID,
    data: ContributionCreate,
) -> GoalResponse:
    return await add_contribution(
        db=db, goal_id=goal_id, user_id=current_user.id, data=data
    )


@router.get("/{goal_id}/contributions", response_model=list[ContributionResponse])
async def list_contributions_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    goal_id: uuid.UUID,
) -> list[ContributionResponse]:
    return await list_contributions(db=db, goal_id=goal_id, user_id=current_user.id)
```

- [ ] **Step 2: Commit**

```bash
git add Backend/app/goals/router.py
git commit -m "feat(goals): add goals FastAPI router with 7 endpoints"
```

---

## Task 6: Register router in main.py

**Files:**
- Modify: `Backend/app/main.py`

- [ ] **Step 1: Add import and register**

After the existing router imports (after line `from app.transactions.router import ...`), add:

```python
from app.goals.router import router as goals_router  # noqa: E402
```

After `app.include_router(recurring_charges_router, prefix="/api/v1")`, add:

```python
app.include_router(goals_router, prefix="/api/v1")
```

- [ ] **Step 2: Verify server starts**

```bash
cd Backend && python -c "from app.main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add Backend/app/main.py
git commit -m "feat(goals): register goals router in FastAPI app"
```

---

## Task 7: Backend tests — CRUD

**Files:**
- Create: `Backend/tests/goals/__init__.py`
- Create: `Backend/tests/goals/test_goals_crud.py`

- [ ] **Step 1: Write `__init__.py`**

Empty file.

- [ ] **Step 2: Write failing tests first**

```python
# Backend/tests/goals/test_goals_crud.py
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

import app.goals.models  # noqa: F401 — register metadata
from app.auth.models import User
from app.goals.models import GoalContribution, SavingsGoal
from app.goals.schemas import GoalCreate, GoalUpdate
from app.goals.service import (
    create_goal,
    delete_goal,
    get_goal,
    list_goals,
    update_goal,
)


async def _seed_user(db) -> uuid.UUID:
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",
        name="Test User",
    )
    db.add(user)
    await db.flush()
    return user.id


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
    assert goal.status == "active"
    assert goal.percentage == 0.0
    assert goal.motivational_message == "¡Empieza a ahorrar hoy!"


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
    from app.goals.schemas import ContributionCreate
    from app.goals.service import add_contribution

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
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
            await db.execute(
                select(SavingsGoal).where(SavingsGoal.id == created.id)
            )
        ).scalar_one_or_none()
        remaining_contributions = (
            await db.execute(
                select(GoalContribution).where(GoalContribution.goal_id == created.id)
            )
        ).scalars().all()

    assert remaining_goals is None
    assert len(remaining_contributions) == 0


@pytest.mark.asyncio
async def test_create_goal_rejects_zero_target():
    from tests.conftest import TestSessionLocal
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GoalCreate(name="Invalido", target_amount=Decimal("0"))

    with pytest.raises(ValidationError):
        GoalCreate(name="Invalido", target_amount=Decimal("-100"))
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
cd Backend && pytest tests/goals/test_goals_crud.py -v
```
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add Backend/tests/goals/__init__.py Backend/tests/goals/test_goals_crud.py
git commit -m "test(goals): add CRUD tests for savings goals"
```

---

## Task 8: Backend tests — contributions

**Files:**
- Create: `Backend/tests/goals/test_contributions.py`

- [ ] **Step 1: Write tests**

```python
# Backend/tests/goals/test_contributions.py
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

import app.goals.models  # noqa: F401
from app.auth.models import User
from app.goals.schemas import ContributionCreate, GoalCreate, GoalUpdate
from app.goals.service import add_contribution, create_goal, list_contributions, update_goal


async def _seed_user(db) -> uuid.UUID:
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",
        name="Test",
    )
    db.add(user)
    await db.flush()
    return user.id


@pytest.mark.asyncio
async def test_add_deposit():
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user_id = await _seed_user(db)
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
    # Most recent first — SQLite preserves insertion order with DESC
    assert contributions[0].amount == Decimal("300")
    assert contributions[2].amount == Decimal("100")
```

- [ ] **Step 2: Run tests**

```bash
cd Backend && pytest tests/goals/test_contributions.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add Backend/tests/goals/test_contributions.py
git commit -m "test(goals): add contribution tests (deposit, withdrawal, validations)"
```

---

## Task 9: Backend tests — computed fields

**Files:**
- Create: `Backend/tests/goals/test_computed_fields.py`

- [ ] **Step 1: Write tests**

```python
# Backend/tests/goals/test_computed_fields.py
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.goals.service import (
    _compute_days_remaining,
    _compute_estimated_completion,
    _compute_motivational_message,
    _compute_pace_status,
    _compute_percentage,
)


def test_percentage_normal():
    assert _compute_percentage(Decimal("250"), Decimal("1000")) == 25.0


def test_percentage_complete():
    assert _compute_percentage(Decimal("1000"), Decimal("1000")) == 100.0


def test_percentage_over():
    assert _compute_percentage(Decimal("1200"), Decimal("1000")) == 120.0


def test_percentage_zero_current():
    assert _compute_percentage(Decimal("0"), Decimal("1000")) == 0.0


def test_days_remaining_future():
    future = date.today() + timedelta(days=30)
    assert _compute_days_remaining(future) == 30


def test_days_remaining_past():
    past = date.today() - timedelta(days=5)
    assert _compute_days_remaining(past) == -5


def test_days_remaining_none():
    assert _compute_days_remaining(None) is None


def test_estimated_completion_basic():
    result = _compute_estimated_completion(
        Decimal("0"), Decimal("1200"), Decimal("100")
    )
    assert result is not None
    assert result > date.today()


def test_estimated_completion_no_monthly():
    assert _compute_estimated_completion(Decimal("0"), Decimal("1000"), None) is None


def test_estimated_completion_already_done():
    assert (
        _compute_estimated_completion(Decimal("1000"), Decimal("1000"), Decimal("100"))
        is None
    )


def test_pace_status_ahead():
    deadline = date.today() + timedelta(days=300)
    # Need 1000€, 10 months, 100€/month required — contributing 200€ = ahead
    result = _compute_pace_status(
        Decimal("0"), Decimal("1000"), Decimal("200"), deadline
    )
    assert result == "ahead"


def test_pace_status_on_track():
    deadline = date.today() + timedelta(days=300)
    # ~10 months, ~100€/month required, contributing 100€ = on_track
    result = _compute_pace_status(
        Decimal("0"), Decimal("1000"), Decimal("100"), deadline
    )
    assert result == "on_track"


def test_pace_status_at_risk():
    deadline = date.today() + timedelta(days=60)
    # 2 months, 500€/month required, contributing 50€ = at_risk
    result = _compute_pace_status(
        Decimal("0"), Decimal("1000"), Decimal("50"), deadline
    )
    assert result == "at_risk"


def test_pace_status_no_deadline():
    assert _compute_pace_status(Decimal("0"), Decimal("1000"), Decimal("100"), None) is None


def test_pace_status_no_monthly():
    deadline = date.today() + timedelta(days=60)
    assert _compute_pace_status(Decimal("0"), Decimal("1000"), None, deadline) is None


@pytest.mark.parametrize(
    "percentage,expected",
    [
        (100.0, "¡Objetivo cumplido! 🎉"),
        (120.0, "¡Objetivo cumplido! 🎉"),
        (75.0, "¡Ya casi lo tienes!"),
        (80.0, "¡Ya casi lo tienes!"),
        (50.0, "¡Más de la mitad! Sigue así"),
        (60.0, "¡Más de la mitad! Sigue así"),
        (25.0, "Vas por buen camino"),
        (40.0, "Vas por buen camino"),
        (1.0, "¡Buen comienzo!"),
        (24.9, "Vas por buen camino"),
        (0.0, "¡Empieza a ahorrar hoy!"),
    ],
)
def test_motivational_message(percentage, expected):
    assert _compute_motivational_message(percentage) == expected
```

- [ ] **Step 2: Run all goals tests**

```bash
cd Backend && pytest tests/goals/ -v
```
Expected: All tests PASS (green).

- [ ] **Step 3: Run ruff**

```bash
cd Backend && ruff check app/goals/ --fix && ruff format app/goals/
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add Backend/tests/goals/test_computed_fields.py
git commit -m "test(goals): add computed field unit tests (percentage, pace, messages)"
```

---

## Task 10: Frontend types

**Files:**
- Create: `frontend/src/types/goals.ts`

- [ ] **Step 1: Write `goals.ts`**

```typescript
// frontend/src/types/goals.ts
// Decimal fields serialised as string by FastAPI. Create/Update use number (user input).

export interface SavingsGoal {
  id: string;
  user_id: string;
  name: string;
  icon: string;
  color: string;
  /** Decimal → string */
  target_amount: string;
  /** Decimal → string */
  current_amount: string;
  /** Decimal → string | null */
  monthly_contribution: string | null;
  deadline: string | null;
  priority: number;
  status: 'active' | 'completed' | 'cancelled';
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  // Computed fields
  percentage: number;
  days_remaining: number | null;
  estimated_completion_date: string | null;
  pace_status: 'on_track' | 'ahead' | 'at_risk' | null;
  motivational_message: string;
  recent_contributions: GoalContribution[];
}

export interface GoalContribution {
  id: string;
  goal_id: string;
  /** Decimal → string */
  amount: string;
  note: string | null;
  created_at: string;
}

export interface GoalSummary {
  goals: SavingsGoal[];
  /** Decimal → string */
  total_saved: string;
  /** Decimal → string */
  total_target: string;
  active_count: number;
  completed_count: number;
}

export interface GoalCreate {
  name: string;
  target_amount: number;
  icon?: string;
  color?: string;
  monthly_contribution?: number | null;
  deadline?: string | null;
  priority?: number;
}

export interface GoalUpdate {
  name?: string;
  target_amount?: number;
  icon?: string;
  color?: string;
  monthly_contribution?: number | null;
  deadline?: string | null;
  priority?: number;
  status?: 'active' | 'completed' | 'cancelled';
}

export interface ContributionCreate {
  amount: number;
  note?: string | null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/goals.ts
git commit -m "feat(goals): add TypeScript types for goals domain"
```

---

## Task 11: Frontend API layer

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add imports and `goalsApi` at end of file**

Add these imports at the top of `api.ts` (after existing imports):

```typescript
import type {
  ContributionCreate,
  GoalContribution,
  GoalCreate,
  GoalSummary,
  GoalUpdate,
  SavingsGoal,
} from '@/types/goals';
```

Add `goalsApi` before the final `export { ApiError }` line:

```typescript
// ─── Goals endpoints ─────────────────────────────────────────────────────────

export const goalsApi = {
  list(status?: string): Promise<GoalSummary> {
    const qs = status && status !== 'all' ? `?status=${status}` : '';
    return api.get<GoalSummary>(`/goals/${qs}`);
  },

  get(id: string): Promise<SavingsGoal> {
    return api.get<SavingsGoal>(`/goals/${id}`);
  },

  create(data: GoalCreate): Promise<SavingsGoal> {
    return api.post<SavingsGoal>('/goals/', data);
  },

  update(id: string, data: GoalUpdate): Promise<SavingsGoal> {
    return api.patch<SavingsGoal>(`/goals/${id}`, data);
  },

  delete(id: string): Promise<void> {
    return api.delete<void>(`/goals/${id}`);
  },

  addContribution(id: string, data: ContributionCreate): Promise<SavingsGoal> {
    return api.post<SavingsGoal>(`/goals/${id}/contributions`, data);
  },

  getContributions(id: string): Promise<GoalContribution[]> {
    return api.get<GoalContribution[]>(`/goals/${id}/contributions`);
  },
};
```

- [ ] **Step 2: Verify lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/types/goals.ts
git commit -m "feat(goals): add goalsApi to frontend API layer"
```

---

## Task 12: Frontend hook

**Files:**
- Create: `frontend/src/hooks/useGoals.ts`

- [ ] **Step 1: Write `useGoals.ts`**

```typescript
// frontend/src/hooks/useGoals.ts
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { goalsApi } from '@/lib/api';
import type { ContributionCreate, GoalCreate, GoalUpdate } from '@/types/goals';

export function useGoals(status?: string) {
  return useQuery({
    queryKey: ['goals', status ?? 'all'],
    queryFn: () => goalsApi.list(status),
  });
}

export function useCreateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: GoalCreate) => goalsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) =>
      goalsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDeleteGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => goalsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useAddContribution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContributionCreate }) =>
      goalsApi.addContribution(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useGoals.ts
git commit -m "feat(goals): add useGoals hook with mutations"
```

---

## Task 13: GoalProgressBar + GoalEmptyState components

**Files:**
- Create: `frontend/src/components/features/goals/GoalProgressBar.tsx`
- Create: `frontend/src/components/features/goals/GoalEmptyState.tsx`

- [ ] **Step 1: Write `GoalProgressBar.tsx`**

```tsx
// frontend/src/components/features/goals/GoalProgressBar.tsx

interface GoalProgressBarProps {
  percentage: number;
  height?: string;
}

function barColor(pct: number): string {
  if (pct >= 100) return '#059669';
  if (pct >= 80) return '#10B981';
  if (pct >= 50) return '#6366F1';
  if (pct > 0) return '#3B82F6';
  return '#D1D5DB';
}

export function GoalProgressBar({ percentage, height = 'h-3' }: GoalProgressBarProps) {
  const clamped = Math.min(percentage, 100);
  const color = barColor(percentage);

  return (
    <div className="relative w-full">
      <div className={`relative w-full ${height} overflow-hidden rounded-full bg-[#f3f4f3]`}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${clamped}%`, backgroundColor: color }}
        />
        {/* Milestone markers at 25%, 50%, 75% */}
        {[25, 50, 75].map((mark) => (
          <div
            key={mark}
            className="absolute top-0 h-full w-px bg-white/60"
            style={{ left: `${mark}%` }}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `GoalEmptyState.tsx`**

```tsx
// frontend/src/components/features/goals/GoalEmptyState.tsx
import { Target } from 'lucide-react';

interface GoalEmptyStateProps {
  onCreateClick: () => void;
}

export function GoalEmptyState({ onCreateClick }: GoalEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-[#f3f4f3]">
        <Target size={40} className="text-[#9ca3af]" />
      </div>
      <h3 className="text-lg font-semibold text-[#303333]">
        Aún no tienes objetivos de ahorro
      </h3>
      <p className="mt-2 max-w-sm text-sm text-[#5d605f]">
        Crea tu primer objetivo y empieza a ahorrar para lo que más te importa
      </p>
      <button
        onClick={onCreateClick}
        className="mt-6 rounded-full bg-[#0060ad] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] transition-colors"
      >
        Crear mi primer objetivo
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/features/goals/
git commit -m "feat(goals): add GoalProgressBar and GoalEmptyState components"
```

---

## Task 14: DeleteGoalDialog + ContributionPanel components

**Files:**
- Create: `frontend/src/components/features/goals/DeleteGoalDialog.tsx`
- Create: `frontend/src/components/features/goals/ContributionPanel.tsx`

- [ ] **Step 1: Write `DeleteGoalDialog.tsx`**

```tsx
// frontend/src/components/features/goals/DeleteGoalDialog.tsx
import type { SavingsGoal } from '@/types/goals';

interface DeleteGoalDialogProps {
  goal: SavingsGoal;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

export function DeleteGoalDialog({
  goal,
  onConfirm,
  onCancel,
  isLoading,
}: DeleteGoalDialogProps) {
  const hasSavings = parseFloat(goal.current_amount) > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-[#303333]">Eliminar objetivo</h3>
        <p className="mt-2 text-sm text-[#5d605f]">
          {hasSavings
            ? `¿Eliminar "${goal.name}"? Tienes ${fmt.format(parseFloat(goal.current_amount))} acumulados en este objetivo. Esta acción no se puede deshacer.`
            : `¿Eliminar "${goal.name}"? Esta acción no se puede deshacer.`}
        </p>
        <div className="mt-5 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-[#edeeed] py-2.5 text-sm font-medium text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 rounded-xl bg-red-500 py-2.5 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Eliminando...' : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `ContributionPanel.tsx`**

```tsx
// frontend/src/components/features/goals/ContributionPanel.tsx
'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

interface ContributionPanelProps {
  goalId: string;
  onSubmit: (amount: number, note: string | null) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const QUICK_AMOUNTS = [10, 50, 100, 500];

export function ContributionPanel({
  onSubmit,
  onCancel,
  isLoading,
}: ContributionPanelProps) {
  const [isWithdraw, setIsWithdraw] = useState(false);
  const [customAmount, setCustomAmount] = useState('');
  const [note, setNote] = useState('');

  function handleQuick(amount: number) {
    const final = isWithdraw ? -amount : amount;
    onSubmit(final, note.trim() || null);
  }

  function handleCustomSubmit() {
    const val = parseFloat(customAmount.replace(',', '.'));
    if (!val || val <= 0) return;
    const final = isWithdraw ? -val : val;
    onSubmit(final, note.trim() || null);
  }

  return (
    <div
      className={`mt-3 rounded-xl border-2 p-4 ${isWithdraw ? 'border-orange-300 bg-orange-50' : 'border-[#e8f0f8] bg-[#f8fafc]'}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#303333]">
            {isWithdraw ? 'Retirar fondos' : 'Añadir fondos'}
          </span>
          <button
            onClick={() => setIsWithdraw((p) => !p)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              isWithdraw
                ? 'bg-orange-100 text-orange-700'
                : 'bg-[#e8f0f8] text-[#0060ad]'
            }`}
          >
            {isWithdraw ? 'Modo retirar' : 'Modo añadir'}
          </button>
        </div>
        <button onClick={onCancel} className="text-[#9ca3af] hover:text-[#5d605f]">
          <X size={16} />
        </button>
      </div>

      {/* Quick amount buttons */}
      <div className="mb-3 flex gap-2">
        {QUICK_AMOUNTS.map((amt) => (
          <button
            key={amt}
            onClick={() => handleQuick(amt)}
            disabled={isLoading}
            className={`flex-1 rounded-lg py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${
              isWithdraw
                ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                : 'bg-[#e8f0f8] text-[#0060ad] hover:bg-[#d0e4f5]'
            }`}
          >
            {isWithdraw ? '-' : '+'}{amt}€
          </button>
        ))}
      </div>

      {/* Custom amount + submit */}
      <div className="mb-2 flex gap-2">
        <input
          type="number"
          min="0"
          step="0.01"
          value={customAmount}
          onChange={(e) => setCustomAmount(e.target.value)}
          placeholder="Cantidad personalizada"
          className={`flex-1 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 ${
            isWithdraw
              ? 'border-orange-300 focus:ring-orange-200'
              : 'border-[#e0e7ef] focus:ring-[#3B82F6]/20'
          }`}
        />
        <button
          onClick={handleCustomSubmit}
          disabled={isLoading || !customAmount}
          className="rounded-lg bg-[#0060ad] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0052a3] disabled:opacity-50 transition-colors"
        >
          {isLoading ? '...' : isWithdraw ? 'Retirar' : 'Añadir'}
        </button>
      </div>

      {/* Note field */}
      <input
        type="text"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Nota opcional..."
        maxLength={200}
        className="w-full rounded-lg border border-[#e0e7ef] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
      />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/features/goals/DeleteGoalDialog.tsx frontend/src/components/features/goals/ContributionPanel.tsx
git commit -m "feat(goals): add DeleteGoalDialog and ContributionPanel components"
```

---

## Task 15: GoalCard + GoalSummaryCard components

**Files:**
- Create: `frontend/src/components/features/goals/GoalCard.tsx`
- Create: `frontend/src/components/features/goals/GoalSummaryCard.tsx`

- [ ] **Step 1: Write `GoalCard.tsx`**

```tsx
// frontend/src/components/features/goals/GoalCard.tsx
'use client';

import { useState } from 'react';
import {
  PiggyBank, Wallet, Home, Car, Plane, Heart, Star, Shield,
  GraduationCap, Laptop, Gift, Music, Camera, Book, Coffee,
  Sun, Umbrella, Anchor, Target, Trophy, Plus, Pencil, Trash2,
  type LucideIcon,
} from 'lucide-react';
import { GoalProgressBar } from './GoalProgressBar';
import { ContributionPanel } from './ContributionPanel';
import type { SavingsGoal } from '@/types/goals';

const GOAL_ICONS: Record<string, LucideIcon> = {
  'piggy-bank': PiggyBank, wallet: Wallet, home: Home, car: Car, plane: Plane,
  heart: Heart, star: Star, shield: Shield, 'graduation-cap': GraduationCap,
  laptop: Laptop, gift: Gift, music: Music, camera: Camera, book: Book,
  coffee: Coffee, sun: Sun, umbrella: Umbrella, anchor: Anchor, target: Target,
  trophy: Trophy,
};

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

const PACE_LABELS: Record<string, { label: string; cls: string }> = {
  ahead: { label: 'Adelantado', cls: 'bg-green-100 text-green-700' },
  on_track: { label: 'En ritmo', cls: 'bg-blue-100 text-blue-700' },
  at_risk: { label: 'En riesgo', cls: 'bg-orange-100 text-orange-700' },
};

interface GoalCardProps {
  goal: SavingsGoal;
  onContribute: (id: string, amount: number, note: string | null) => void;
  onEdit: (goal: SavingsGoal) => void;
  onDelete: (goal: SavingsGoal) => void;
  isContributing?: boolean;
}

export function GoalCard({ goal, onContribute, onEdit, onDelete, isContributing }: GoalCardProps) {
  const [showPanel, setShowPanel] = useState(false);
  const Icon = GOAL_ICONS[goal.icon] ?? PiggyBank;
  const pace = goal.pace_status ? PACE_LABELS[goal.pace_status] : null;
  const current = parseFloat(goal.current_amount);
  const target = parseFloat(goal.target_amount);
  const daysLeft = goal.days_remaining;

  let deadlineText: { text: string; cls: string } | null = null;
  if (daysLeft !== null) {
    if (daysLeft < 0) {
      deadlineText = { text: `Vencido hace ${Math.abs(daysLeft)} días`, cls: 'text-red-600' };
    } else if (daysLeft <= 7) {
      deadlineText = { text: `Quedan ${daysLeft} días`, cls: 'text-orange-500' };
    } else {
      deadlineText = { text: `Quedan ${daysLeft} días`, cls: 'text-[#5d605f]' };
    }
  }

  return (
    <div
      className="rounded-2xl bg-white shadow-card overflow-hidden"
      style={{ borderLeft: `4px solid ${goal.color}` }}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Icon size={20} style={{ color: goal.color }} className="shrink-0" />
            <span className="truncate font-semibold text-[#303333]">{goal.name}</span>
            {pace && (
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${pace.cls}`}>
                {pace.label}
              </span>
            )}
          </div>
          <div className="flex shrink-0 gap-1">
            <button
              onClick={() => onEdit(goal)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[#9ca3af] hover:bg-[#f3f4f3] hover:text-[#5d605f] transition-colors"
            >
              <Pencil size={13} />
            </button>
            <button
              onClick={() => onDelete(goal)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[#9ca3af] hover:bg-red-50 hover:text-red-500 transition-colors"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs text-[#5d605f]">
              {fmt.format(current)} de {fmt.format(target)}
            </span>
            <span className="text-xs font-semibold" style={{ color: goal.color }}>
              {goal.percentage.toFixed(0)}%
            </span>
          </div>
          <GoalProgressBar percentage={goal.percentage} />
        </div>

        {/* Motivational message */}
        <p className="mt-2 text-xs text-[#9ca3af]">{goal.motivational_message}</p>

        {/* Deadline / estimated */}
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {deadlineText && (
            <span className={deadlineText.cls}>{deadlineText.text}</span>
          )}
          {goal.estimated_completion_date && (
            <span className="text-[#9ca3af]">
              Estimado:{' '}
              {new Date(goal.estimated_completion_date).toLocaleDateString('es-ES', {
                day: 'numeric', month: 'short', year: 'numeric',
              })}
            </span>
          )}
        </div>

        {/* Contribution panel or button */}
        {goal.status === 'active' && (
          <>
            {showPanel ? (
              <ContributionPanel
                goalId={goal.id}
                onSubmit={(amount, note) => {
                  onContribute(goal.id, amount, note);
                  setShowPanel(false);
                }}
                onCancel={() => setShowPanel(false)}
                isLoading={isContributing}
              />
            ) : (
              <button
                onClick={() => setShowPanel(true)}
                className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-[#cce8d7] py-2 text-sm font-medium text-[#0060ad] hover:border-[#0060ad] hover:bg-[#f0f7ff] transition-colors"
              >
                <Plus size={14} />
                Añadir
              </button>
            )}
          </>
        )}

        {goal.status === 'completed' && (
          <div className="mt-3 flex items-center justify-center gap-1.5 rounded-xl bg-green-50 py-2 text-sm font-medium text-green-700">
            ¡Objetivo cumplido! 🎉
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `GoalSummaryCard.tsx`**

```tsx
// frontend/src/components/features/goals/GoalSummaryCard.tsx
import { GoalProgressBar } from './GoalProgressBar';
import type { GoalSummary } from '@/types/goals';

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

interface GoalSummaryCardProps {
  summary: GoalSummary;
  completedExpanded: boolean;
  onToggleCompleted: () => void;
}

export function GoalSummaryCard({
  summary,
  completedExpanded,
  onToggleCompleted,
}: GoalSummaryCardProps) {
  const saved = parseFloat(summary.total_saved);
  const target = parseFloat(summary.total_target);
  const globalPct = target > 0 ? (saved / target) * 100 : 0;

  return (
    <div className="rounded-2xl bg-white p-5 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-[#5d605f]">
            Total ahorrado
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#303333]">{fmt.format(saved)}</span>
            <span className="text-sm text-[#9ca3af]">de {fmt.format(target)}</span>
          </div>
          <div className="mt-3">
            <GoalProgressBar percentage={globalPct} height="h-2.5" />
          </div>
        </div>
        <div className="flex gap-4 text-center sm:flex-col sm:items-end">
          <div>
            <p className="text-xl font-bold text-[#0060ad]">{summary.active_count}</p>
            <p className="text-xs text-[#5d605f]">activos</p>
          </div>
          {summary.completed_count > 0 && (
            <button
              onClick={onToggleCompleted}
              className="text-right hover:underline"
            >
              <p className="text-xl font-bold text-green-600">{summary.completed_count}</p>
              <p className="text-xs text-[#5d605f]">
                completados {completedExpanded ? '▲' : '▼'}
              </p>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/features/goals/GoalCard.tsx frontend/src/components/features/goals/GoalSummaryCard.tsx
git commit -m "feat(goals): add GoalCard and GoalSummaryCard components"
```

---

## Task 16: NewGoalModal + EditGoalModal components

**Files:**
- Create: `frontend/src/components/features/goals/NewGoalModal.tsx`
- Create: `frontend/src/components/features/goals/EditGoalModal.tsx`

- [ ] **Step 1: Write `NewGoalModal.tsx`**

```tsx
// frontend/src/components/features/goals/NewGoalModal.tsx
'use client';

import { useState } from 'react';
import {
  PiggyBank, Wallet, Home, Car, Plane, Heart, Star, Shield,
  GraduationCap, Laptop, Gift, Music, Camera, Book, Coffee,
  Sun, Umbrella, Anchor, Target, Trophy, PlusCircle, X,
  type LucideIcon,
} from 'lucide-react';
import type { GoalCreate } from '@/types/goals';

const ICONS: { name: string; Icon: LucideIcon }[] = [
  { name: 'piggy-bank', Icon: PiggyBank }, { name: 'wallet', Icon: Wallet },
  { name: 'home', Icon: Home }, { name: 'car', Icon: Car },
  { name: 'plane', Icon: Plane }, { name: 'heart', Icon: Heart },
  { name: 'star', Icon: Star }, { name: 'shield', Icon: Shield },
  { name: 'graduation-cap', Icon: GraduationCap }, { name: 'laptop', Icon: Laptop },
  { name: 'gift', Icon: Gift }, { name: 'music', Icon: Music },
  { name: 'camera', Icon: Camera }, { name: 'book', Icon: Book },
  { name: 'coffee', Icon: Coffee }, { name: 'sun', Icon: Sun },
  { name: 'umbrella', Icon: Umbrella }, { name: 'anchor', Icon: Anchor },
  { name: 'target', Icon: Target }, { name: 'trophy', Icon: Trophy },
];

const COLORS = [
  '#EF4444', '#F59E0B', '#F97316', '#10B981', '#3B82F6',
  '#6366F1', '#8B5CF6', '#EC4899', '#14B8A6', '#6B7280',
  '#84CC16', '#06B6D4',
];

const PRESETS = [
  { name: 'Fondo de emergencia', icon: 'shield', color: '#EF4444' },
  { name: 'Vacaciones', icon: 'plane', color: '#F59E0B' },
  { name: 'Entrada de piso', icon: 'home', color: '#8B5CF6' },
  { name: 'Coche nuevo', icon: 'car', color: '#3B82F6' },
  { name: 'Tecnología', icon: 'laptop', color: '#6366F1' },
  { name: 'Educación', icon: 'graduation-cap', color: '#10B981' },
  { name: 'Boda', icon: 'heart', color: '#EC4899' },
  { name: 'Otro...', icon: 'plus-circle', color: '#6B7280' },
];

interface NewGoalModalProps {
  onSubmit: (data: GoalCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function NewGoalModal({ onSubmit, onCancel, isLoading }: NewGoalModalProps) {
  const [step, setStep] = useState<'preset' | 'form'>('preset');
  const [name, setName] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [monthlyContribution, setMonthlyContribution] = useState('');
  const [deadline, setDeadline] = useState('');
  const [icon, setIcon] = useState('piggy-bank');
  const [color, setColor] = useState('#3B82F6');

  function handlePreset(preset: (typeof PRESETS)[0]) {
    if (preset.name !== 'Otro...') {
      setName(preset.name);
      setIcon(preset.icon);
      setColor(preset.color);
    }
    setStep('form');
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const target = parseFloat(targetAmount.replace(',', '.'));
    if (!name.trim() || !target || target <= 0) return;
    onSubmit({
      name: name.trim(),
      target_amount: target,
      icon,
      color,
      monthly_contribution: monthlyContribution
        ? parseFloat(monthlyContribution.replace(',', '.'))
        : null,
      deadline: deadline || null,
      priority: 0,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[#f3f4f3] px-5 py-4">
          <h2 className="font-semibold text-[#303333]">
            {step === 'preset' ? 'Nuevo objetivo' : 'Configurar objetivo'}
          </h2>
          <button onClick={onCancel} className="text-[#9ca3af] hover:text-[#5d605f]">
            <X size={20} />
          </button>
        </div>

        {step === 'preset' ? (
          <div className="p-5">
            <p className="mb-4 text-sm text-[#5d605f]">¿Para qué quieres ahorrar?</p>
            <div className="grid grid-cols-4 gap-2">
              {PRESETS.map((preset) => {
                const found = ICONS.find((i) => i.name === preset.icon);
                const Icon = found ? found.Icon : PlusCircle;
                return (
                  <button
                    key={preset.name}
                    onClick={() => handlePreset(preset)}
                    className="flex flex-col items-center gap-1.5 rounded-xl p-3 hover:bg-[#f3f4f3] transition-colors"
                  >
                    <Icon size={24} style={{ color: preset.color }} />
                    <span className="text-center text-xs text-[#5d605f] leading-tight">
                      {preset.name}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto p-5 space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-[#5d605f]">
                Nombre del objetivo *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                required
                placeholder="Ej: Vacaciones en Japón"
                className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[#5d605f]">
                Importe objetivo (€) *
              </label>
              <input
                type="number"
                value={targetAmount}
                onChange={(e) => setTargetAmount(e.target.value)}
                min="0.01"
                step="0.01"
                required
                placeholder="Ej: 2000"
                className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[#5d605f]">
                Aportación mensual (€) — opcional
              </label>
              <input
                type="number"
                value={monthlyContribution}
                onChange={(e) => setMonthlyContribution(e.target.value)}
                min="0.01"
                step="0.01"
                placeholder="Ej: 100 €/mes"
                className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[#5d605f]">
                Fecha límite — opcional
              </label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
              />
            </div>
            <div>
              <label className="mb-2 block text-xs font-medium text-[#5d605f]">Icono</label>
              <div className="grid grid-cols-10 gap-1">
                {ICONS.map(({ name: n, Icon }) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setIcon(n)}
                    className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                      icon === n ? 'bg-[#e8f0f8]' : 'hover:bg-[#f3f4f3]'
                    }`}
                  >
                    <Icon size={18} style={{ color: icon === n ? color : '#9ca3af' }} />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-2 block text-xs font-medium text-[#5d605f]">Color</label>
              <div className="flex flex-wrap gap-2">
                {COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={`h-7 w-7 rounded-full transition-transform ${
                      color === c ? 'scale-125 ring-2 ring-offset-1 ring-[#303333]' : ''
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep('preset')}
                className="flex-1 rounded-xl border border-[#edeeed] py-2.5 text-sm font-medium text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
              >
                Atrás
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 rounded-xl bg-[#0060ad] py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] disabled:opacity-50 transition-colors"
              >
                {isLoading ? 'Creando...' : 'Crear objetivo'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `EditGoalModal.tsx`**

```tsx
// frontend/src/components/features/goals/EditGoalModal.tsx
'use client';

import { useState } from 'react';
import {
  PiggyBank, Wallet, Home, Car, Plane, Heart, Star, Shield,
  GraduationCap, Laptop, Gift, Music, Camera, Book, Coffee,
  Sun, Umbrella, Anchor, Target, Trophy, X, type LucideIcon,
} from 'lucide-react';
import type { GoalUpdate, SavingsGoal } from '@/types/goals';

const ICONS: { name: string; Icon: LucideIcon }[] = [
  { name: 'piggy-bank', Icon: PiggyBank }, { name: 'wallet', Icon: Wallet },
  { name: 'home', Icon: Home }, { name: 'car', Icon: Car },
  { name: 'plane', Icon: Plane }, { name: 'heart', Icon: Heart },
  { name: 'star', Icon: Star }, { name: 'shield', Icon: Shield },
  { name: 'graduation-cap', Icon: GraduationCap }, { name: 'laptop', Icon: Laptop },
  { name: 'gift', Icon: Gift }, { name: 'music', Icon: Music },
  { name: 'camera', Icon: Camera }, { name: 'book', Icon: Book },
  { name: 'coffee', Icon: Coffee }, { name: 'sun', Icon: Sun },
  { name: 'umbrella', Icon: Umbrella }, { name: 'anchor', Icon: Anchor },
  { name: 'target', Icon: Target }, { name: 'trophy', Icon: Trophy },
];

const COLORS = [
  '#EF4444', '#F59E0B', '#F97316', '#10B981', '#3B82F6',
  '#6366F1', '#8B5CF6', '#EC4899', '#14B8A6', '#6B7280',
  '#84CC16', '#06B6D4',
];

interface EditGoalModalProps {
  goal: SavingsGoal;
  onSubmit: (id: string, data: GoalUpdate) => void;
  onMarkCompleted: (id: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function EditGoalModal({
  goal,
  onSubmit,
  onMarkCompleted,
  onCancel,
  isLoading,
}: EditGoalModalProps) {
  const [name, setName] = useState(goal.name);
  const [targetAmount, setTargetAmount] = useState(goal.target_amount);
  const [monthlyContribution, setMonthlyContribution] = useState(
    goal.monthly_contribution ?? '',
  );
  const [deadline, setDeadline] = useState(goal.deadline ?? '');
  const [icon, setIcon] = useState(goal.icon);
  const [color, setColor] = useState(goal.color);
  const [confirmComplete, setConfirmComplete] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const target = parseFloat(String(targetAmount).replace(',', '.'));
    if (!name.trim() || !target || target <= 0) return;
    onSubmit(goal.id, {
      name: name.trim(),
      target_amount: target,
      icon,
      color,
      monthly_contribution: monthlyContribution
        ? parseFloat(String(monthlyContribution).replace(',', '.'))
        : null,
      deadline: deadline || null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[#f3f4f3] px-5 py-4">
          <h2 className="font-semibold text-[#303333]">Editar objetivo</h2>
          <button onClick={onCancel} className="text-[#9ca3af] hover:text-[#5d605f]">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto p-5 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">Nombre *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">
              Importe objetivo (€) *
            </label>
            <input
              type="number"
              value={targetAmount}
              onChange={(e) => setTargetAmount(e.target.value)}
              min="0.01"
              step="0.01"
              required
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">
              Aportación mensual (€) — opcional
            </label>
            <input
              type="number"
              value={monthlyContribution}
              onChange={(e) => setMonthlyContribution(e.target.value)}
              min="0.01"
              step="0.01"
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#5d605f]">
              Fecha límite — opcional
            </label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full rounded-xl border border-[#e0e7ef] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-medium text-[#5d605f]">Icono</label>
            <div className="grid grid-cols-10 gap-1">
              {ICONS.map(({ name: n, Icon }) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setIcon(n)}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                    icon === n ? 'bg-[#e8f0f8]' : 'hover:bg-[#f3f4f3]'
                  }`}
                >
                  <Icon size={18} style={{ color: icon === n ? color : '#9ca3af' }} />
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-2 block text-xs font-medium text-[#5d605f]">Color</label>
            <div className="flex flex-wrap gap-2">
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded-full transition-transform ${
                    color === c ? 'scale-125 ring-2 ring-offset-1 ring-[#303333]' : ''
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {goal.status === 'active' && (
            <div className="rounded-xl border border-green-200 bg-green-50 p-3">
              {confirmComplete ? (
                <div>
                  <p className="text-sm text-green-800">
                    ¿Marcar &quot;{goal.name}&quot; como completado? El objetivo quedará registrado
                    en tu historial.
                  </p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => setConfirmComplete(false)}
                      className="flex-1 rounded-lg border border-green-300 py-1.5 text-xs font-medium text-green-700"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      onClick={() => onMarkCompleted(goal.id)}
                      className="flex-1 rounded-lg bg-green-600 py-1.5 text-xs font-semibold text-white"
                    >
                      Confirmar
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmComplete(true)}
                  className="w-full text-sm font-medium text-green-700 hover:underline"
                >
                  Marcar como completado ✓
                </button>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-xl border border-[#edeeed] py-2.5 text-sm font-medium text-[#5d605f] hover:bg-[#f3f4f3] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 rounded-xl bg-[#0060ad] py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Guardando...' : 'Guardar cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/features/goals/NewGoalModal.tsx frontend/src/components/features/goals/EditGoalModal.tsx
git commit -m "feat(goals): add NewGoalModal and EditGoalModal components"
```

---

## Task 17: Goals page + loading skeleton

**Files:**
- Create: `frontend/src/app/(dashboard)/goals/page.tsx`
- Create: `frontend/src/app/(dashboard)/goals/loading.tsx`

- [ ] **Step 1: Write `loading.tsx`**

```tsx
// frontend/src/app/(dashboard)/goals/loading.tsx
export default function GoalsLoading() {
  return (
    <div className="space-y-6 pb-32">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="h-8 w-52 animate-pulse rounded-full bg-[#f3f4f3]" />
        <div className="h-11 w-44 animate-pulse rounded-full bg-[#f3f4f3]" />
      </div>

      {/* Summary card skeleton */}
      <div className="animate-pulse rounded-2xl bg-white p-5 shadow-card">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-3 w-24 rounded-full bg-[#edeeed]" />
            <div className="h-9 w-40 rounded-full bg-[#f3f4f3]" />
            <div className="mt-3 h-2.5 w-72 rounded-full bg-[#edeeed]" />
          </div>
          <div className="space-y-2 text-right">
            <div className="h-7 w-10 rounded-full bg-[#edeeed]" />
            <div className="h-3 w-12 rounded-full bg-[#edeeed]" />
          </div>
        </div>
      </div>

      {/* Goal cards grid skeleton */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <div
            key={i}
            className="animate-pulse overflow-hidden rounded-2xl bg-white shadow-card"
            style={{ borderLeft: '4px solid #f3f4f3' }}
          >
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-5 w-5 rounded-full bg-[#edeeed]" />
                <div className="h-4 w-32 rounded-full bg-[#f3f4f3]" />
              </div>
              <div className="h-3 w-full rounded-full bg-[#edeeed]" />
              <div className="space-y-1">
                <div className="h-3 w-2/3 rounded-full bg-[#edeeed]" />
                <div className="h-2.5 rounded-full bg-[#f3f4f3]" />
              </div>
              <div className="h-9 w-full rounded-xl bg-[#f3f4f3]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `page.tsx`**

```tsx
// frontend/src/app/(dashboard)/goals/page.tsx
'use client';

import { useState } from 'react';
import { Plus, ChevronDown, ChevronUp } from 'lucide-react';
import { useGoals, useCreateGoal, useUpdateGoal, useDeleteGoal, useAddContribution } from '@/hooks/useGoals';
import { GoalSummaryCard } from '@/components/features/goals/GoalSummaryCard';
import { GoalCard } from '@/components/features/goals/GoalCard';
import { GoalEmptyState } from '@/components/features/goals/GoalEmptyState';
import { NewGoalModal } from '@/components/features/goals/NewGoalModal';
import { EditGoalModal } from '@/components/features/goals/EditGoalModal';
import { DeleteGoalDialog } from '@/components/features/goals/DeleteGoalDialog';
import type { GoalCreate, GoalUpdate, SavingsGoal } from '@/types/goals';

export default function GoalsPage() {
  const { data: summary, isLoading, isError } = useGoals();
  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const deleteGoal = useDeleteGoal();
  const addContribution = useAddContribution();

  const [showNewModal, setShowNewModal] = useState(false);
  const [editingGoal, setEditingGoal] = useState<SavingsGoal | null>(null);
  const [deletingGoal, setDeletingGoal] = useState<SavingsGoal | null>(null);
  const [completedExpanded, setCompletedExpanded] = useState(false);

  if (isLoading) return null;

  if (isError) {
    return (
      <div className="py-20 text-center text-sm text-red-500">
        Error al cargar los objetivos. Inténtalo de nuevo.
      </div>
    );
  }

  const activeGoals = summary?.goals.filter((g) => g.status === 'active') ?? [];
  const completedGoals = summary?.goals.filter((g) => g.status !== 'active') ?? [];
  const hasGoals = (summary?.goals.length ?? 0) > 0;

  function handleCreate(data: GoalCreate) {
    createGoal.mutate(data, { onSuccess: () => setShowNewModal(false) });
  }

  function handleUpdate(id: string, data: GoalUpdate) {
    updateGoal.mutate({ id, data }, { onSuccess: () => setEditingGoal(null) });
  }

  function handleMarkCompleted(id: string) {
    updateGoal.mutate(
      { id, data: { status: 'completed' } },
      { onSuccess: () => setEditingGoal(null) },
    );
  }

  function handleDelete() {
    if (!deletingGoal) return;
    deleteGoal.mutate(deletingGoal.id, { onSuccess: () => setDeletingGoal(null) });
  }

  function handleContribute(id: string, amount: number, note: string | null) {
    addContribution.mutate({ id, data: { amount, note } });
  }

  return (
    <div className="space-y-6 pb-32">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#303333]">Objetivos de ahorro</h1>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 rounded-full bg-[#0060ad] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] transition-colors"
        >
          <Plus size={16} />
          Nuevo objetivo
        </button>
      </div>

      {!hasGoals ? (
        <GoalEmptyState onCreateClick={() => setShowNewModal(true)} />
      ) : (
        <>
          {/* Summary card */}
          {summary && (
            <GoalSummaryCard
              summary={summary}
              completedExpanded={completedExpanded}
              onToggleCompleted={() => setCompletedExpanded((p) => !p)}
            />
          )}

          {/* Active goals */}
          {activeGoals.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#9ca3af]">
                Objetivos activos
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {activeGoals.map((goal) => (
                  <GoalCard
                    key={goal.id}
                    goal={goal}
                    onContribute={handleContribute}
                    onEdit={setEditingGoal}
                    onDelete={setDeletingGoal}
                    isContributing={addContribution.isPending}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Completed / cancelled goals (collapsible) */}
          {completedGoals.length > 0 && (
            <section>
              <button
                onClick={() => setCompletedExpanded((p) => !p)}
                className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[#9ca3af] hover:text-[#5d605f] transition-colors"
              >
                Completados ({completedGoals.length})
                {completedExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {completedExpanded && (
                <div className="grid grid-cols-1 gap-4 opacity-75 md:grid-cols-2 lg:grid-cols-3">
                  {completedGoals.map((goal) => (
                    <GoalCard
                      key={goal.id}
                      goal={goal}
                      onContribute={handleContribute}
                      onEdit={setEditingGoal}
                      onDelete={setDeletingGoal}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}

      {/* Modals */}
      {showNewModal && (
        <NewGoalModal
          onSubmit={handleCreate}
          onCancel={() => setShowNewModal(false)}
          isLoading={createGoal.isPending}
        />
      )}
      {editingGoal && (
        <EditGoalModal
          goal={editingGoal}
          onSubmit={handleUpdate}
          onMarkCompleted={handleMarkCompleted}
          onCancel={() => setEditingGoal(null)}
          isLoading={updateGoal.isPending}
        />
      )}
      {deletingGoal && (
        <DeleteGoalDialog
          goal={deletingGoal}
          onConfirm={handleDelete}
          onCancel={() => setDeletingGoal(null)}
          isLoading={deleteGoal.isPending}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify build compiles**

```bash
cd frontend && npm run build 2>&1 | tail -20
```
Expected: no TypeScript errors in goals pages/components.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(dashboard\)/goals/
git commit -m "feat(goals): add goals page with grid layout, modals, and loading skeleton"
```

---

## Task 18: Sidebar link

**Files:**
- Modify: `frontend/src/app/(dashboard)/layout.tsx`

- [ ] **Step 1: Add "Objetivos" link**

In `layout.tsx`, locate the `navLinks` array. After `{ href: '/budgets', label: 'Presupuestos' }` (line 33), add:

```typescript
{ href: '/goals', label: 'Objetivos' },
```

The array should look like:

```typescript
  { href: '/budgets', label: 'Presupuestos' },
  { href: '/goals', label: 'Objetivos' },
  { href: '/reports', label: 'Informes' },
```

- [ ] **Step 2: Verify lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(dashboard\)/layout.tsx
git commit -m "feat(goals): add Objetivos link to navigation sidebar"
```

---

## Task 19: Dashboard backend integration

**Files:**
- Modify: `Backend/app/dashboard/schemas.py`
- Modify: `Backend/app/dashboard/service.py`

- [ ] **Step 1: Update `schemas.py`**

Add import and field to `DashboardResponse`:

```python
# Add import at top (after existing imports):
from app.goals.schemas import GoalResponse

# Add field to DashboardResponse:
class DashboardResponse(BaseModel):
    total_balance: Decimal
    currency: str
    accounts: list[AccountSummary]
    recent_transactions: list[TransactionResponse]
    last_synced_at: datetime | None
    upcoming_charges: list[RecurringChargeResponse] = []
    active_goal: GoalResponse | None = None
```

- [ ] **Step 2: Update `service.py`**

Add `_fetch_active_goal` method and include it in `asyncio.gather`:

```python
# Add import at top (after existing imports):
from app.goals.service import get_active_goal_for_dashboard

# Add method to DashboardService (before get_dashboard):
async def _fetch_active_goal(self, user_id: uuid.UUID) -> GoalResponse | None:
    from app.goals.schemas import GoalResponse as _GoalResponse  # avoid circular at module level
    try:
        return await get_active_goal_for_dashboard(self._db, user_id)
    except Exception:
        return None
```

Replace `asyncio.gather` call inside `_fetch` in `get_dashboard` with 4 items:

```python
async def _fetch() -> dict[str, object]:
    (
        (accounts, total_balance, last_synced_at),
        recent_transactions,
        upcoming_charges,
        active_goal,
    ) = await asyncio.gather(
        self._fetch_accounts(user_id, user_currency),
        self._fetch_recent_transactions(user_id),
        get_upcoming_charges(self._db, user_id),
        self._fetch_active_goal(user_id),
    )

    response = DashboardResponse(
        total_balance=total_balance,
        currency=user_currency,
        accounts=accounts,
        recent_transactions=recent_transactions,
        last_synced_at=last_synced_at,
        upcoming_charges=upcoming_charges,
        active_goal=active_goal,
    )
    return response.model_dump(mode="json")
```

- [ ] **Step 3: Verify backend imports**

```bash
cd Backend && python -c "from app.dashboard.service import DashboardService; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add Backend/app/dashboard/schemas.py Backend/app/dashboard/service.py
git commit -m "feat(goals): add active_goal to DashboardResponse and service"
```

---

## Task 20: Dashboard frontend integration

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/app/(dashboard)/dashboard/page.tsx`

- [ ] **Step 1: Update `types/index.ts`**

Add import and field to `Dashboard` interface. First add import at the top:

```typescript
import type { SavingsGoal } from '@/types/goals';
```

Then find the `Dashboard` interface and add `active_goal`:

```typescript
export interface Dashboard {
  total_balance: string;
  currency: string;
  accounts: AccountSummary[];
  recent_transactions: Transaction[];
  last_synced_at: string | null;
  upcoming_charges: RecurringCharge[];
  active_goal: SavingsGoal | null;
}
```

- [ ] **Step 2: Add goal widget to dashboard page**

In `frontend/src/app/(dashboard)/dashboard/page.tsx`, add the import:

```typescript
import Link from 'next/link';
import { GoalProgressBar } from '@/components/features/goals/GoalProgressBar';
```

Then after the recurring charges section (look for the section that renders `upcoming_charges`), add a goal widget conditionally:

```tsx
{/* Active goal widget */}
{data?.active_goal && (
  <section>
    <h2 className="mb-3 text-sm font-semibold text-[#5d605f]">Objetivo activo</h2>
    <Link
      href="/goals"
      className="block rounded-2xl bg-white p-4 shadow-card hover:shadow-md transition-shadow"
      style={{ borderLeft: `4px solid ${data.active_goal.color}` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-[#303333]">{data.active_goal.name}</span>
        <span className="text-sm font-semibold text-[#0060ad]">
          {data.active_goal.percentage.toFixed(0)}%
        </span>
      </div>
      <div className="mt-2">
        <GoalProgressBar percentage={data.active_goal.percentage} height="h-2" />
      </div>
      <div className="mt-1.5 text-xs text-[#9ca3af]">
        {new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(
          parseFloat(data.active_goal.current_amount),
        )}{' '}
        /{' '}
        {new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(
          parseFloat(data.active_goal.target_amount),
        )}
      </div>
    </Link>
  </section>
)}
```

- [ ] **Step 3: Run lint + build**

```bash
cd frontend && npm run lint && npm run build 2>&1 | tail -20
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/app/\(dashboard\)/dashboard/page.tsx
git commit -m "feat(goals): add active goal widget to dashboard page"
```

---

## Task 21: Documentation updates

**Files:**
- Modify: `PROJECT_STATUS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `PROJECT_STATUS.md`**

1. In the implementation status table (section 1), change the Goals row from `Not implemented` to `Complete`.
2. Remove the Goals row from the "Not Implemented" section.
3. Add to the "Route Map" table: `| /goals | app/(dashboard)/goals/page.tsx | Client | Savings goals grid with progress tracking |`
4. Add to "Feature Components": GoalSummaryCard, GoalCard, GoalProgressBar, ContributionPanel, NewGoalModal, EditGoalModal, DeleteGoalDialog, GoalEmptyState.
5. Add to "Hooks": `| useGoals | ['goals'] | GET /goals/, mutations | Summary + CRUD mutations + addContribution |`
6. Add to "Types": `| goals.ts | SavingsGoal, GoalContribution, GoalSummary, GoalCreate, GoalUpdate, ContributionCreate |`
7. Add to "All Registered Routers": `| goals | /goals | ["goals"] |`
8. Update metrics: +2 DB tables, +7 endpoints, +1 page, +8 components, +1 hook, +1 type file.

- [ ] **Step 2: Update `CLAUDE.md`**

In the Project Structure tree under `app/`, add the goals domain after `budgets/`:

```
│   │   ├── goals/               # Savings goals domain
│   │   │   ├── router.py        # CRUD endpoints for goals + contributions
│   │   │   ├── schemas.py       # GoalCreate, GoalUpdate, GoalResponse, etc.
│   │   │   ├── models.py        # SavingsGoal, GoalContribution SQLAlchemy models
│   │   │   ├── service.py       # Goal management + computed fields
│   │   │   └── __init__.py
```

In the App Router tree under `(dashboard)/`, add:
```
│   │   │       ├── goals/page.tsx
```

In the "NOT implemented yet" line, remove `goals`.

- [ ] **Step 3: Commit**

```bash
git add PROJECT_STATUS.md CLAUDE.md
git commit -m "docs: update PROJECT_STATUS and CLAUDE.md to reflect goals feature completion"
```

---

## Quality Checklist (run before declaring done)

```bash
# Backend
cd Backend
ruff check app/goals/ --fix && ruff format app/goals/
pytest tests/goals/ -v

# Frontend
cd ../frontend
npm run lint
npm run build
```

All must pass with no errors.
