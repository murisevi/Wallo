"""Reports API router — spending analytics, income/expense comparison, and CSV export."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
from app.reports import service
from app.reports.schemas import (
    BalanceEvolutionResponse,
    IncomeByCategoryResponse,
    IncomeVsExpensesResponse,
    PeriodEnum,
    SankeyResponse,
    SpendingByCategoryResponse,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/spending-by-category", response_model=SpendingByCategoryResponse)
async def spending_by_category(
    current_user: CurrentUser,
    db: DbSession,
    period: Annotated[PeriodEnum, Query(description="Aggregation period")] = PeriodEnum.quarter,
    date: Annotated[
        date_cls | None,
        Query(description="Reference date (ISO 8601). Defaults to today."),
    ] = None,
) -> SpendingByCategoryResponse:
    """Return spending grouped by category for the requested period."""
    return await service.get_spending_by_category(
        db=db,
        user_id=current_user.id,
        period=period,
        ref_date=date,
    )


@router.get("/income-vs-expenses", response_model=IncomeVsExpensesResponse)
async def income_vs_expenses(
    current_user: CurrentUser,
    db: DbSession,
    period: Annotated[PeriodEnum, Query(description="Aggregation period")] = PeriodEnum.quarter,
    date: Annotated[
        date_cls | None,
        Query(description="Reference date (ISO 8601). Defaults to today."),
    ] = None,
) -> IncomeVsExpensesResponse:
    """Return income vs. expenses broken down by sub-period time buckets."""
    return await service.get_income_vs_expenses(
        db=db,
        user_id=current_user.id,
        period=period,
        ref_date=date,
    )


@router.get("/cashflow-sankey", response_model=SankeyResponse)
async def cashflow_sankey(
    current_user: CurrentUser,
    db: DbSession,
    period: Annotated[PeriodEnum, Query(description="Aggregation period")] = PeriodEnum.quarter,
    date: Annotated[
        date_cls | None,
        Query(description="Reference date (ISO 8601). Defaults to today."),
    ] = None,
) -> SankeyResponse:
    """Return Sankey graph data: income sources → expense categories."""
    return await service.get_cashflow_sankey(
        db=db,
        user_id=current_user.id,
        period=period,
        ref_date=date,
    )


@router.get("/balance-evolution", response_model=BalanceEvolutionResponse)
async def balance_evolution(
    current_user: CurrentUser,
    db: DbSession,
    period: Annotated[PeriodEnum, Query(description="Aggregation period")] = PeriodEnum.quarter,
    date: Annotated[
        date_cls | None,
        Query(description="Reference date (ISO 8601). Defaults to today."),
    ] = None,
) -> BalanceEvolutionResponse:
    """Return reconstructed balance evolution for the requested period."""
    return await service.get_balance_evolution(
        db=db,
        user_id=current_user.id,
        period=period,
        ref_date=date,
    )


@router.get("/income-by-category", response_model=IncomeByCategoryResponse)
async def income_by_category(
    current_user: CurrentUser,
    db: DbSession,
    period: Annotated[PeriodEnum, Query(description="Aggregation period")] = PeriodEnum.quarter,
    date: Annotated[
        date_cls | None,
        Query(description="Reference date (ISO 8601). Defaults to today."),
    ] = None,
) -> IncomeByCategoryResponse:
    """Return income grouped by category for the requested period."""
    return await service.get_income_by_category(
        db=db,
        user_id=current_user.id,
        period=period,
        ref_date=date,
    )


@router.get("/export-csv")
async def export_csv(
    current_user: CurrentUser,
    db: DbSession,
    period: Annotated[PeriodEnum, Query(description="Aggregation period")] = PeriodEnum.quarter,
    date: Annotated[
        date_cls | None,
        Query(description="Reference date (ISO 8601). Defaults to today."),
    ] = None,
) -> StreamingResponse:
    """Export all transactions in the period as a CSV file download."""
    ref = date or date_cls.today()
    filename = f"wallo_transactions_{period.value}_{ref.isoformat()}.csv"

    csv_content = await service.export_transactions_csv(
        db=db,
        user_id=current_user.id,
        period=period,
        ref_date=date,
    )

    return StreamingResponse(
        iter([csv_content.read()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
