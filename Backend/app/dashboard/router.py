"""Dashboard API router — single aggregated endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dashboard.schemas import DashboardResponse
from app.dashboard.service import DashboardService
from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: DbSession) -> DashboardService:
    return DashboardService(db=db)


DashboardSvc = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    current_user: CurrentUser,
    svc: DashboardSvc,
) -> DashboardResponse:
    """Return a unified overview: total balance, all accounts, and the 5 most
    recent transactions across all connected banks."""
    return await svc.get_dashboard(
        user_id=current_user.id,
        user_currency=current_user.currency,
    )
