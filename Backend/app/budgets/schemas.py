"""Budget domain Pydantic schemas."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, field_validator


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    icon: str
    type: str
    is_custom: bool

    model_config = {"from_attributes": True}


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    amount_limit: Decimal
    month: int
    year: int

    @field_validator("amount_limit")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount_limit must be greater than 0")
        return v

    @field_validator("month")
    @classmethod
    def month_must_be_valid(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("month must be between 1 and 12")
        return v

    @field_validator("year")
    @classmethod
    def year_must_be_valid(cls, v: int) -> int:
        if v < 2000:
            raise ValueError("year must be >= 2000")
        return v


class BudgetUpdate(BaseModel):
    amount_limit: Decimal

    @field_validator("amount_limit")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount_limit must be greater than 0")
        return v


class BudgetResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_icon: str
    amount_limit: Decimal
    amount_spent: Decimal
    percentage: float
    month: int
    year: int

    model_config = {"from_attributes": True}


class BudgetSummaryResponse(BaseModel):
    month: int
    year: int
    total_limit: Decimal
    total_spent: Decimal
    total_available: Decimal
    percentage: float
    status: str  # "DENTRO DEL LÍMITE" | "CERCA DEL LÍMITE" | "SUPERADO"
    budgets: list[BudgetResponse]
    comparison_message: str


class CopySourceResponse(BaseModel):
    month: int
    year: int
    budget_count: int
    total_limit: Decimal
