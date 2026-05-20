"""Budget domain service — CRUD + monthly summary with spending calculation."""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.models import BankAccount, BankConnection
from app.budgets.models import Budget, Category
from app.budgets.schemas import (
    BudgetCreate,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetUpdate,
    CategoryResponse,
    CopySourceResponse,
)
from app.transactions.models import Transaction

# ---------------------------------------------------------------------------
# Category queries
# ---------------------------------------------------------------------------


async def get_categories(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[CategoryResponse]:
    """Return system categories plus any custom categories created by the user."""
    stmt = select(Category).where(
        or_(Category.user_id.is_(None), Category.user_id == user_id)
    ).order_by(Category.name)
    rows = (await db.execute(stmt)).scalars().all()
    return [CategoryResponse.model_validate(c) for c in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _date_range_for_month(month: int, year: int) -> tuple[date, date]:
    """Return (first_day, last_day) for the given month/year."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


async def _amount_spent_for_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    month: int,
    year: int,
) -> Decimal:
    """Sum DBIT transactions assigned to the given category for the given month/year.

    Transactions from disconnected bank connections are excluded.
    Matches on the category_id FK set by the ML categorization pipeline.
    """
    start, end = _date_range_for_month(month, year)

    stmt = (
        select(func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0")))
        .select_from(Transaction)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.credit_debit_indicator == "DBIT",
            Transaction.date >= start,
            Transaction.date <= end,
            BankConnection.status != "disconnected",
            Transaction.category_id == category_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one() or Decimal("0")


async def _total_spent_for_period(
    db: AsyncSession,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> Decimal:
    """Sum ALL DBIT transactions for a user in a date range (any category)."""
    stmt = (
        select(func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0")))
        .select_from(Transaction)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.credit_debit_indicator == "DBIT",
            Transaction.date >= date_from,
            Transaction.date <= date_to,
            BankConnection.status != "disconnected",
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one() or Decimal("0")


def _build_comparison_message(
    month: int,
    year: int,
    total_spent: Decimal,
) -> str:
    """Generate a human-readable spending comparison vs. the same period last month."""
    today = date.today()

    # Only generate a meaningful comparison for the current month
    if month != today.month or year != today.year:
        return "Revisa tus gastos del mes seleccionado."

    day = today.day
    days_in_month = calendar.monthrange(year, month)[1]

    # Prorate to project end-of-month spend
    daily_rate = total_spent / day if day > 0 else Decimal("0")
    projected = daily_rate * days_in_month

    return (
        f"A este ritmo proyectarás gastar {projected:,.2f} € este mes. "
        f"Llevas {day} de {days_in_month} días del mes."
    )


async def _build_comparison_message_with_last_month(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: int,
    year: int,
    total_spent: Decimal,
) -> str:
    """Compare current month spending (prorated) against same period last month."""
    today = date.today()

    # For past/future months just return a neutral message
    if month != today.month or year != today.year:
        return "Revisa tus gastos del mes seleccionado."

    day = today.day
    days_in_month = calendar.monthrange(year, month)[1]

    # Same period last month
    last_month = month - 1 if month > 1 else 12
    last_year = year if month > 1 else year - 1
    last_month_start = date(last_year, last_month, 1)
    last_month_day = min(day, calendar.monthrange(last_year, last_month)[1])
    last_month_end = date(last_year, last_month, last_month_day)

    last_spent = await _total_spent_for_period(
        db, user_id, last_month_start, last_month_end
    )

    if last_spent == Decimal("0"):
        # No comparison possible
        daily_rate = total_spent / day if day > 0 else Decimal("0")
        projected = daily_rate * days_in_month
        return (
            f"A este ritmo proyectarás gastar {projected:,.2f} € este mes "
            f"({day}/{days_in_month} días transcurridos)."
        )

    if total_spent <= last_spent:
        if last_spent > 0:
            pct = int(((last_spent - total_spent) / last_spent) * 100)
        else:
            pct = 0
        return (
            f"Vas por buen camino. A este ritmo, ahorrarás un {pct}% más que el mes pasado."
        )
    else:
        if last_spent > 0:
            pct = int(((total_spent - last_spent) / last_spent) * 100)
        else:
            pct = 0
        return (
            f"Cuidado, estás gastando un {pct}% más que el mes pasado a estas alturas."
        )


def _budget_status(percentage: float) -> str:
    if percentage >= 100:
        return "SUPERADO"
    if percentage >= 80:
        return "CERCA DEL LÍMITE"
    return "DENTRO DEL LÍMITE"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def get_monthly_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: int,
    year: int,
) -> BudgetSummaryResponse:
    """Return all budgets for a user in a given month with spending info."""
    stmt = (
        select(Budget, Category.name, Category.icon)
        .join(Category, Budget.category_id == Category.id)
        .where(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year,
        )
        .order_by(Category.name)
    )
    rows = (await db.execute(stmt)).all()

    budget_responses: list[BudgetResponse] = []
    total_limit = Decimal("0")
    total_spent = Decimal("0")

    for budget, cat_name, cat_icon in rows:
        spent = await _amount_spent_for_category(db, user_id, budget.category_id, month, year)
        limit = Decimal(str(budget.amount_limit))
        pct = float((spent / limit) * 100) if limit > 0 else 0.0

        budget_responses.append(
            BudgetResponse(
                id=budget.id,
                category_id=budget.category_id,
                category_name=cat_name,
                category_icon=cat_icon,
                amount_limit=limit,
                amount_spent=spent,
                percentage=round(pct, 1),
                month=budget.month,
                year=budget.year,
            )
        )
        total_limit += limit
        total_spent += spent

    global_pct = float((total_spent / total_limit) * 100) if total_limit > 0 else 0.0
    global_status = _budget_status(global_pct)

    comparison = await _build_comparison_message_with_last_month(
        db, user_id, month, year, total_spent
    )

    return BudgetSummaryResponse(
        month=month,
        year=year,
        total_limit=total_limit,
        total_spent=total_spent,
        total_available=total_limit - total_spent,
        percentage=round(global_pct, 1),
        status=global_status,
        budgets=budget_responses,
        comparison_message=comparison,
    )


async def create_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: BudgetCreate,
) -> BudgetResponse:
    """Create a new budget for a category/month/year. Raises 409 if duplicate."""
    # Check category exists and is accessible by this user
    cat_stmt = select(Category).where(
        Category.id == data.category_id,
        or_(Category.user_id.is_(None), Category.user_id == user_id),
    )
    category = (await db.execute(cat_stmt)).scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    # Check for duplicate
    dup_stmt = select(Budget).where(
        Budget.user_id == user_id,
        Budget.category_id == data.category_id,
        Budget.month == data.month,
        Budget.year == data.year,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A budget for this category and month already exists",
        )

    budget = Budget(
        user_id=user_id,
        category_id=data.category_id,
        amount_limit=data.amount_limit,
        month=data.month,
        year=data.year,
    )
    db.add(budget)
    await db.flush()

    spent = await _amount_spent_for_category(
        db, user_id, data.category_id, data.month, data.year
    )
    limit = Decimal(str(budget.amount_limit))
    pct = float((spent / limit) * 100) if limit > 0 else 0.0

    return BudgetResponse(
        id=budget.id,
        category_id=budget.category_id,
        category_name=category.name,
        category_icon=category.icon,
        amount_limit=limit,
        amount_spent=spent,
        percentage=round(pct, 1),
        month=budget.month,
        year=budget.year,
    )


async def update_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
    data: BudgetUpdate,
) -> BudgetResponse:
    """Update the limit of an existing budget."""
    stmt = (
        select(Budget, Category.name, Category.icon)
        .join(Category, Budget.category_id == Category.id)
        .where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found"
        )

    budget, cat_name, cat_icon = row
    budget.amount_limit = data.amount_limit  # type: ignore[assignment]
    await db.flush()

    spent = await _amount_spent_for_category(
        db, user_id, budget.category_id, budget.month, budget.year
    )
    limit = Decimal(str(budget.amount_limit))
    pct = float((spent / limit) * 100) if limit > 0 else 0.0

    return BudgetResponse(
        id=budget.id,
        category_id=budget.category_id,
        category_name=cat_name,
        category_icon=cat_icon,
        amount_limit=limit,
        amount_spent=spent,
        percentage=round(pct, 1),
        month=budget.month,
        year=budget.year,
    )


async def delete_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> None:
    """Delete a budget. Raises 404 if not found or not owned by user."""
    stmt = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    budget = (await db.execute(stmt)).scalar_one_or_none()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found"
        )
    await db.delete(budget)
    await db.flush()


async def find_copy_source(
    db: AsyncSession,
    user_id: uuid.UUID,
    target_month: int,
    target_year: int,
    max_lookback: int = 6,
) -> CopySourceResponse | None:
    """Return CopySourceResponse for the most recent previous month with budgets.

    Searches back up to max_lookback months. Returns None if nothing is found.
    """
    m, y = target_month, target_year
    for _ in range(max_lookback):
        if m == 1:
            m, y = 12, y - 1
        else:
            m -= 1
        count_stmt = select(func.count(Budget.id)).where(
            Budget.user_id == user_id,
            Budget.month == m,
            Budget.year == y,
        )
        count = (await db.execute(count_stmt)).scalar_one()
        if count > 0:
            total_stmt = select(
                func.coalesce(func.sum(Budget.amount_limit), Decimal("0"))
            ).where(
                Budget.user_id == user_id,
                Budget.month == m,
                Budget.year == y,
            )
            total = (await db.execute(total_stmt)).scalar_one() or Decimal("0")
            return CopySourceResponse(month=m, year=y, budget_count=count, total_limit=total)
    return None


async def copy_previous_month(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: int,
    year: int,
) -> BudgetSummaryResponse:
    """Clone budgets from the most recent previous month with budgets into month/year.

    Searches back up to 6 months for a source. Silently skips categories that
    already have a budget for the target month. Returns the full monthly summary.
    """
    source = await find_copy_source(db, user_id, month, year)
    if source is None:
        return await get_monthly_summary(db=db, user_id=user_id, month=month, year=year)

    prev_month, prev_year = source.month, source.year

    # Fetch all budgets from the source month
    stmt = select(Budget).where(
        Budget.user_id == user_id,
        Budget.month == prev_month,
        Budget.year == prev_year,
    )
    prev_budgets = (await db.execute(stmt)).scalars().all()

    # Single query for all existing category_ids in target month
    existing_stmt = select(Budget.category_id).where(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.year == year,
    )
    existing_ids: set[uuid.UUID] = set(
        (await db.execute(existing_stmt)).scalars().all()
    )

    for prev in prev_budgets:
        if prev.category_id in existing_ids:
            continue
        db.add(
            Budget(
                user_id=user_id,
                category_id=prev.category_id,
                amount_limit=Decimal(str(prev.amount_limit)),
                month=month,
                year=year,
            )
        )

    await db.flush()
    return await get_monthly_summary(db=db, user_id=user_id, month=month, year=year)
