"""Reports domain schemas — response models for financial reporting endpoints."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class PeriodEnum(str, Enum):
    month = "month"
    quarter = "quarter"
    year = "year"
    week = "week"


class CategorySpending(BaseModel):
    name: str
    amount: Decimal
    percentage: float
    color: str


class SpendingByCategoryResponse(BaseModel):
    total_spending: Decimal
    categories: list[CategorySpending]


class TimeDataPoint(BaseModel):
    label: str
    income: Decimal
    expenses: Decimal


class IncomeVsExpensesResponse(BaseModel):
    data_points: list[TimeDataPoint]


class SankeyNode(BaseModel):
    id: str
    label: str


class SankeyLink(BaseModel):
    source: str
    target: str
    value: Decimal


class SankeyResponse(BaseModel):
    nodes: list[SankeyNode]
    links: list[SankeyLink]


class BalanceEvolutionPoint(BaseModel):
    date: str
    label: str
    balance: Decimal
    change_percent: float


class BalanceEvolutionResponse(BaseModel):
    period: str
    data_points: list[BalanceEvolutionPoint]
    start_balance: Decimal
    end_balance: Decimal
    total_change: Decimal
    total_change_percent: float


class IncomeByCategoryResponse(BaseModel):
    period: str
    total_income: Decimal
    categories: list[CategorySpending]
