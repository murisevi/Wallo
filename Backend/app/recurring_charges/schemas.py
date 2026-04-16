"""Pydantic schemas for recurring charges API."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RecurringChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    amount: Decimal
    currency: str
    periodicity: str
    status: str
    user_confirmed: bool
    occurrence_count: int
    next_predicted_date: date
    is_installment: bool
    installment_total: int | None
    installment_paid: int | None


class SetInstallmentRequest(BaseModel):
    installment_total: int = Field(ge=1)
