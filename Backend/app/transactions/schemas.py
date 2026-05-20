from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.categories.schemas import CategoryResponse


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    entry_reference: str | None
    amount: Decimal
    currency: str
    date: date
    value_date: date | None
    description: str | None
    debtor_name: str | None
    creditor_name: str | None
    credit_debit_indicator: str
    bank_transaction_code: str | None
    merchant_category_code: str | None = None
    status: str
    category_text: str | None = None  # legacy string column (rarely populated)
    account_iban: str | None = None

    # Categorisation fields — populated after ML categorisation
    category_id: uuid.UUID | None = None
    category: CategoryResponse | None = None       # nested category object
    category_name: str | None = None               # convenience duplicate for frontend
    category_icon: str | None = None               # convenience duplicate for frontend
    # "merchant_map" | "ml_auto" | "ml_suggested" | "manual"
    categorization_method: str | None = None
    confidence_score: float | None = None          # 0.0 - 1.0
    is_manually_corrected: bool = False

    # ML suggestion fields — do not affect reports/budgets until confirmed
    suggested_category_id: uuid.UUID | None = None
    suggested_category: CategoryResponse | None = None
    suggested_category_name: str | None = None
    suggested_category_icon: str | None = None
    suggested_categorization_method: str | None = None
    suggested_confidence_score: float | None = None


class TransactionCategoryUpdate(BaseModel):
    """Payload for PATCH /transactions/{id} — update category only."""

    category_id: uuid.UUID | None


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
