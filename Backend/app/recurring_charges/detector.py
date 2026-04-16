"""Pure recurring-charge detection algorithm — no database dependencies.

Given a list of transaction tuples (merchant_key, display_name, amount,
currency, date, is_subscription), groups them by merchant_key, checks for a
consistent WEEKLY / MONTHLY / ANNUAL periodicity across ≥ 2 occurrences, and
returns a DetectedCharge dataclass for each confirmed pattern.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

# Periodicity tolerances (days)
_WEEKLY_TARGET = 7
_MONTHLY_TARGET = 30
_ANNUAL_TARGET = 365

_WEEKLY_TOL = 2
_MONTHLY_TOL = 4
_ANNUAL_TOL = 15

_PERIODICITY_SPECS = [
    (_WEEKLY_TARGET, _WEEKLY_TOL, "WEEKLY"),
    (_MONTHLY_TARGET, _MONTHLY_TOL, "MONTHLY"),
    (_ANNUAL_TARGET, _ANNUAL_TOL, "ANNUAL"),
]

_PERIODICITY_ADVANCE: dict[str, timedelta] = {
    "WEEKLY": timedelta(days=7),
    "MONTHLY": timedelta(days=30),
    "ANNUAL": timedelta(days=365),
}


@dataclass
class DetectedCharge:
    merchant_key: str
    display_name: str
    amount: Decimal
    currency: str
    periodicity: str
    occurrence_count: int
    last_seen_date: date
    next_predicted_date: date
    is_subscription: bool


def _classify_periodicity(intervals: list[int]) -> str | None:
    """Return the periodicity label if all intervals are consistent, else None."""
    if not intervals:
        return None
    avg = sum(intervals) / len(intervals)
    for target, tol, label in _PERIODICITY_SPECS:
        if abs(avg - target) <= tol:
            # Every individual interval must also be within 2x tolerance
            if all(abs(iv - target) <= tol * 2 for iv in intervals):
                return label
    return None


def detect_recurring(
    transactions: list[tuple[str, str, Decimal, str, date, bool]],
) -> list[DetectedCharge]:
    """Detect recurring charge patterns from transaction tuples.

    Args:
        transactions: List of (merchant_key, display_name, amount, currency,
                      date, is_subscription) tuples. Already-cleaned data.

    Returns:
        One DetectedCharge per merchant with ≥ 2 occurrences and a
        consistent periodicity (WEEKLY / MONTHLY / ANNUAL).
    """
    TxnRow = tuple[str, str, Decimal, str, date, bool]
    groups: dict[str, list[TxnRow]] = defaultdict(list)
    for row in transactions:
        groups[row[0]].append(row)

    results: list[DetectedCharge] = []
    for merchant_key, rows in groups.items():
        if len(rows) < 2:
            continue

        rows_sorted = sorted(rows, key=lambda r: r[4])

        # Deduplicate by date: the same charge may appear on multiple bank
        # accounts (e.g. the bank reports it on both a current and savings view).
        seen_dates: set[date] = set()
        deduped: list[tuple[str, str, Decimal, str, date, bool]] = []
        for row in rows_sorted:
            if row[4] not in seen_dates:
                seen_dates.add(row[4])
                deduped.append(row)
        rows_sorted = deduped

        if len(rows_sorted) < 2:
            continue

        dates = [r[4] for r in rows_sorted]
        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]

        periodicity = _classify_periodicity(intervals)
        if periodicity is None:
            continue

        last = rows_sorted[-1]
        display_name: str = last[1]
        amount: Decimal = abs(last[2])
        currency: str = last[3]
        last_seen: date = last[4]
        is_subscription = any(r[5] for r in rows_sorted)

        results.append(
            DetectedCharge(
                merchant_key=merchant_key,
                display_name=display_name,
                amount=amount,
                currency=currency,
                periodicity=periodicity,
                occurrence_count=len(rows_sorted),
                last_seen_date=last_seen,
                next_predicted_date=last_seen + _PERIODICITY_ADVANCE[periodicity],
                is_subscription=is_subscription,
            )
        )

    return results
