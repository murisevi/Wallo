"""Budgets API router — monthly summary, CRUD, and category listing."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.budgets.schemas import (
    BudgetCreate,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetUpdate,
    CategoryResponse,
    CopySourceResponse,
)
from app.budgets.service import (
    copy_previous_month,
    create_budget,
    delete_budget,
    find_copy_source,
    get_categories,
    get_monthly_summary,
    update_budget,
)
from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: CurrentUser,
    db: DbSession,
) -> list[CategoryResponse]:
    """List all categories available to the authenticated user (system + custom)."""
    return await get_categories(db=db, user_id=current_user.id)


@router.get("/", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    current_user: CurrentUser,
    db: DbSession,
    month: Annotated[int, Query(ge=1, le=12, description="Month (1-12)")] = 1,
    year: Annotated[int, Query(ge=2000, description="Year")] = 2024,
) -> BudgetSummaryResponse:
    """Monthly budget summary with per-category spending."""
    return await get_monthly_summary(
        db=db,
        user_id=current_user.id,
        month=month,
        year=year,
    )


@router.get("/copy-source", response_model=CopySourceResponse)
async def get_copy_source(
    current_user: CurrentUser,
    db: DbSession,
    month: Annotated[int, Query(ge=1, le=12, description="Target month (1-12)")] = 1,
    year: Annotated[int, Query(ge=2000, description="Target year")] = 2024,
) -> CopySourceResponse:
    """Return the most recent previous month with budgets (up to 6 months back).

    Raises 404 if no previous month with budgets is found.
    """
    source = await find_copy_source(
        db=db, user_id=current_user.id, target_month=month, target_year=year
    )
    if source is None:
        raise HTTPException(status_code=404, detail="No previous budgets found")
    return source


@router.post("/copy-previous", response_model=BudgetSummaryResponse)
async def copy_previous_month_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    month: Annotated[int, Query(ge=1, le=12, description="Target month (1-12)")] = 1,
    year: Annotated[int, Query(ge=2000, description="Target year")] = 2024,
) -> BudgetSummaryResponse:
    """Copy budgets from the previous month into the given month.

    Silently skips categories that already have a budget for the target month.
    """
    return await copy_previous_month(
        db=db,
        user_id=current_user.id,
        month=month,
        year=year,
    )


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    data: BudgetCreate,
) -> BudgetResponse:
    """Create a new budget for a category/month/year."""
    return await create_budget(db=db, user_id=current_user.id, data=data)


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    budget_id: uuid.UUID,
    data: BudgetUpdate,
) -> BudgetResponse:
    """Update the spending limit of an existing budget."""
    return await update_budget(
        db=db, user_id=current_user.id, budget_id=budget_id, data=data
    )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_budget_endpoint(
    current_user: CurrentUser,
    db: DbSession,
    budget_id: uuid.UUID,
) -> None:
    """Delete a budget."""
    await delete_budget(db=db, user_id=current_user.id, budget_id=budget_id)
