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
    return await list_goals(
        db=db,
        user_id=current_user.id,
        user_currency=current_user.currency,
        status_filter=status,
    )


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


@router.delete(
    "/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
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
        db=db,
        goal_id=goal_id,
        user_id=current_user.id,
        user_currency=current_user.currency,
        data=data,
    )


@router.get("/{goal_id}/contributions", response_model=list[ContributionResponse])
async def list_contributions_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    goal_id: uuid.UUID,
) -> list[ContributionResponse]:
    return await list_contributions(db=db, goal_id=goal_id, user_id=current_user.id)
