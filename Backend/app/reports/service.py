"""Reports domain service — financial analytics and CSV export."""

from __future__ import annotations

import calendar
import csv
import io
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.models import BankAccount, BankConnection
from app.budgets.models import Category
from app.reports.schemas import (
    BalanceEvolutionPoint,
    BalanceEvolutionResponse,
    CategorySpending,
    IncomeByCategoryResponse,
    IncomeVsExpensesResponse,
    PeriodEnum,
    SankeyLink,
    SankeyNode,
    SankeyResponse,
    SpendingByCategoryResponse,
    TimeDataPoint,
)
from app.transactions.models import Transaction

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_COLORS: dict[str, str] = {
    # ── Gastos (seeded colours) ──────────────────────────────────────────
    "alimentación": "#22C55E",
    "alimentacion": "#22C55E",
    "restaurantes y bares": "#F97316",
    "restaurantes": "#F97316",
    "transporte": "#3B82F6",
    "vivienda": "#8B5CF6",
    "suministros": "#EAB308",
    "salud": "#EF4444",
    "ocio": "#EC4899",
    "ropa": "#A855F7",
    "educación": "#06B6D4",
    "educacion": "#06B6D4",
    "suscripciones": "#F59E0B",
    "seguros": "#64748B",
    "mascotas": "#D946EF",
    "regalos": "#F43F5E",
    "otros gastos": "#6B7280",
    # ── Common variants / aliases ────────────────────────────────────────
    "supermercado": "#22C55E",
    "tecnología": "#2980B9",
    "tecnologia": "#2980B9",
    "viajes": "#0EA5E9",
    "gimnasio": "#D35400",
    "ocio y cenas": "#E74C3C",
    "ocio y entretenimiento": "#EC4899",
    # ── Ingresos ────────────────────────────────────────────────────────
    "nómina": "#10B981",
    "nomina": "#10B981",
    "salario": "#10B981",
    "freelance": "#14B8A6",
    "transferencias recibidas": "#0EA5E9",
    "devoluciones": "#84CC16",
    "otros ingresos": "#6B7280",
    "ingresos": "#27AE60",
    # ── Fallback ─────────────────────────────────────────────────────────
    "sin categoría": "#9CA3AF",
    "sin categoria": "#9CA3AF",
    "otros": "#9CA3AF",
}

# Distinct colour palette used as hash-based fallback for unknown categories
_FALLBACK_PALETTE = [
    "#F97316", "#22C55E", "#3B82F6", "#8B5CF6", "#EAB308",
    "#EF4444", "#EC4899", "#A855F7", "#06B6D4", "#F59E0B",
    "#D946EF", "#14B8A6", "#84CC16", "#F43F5E", "#0EA5E9",
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
]

INCOME_COLORS: dict[str, str] = {
    "nómina": "#1A5632",
    "nomina": "#1A5632",
    "salario": "#1A5632",
    "ingresos": "#27AE60",
    "freelance": "#2ECC71",
    "inversiones": "#F39C12",
    "dividendos": "#E67E22",
    "alquiler": "#8E44AD",
    "transferencia": "#2471A3",
    "reembolso": "#5DADE2",
    "otros ingresos": "#95A5A6",
}
INCOME_DEFAULT_COLOR = "#27AE60"

UNCATEGORIZED_LABEL = "Sin categoría"

MONTH_ABBR_ES = [
    "ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
    "JUL", "AGO", "SEP", "OCT", "NOV", "DIC",
]

DAY_ABBR_ES = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_date_range(period: PeriodEnum, ref: date | None) -> tuple[date, date]:
    """Return (start, end) dates for the given period relative to ref.

    Week period: spans days 1-7, 8-14, 15-21, or 22-end of the month,
    determined by which 7-day block the ref date falls into.
    """
    today = ref or date.today()
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]

    if period == PeriodEnum.week:
        # 0-indexed week block: 0 = days 1-7, 1 = 8-14, 2 = 15-21, 3+ = 22-end
        week_block = (today.day - 1) // 7
        start_day = week_block * 7 + 1
        end_day = min(start_day + 6, last_day_of_month)
        start = today.replace(day=start_day)
        end = today.replace(day=end_day)

    elif period == PeriodEnum.month:
        start = today.replace(day=1)
        end = today.replace(day=last_day_of_month)

    elif period == PeriodEnum.quarter:
        q = (today.month - 1) // 3  # 0-indexed quarter (0–3)
        start_month = q * 3 + 1
        end_month = start_month + 2
        start = date(today.year, start_month, 1)
        last_day = calendar.monthrange(today.year, end_month)[1]
        end = date(today.year, end_month, last_day)

    else:  # year
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)

    return start, end


def _category_color(name: str) -> str:
    """Return a deterministic colour for a category name, never plain gray."""
    color = CATEGORY_COLORS.get(name.lower())
    if color:
        return color
    # Hash-based fallback — consistent color per unknown name
    idx = sum(ord(c) for c in name) % len(_FALLBACK_PALETTE)
    return _FALLBACK_PALETTE[idx]


def _income_category_color(name: str) -> str:
    return INCOME_COLORS.get(name.lower(), INCOME_DEFAULT_COLOR)


def _week_label(txn_date: date) -> str:
    """Return 'Semana N' for the given date within its month."""
    week = (txn_date.day - 1) // 7 + 1
    return f"Semana {week}"


def _month_label(txn_date: date) -> str:
    return MONTH_ABBR_ES[txn_date.month - 1]


def _day_label(txn_date: date) -> str:
    """Return 'Día DD' for individual-day buckets (week period)."""
    return f"Día {txn_date.day}"


def _bucket_label(txn_date: date, period: PeriodEnum) -> str:
    if period == PeriodEnum.week:
        return _day_label(txn_date)
    if period == PeriodEnum.month:
        return _week_label(txn_date)
    return _month_label(txn_date)


def _ordered_buckets(start: date, end: date, period: PeriodEnum) -> list[str]:
    """Return all expected bucket labels in the period, ordered chronologically."""
    if period == PeriodEnum.week:
        # One label per calendar day in the week range
        labels: list[str] = []
        current = start
        while current <= end:
            labels.append(_day_label(current))
            current += timedelta(days=1)
        return labels

    if period == PeriodEnum.month:
        last_day = calendar.monthrange(start.year, start.month)[1]
        weeks = (last_day - 1) // 7 + 1
        return [f"Semana {w}" for w in range(1, weeks + 1)]

    # quarter or year — enumerate each calendar month in range
    month_labels: list[str] = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        month_labels.append(MONTH_ABBR_ES[m - 1])
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return month_labels


def _ordered_balance_buckets(
    start: date, end: date, period: PeriodEnum
) -> list[tuple[str, date]]:
    """Return (label, representative_date) pairs for each bucket in chronological order."""
    if period == PeriodEnum.week:
        result: list[tuple[str, date]] = []
        current = start
        while current <= end:
            result.append((_day_label(current), current))
            current += timedelta(days=1)
        return result

    if period == PeriodEnum.month:
        last_day = calendar.monthrange(start.year, start.month)[1]
        weeks = (last_day - 1) // 7 + 1
        return [
            (f"Semana {w}", start.replace(day=(w - 1) * 7 + 1))
            for w in range(1, weeks + 1)
        ]

    # quarter or year — one bucket per calendar month
    result = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        result.append((MONTH_ABBR_ES[m - 1], date(y, m, 1)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return result


async def _get_current_balance(db: AsyncSession, user_id: uuid.UUID) -> Decimal:
    """Sum of all active bank account balances for the user."""
    stmt = (
        select(func.sum(BankAccount.balance_amount))
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .where(
            BankAccount.user_id == user_id,
            BankConnection.status != "disconnected",
        )
    )
    result = await db.execute(stmt)
    total = result.scalar()
    return Decimal(str(total)) if total is not None else Decimal(0)


async def _fetch_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    start: date,
    end: date,
) -> list[tuple[Transaction, str | None, str | None]]:
    """Fetch all non-disconnected transactions for the user in [start, end].

    Returns list of (Transaction, iban, category_name).
    """
    disconnected_filter = BankConnection.status != "disconnected"
    stmt = (
        select(Transaction, BankAccount.iban, Category.name)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .join(BankConnection, BankAccount.connection_id == BankConnection.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date <= end,
            disconnected_filter,
        )
        .order_by(Transaction.date.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [(txn, iban, cat_name) for txn, iban, cat_name in rows]


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def get_spending_by_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    period: PeriodEnum,
    ref_date: date | None,
) -> SpendingByCategoryResponse:
    """Group expense transactions by category and compute percentages."""
    start, end = _get_date_range(period, ref_date)
    rows = await _fetch_transactions(db, user_id, start, end)

    totals: dict[str, Decimal] = defaultdict(Decimal)
    for txn, _iban, cat_name in rows:
        if txn.amount < 0:  # expense only
            label = cat_name or UNCATEGORIZED_LABEL
            totals[label] += abs(txn.amount)

    total_spending = sum(totals.values(), Decimal(0))

    categories: list[CategorySpending] = []
    for name, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        pct = float(amount / total_spending * 100) if total_spending else 0.0
        categories.append(
            CategorySpending(
                name=name,
                amount=amount,
                percentage=round(pct, 1),
                color=_category_color(name),
            )
        )

    return SpendingByCategoryResponse(
        total_spending=total_spending,
        categories=categories,
    )


async def get_income_vs_expenses(
    db: AsyncSession,
    user_id: uuid.UUID,
    period: PeriodEnum,
    ref_date: date | None,
) -> IncomeVsExpensesResponse:
    """Group transactions by time bucket and split income vs expenses."""
    start, end = _get_date_range(period, ref_date)
    rows = await _fetch_transactions(db, user_id, start, end)

    income_map: dict[str, Decimal] = defaultdict(Decimal)
    expense_map: dict[str, Decimal] = defaultdict(Decimal)

    for txn, _iban, _cat_name in rows:
        label = _bucket_label(txn.date, period)
        if txn.amount > 0:
            income_map[label] += txn.amount
        else:
            expense_map[label] += abs(txn.amount)

    ordered = _ordered_buckets(start, end, period)
    data_points = [
        TimeDataPoint(
            label=lbl,
            income=income_map.get(lbl, Decimal(0)),
            expenses=expense_map.get(lbl, Decimal(0)),
        )
        for lbl in ordered
    ]

    return IncomeVsExpensesResponse(data_points=data_points)


async def get_cashflow_sankey(
    db: AsyncSession,
    user_id: uuid.UUID,
    period: PeriodEnum,
    ref_date: date | None,
) -> SankeyResponse:
    """Build a Sankey graph: income sources → expense categories."""
    start, end = _get_date_range(period, ref_date)
    rows = await _fetch_transactions(db, user_id, start, end)

    income_sources: dict[str, Decimal] = defaultdict(Decimal)
    expense_categories: dict[str, Decimal] = defaultdict(Decimal)

    for txn, _iban, cat_name in rows:
        if txn.amount > 0:
            # Source label: prefer creditor/debtor name, fall back to description
            label = (
                txn.creditor_name
                or txn.debtor_name
                or txn.description
                or "Ingreso"
            )
            # Truncate long labels for readability
            if len(label) > 40:
                label = label[:37] + "…"
            income_sources[label] += txn.amount
        else:
            cat = cat_name or UNCATEGORIZED_LABEL
            expense_categories[cat] += abs(txn.amount)

    total_expenses = sum(expense_categories.values(), Decimal(0))

    if not income_sources or not expense_categories or total_expenses == 0:
        return SankeyResponse(nodes=[], links=[])

    # Build node list: income sources on left, categories on right
    nodes: list[SankeyNode] = []
    income_ids: list[str] = []
    for source in income_sources:
        nid = f"income_{source}"
        nodes.append(SankeyNode(id=nid, label=source))
        income_ids.append(nid)

    category_ids: list[str] = []
    for cat in expense_categories:
        nid = f"cat_{cat}"
        nodes.append(SankeyNode(id=nid, label=cat))
        category_ids.append(nid)

    # Build links: each income source → each expense category, proportionally
    links: list[SankeyLink] = []
    expense_items = list(expense_categories.items())
    income_items = list(income_sources.items())

    for i, (source, income_total) in enumerate(income_items):
        for j, (cat, cat_total) in enumerate(expense_items):
            proportion = cat_total / total_expenses
            value = income_total * proportion
            if value > Decimal("0.01"):
                links.append(
                    SankeyLink(
                        source=income_ids[i],
                        target=category_ids[j],
                        value=value.quantize(Decimal("0.01")),
                    )
                )

    return SankeyResponse(nodes=nodes, links=links)


async def export_transactions_csv(
    db: AsyncSession,
    user_id: uuid.UUID,
    period: PeriodEnum,
    ref_date: date | None,
) -> io.StringIO:
    """Generate CSV content for all transactions in the period."""
    start, end = _get_date_range(period, ref_date)
    rows = await _fetch_transactions(db, user_id, start, end)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Fecha", "Concepto", "Categoría", "Cuenta (IBAN)", "Importe", "Moneda"])

    for txn, iban, cat_name in rows:
        concept = (
            txn.description
            or txn.creditor_name
            or txn.debtor_name
            or "—"
        )
        writer.writerow([
            txn.date.isoformat(),
            concept,
            cat_name or UNCATEGORIZED_LABEL,
            iban or "—",
            str(txn.amount),
            txn.currency,
        ])

    output.seek(0)
    return output


async def get_balance_evolution(
    db: AsyncSession,
    user_id: uuid.UUID,
    period: PeriodEnum,
    ref_date: date | None,
) -> BalanceEvolutionResponse:
    """Reconstruct balance at each time bucket using current balance minus future transactions."""
    start, end = _get_date_range(period, ref_date)
    today = date.today()

    # Fetch transactions from period start to today (may go beyond period end)
    rows_to_today = await _fetch_transactions(db, user_id, start, today)

    # Current balance reflects all transactions up to now
    current_balance = await _get_current_balance(db, user_id)

    # Balance at period start = current_balance minus all transactions since then
    total_since_start = sum((txn.amount for txn, _, _ in rows_to_today), Decimal(0))
    start_balance = current_balance - total_since_start

    # Group transactions within the period by bucket label
    bucket_totals: dict[str, Decimal] = defaultdict(Decimal)
    for txn, _, _ in rows_to_today:
        if txn.date <= end:
            label = _bucket_label(txn.date, period)
            bucket_totals[label] += txn.amount

    ordered = _ordered_balance_buckets(start, end, period)

    data_points: list[BalanceEvolutionPoint] = []
    running_balance = start_balance
    prev_balance = start_balance

    for label, bucket_date in ordered:
        running_balance += bucket_totals.get(label, Decimal(0))

        if prev_balance != 0:
            change_pct = float((running_balance - prev_balance) / abs(prev_balance) * 100)
        else:
            change_pct = 0.0

        data_points.append(
            BalanceEvolutionPoint(
                date=bucket_date.isoformat(),
                label=label,
                balance=running_balance.quantize(Decimal("0.01")),
                change_percent=round(change_pct, 2),
            )
        )
        prev_balance = running_balance

    end_balance = data_points[-1].balance if data_points else start_balance.quantize(Decimal("0.01"))
    total_change = end_balance - start_balance.quantize(Decimal("0.01"))
    total_change_pct = (
        float(total_change / abs(start_balance) * 100) if start_balance != 0 else 0.0
    )

    return BalanceEvolutionResponse(
        period=f"{start.isoformat()} — {end.isoformat()}",
        data_points=data_points,
        start_balance=start_balance.quantize(Decimal("0.01")),
        end_balance=end_balance,
        total_change=total_change.quantize(Decimal("0.01")),
        total_change_percent=round(total_change_pct, 2),
    )


async def get_income_by_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    period: PeriodEnum,
    ref_date: date | None,
) -> IncomeByCategoryResponse:
    """Group income transactions by category and compute percentages."""
    start, end = _get_date_range(period, ref_date)
    rows = await _fetch_transactions(db, user_id, start, end)

    totals: dict[str, Decimal] = defaultdict(Decimal)
    for txn, _, cat_name in rows:
        if txn.amount > 0:  # income only
            label = cat_name or "Ingresos"
            totals[label] += txn.amount

    total_income = sum(totals.values(), Decimal(0))

    categories: list[CategorySpending] = []
    for name, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        pct = float(amount / total_income * 100) if total_income else 0.0
        categories.append(
            CategorySpending(
                name=name,
                amount=amount,
                percentage=round(pct, 1),
                color=_income_category_color(name),
            )
        )

    return IncomeByCategoryResponse(
        period=f"{start.isoformat()} — {end.isoformat()}",
        total_income=total_income,
        categories=categories,
    )
