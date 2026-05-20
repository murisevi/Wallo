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
    total_balance: Decimal
    reserved_for_goals: Decimal
    available_to_reserve: Decimal
    active_count: int
    completed_count: int
