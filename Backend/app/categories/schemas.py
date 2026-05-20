"""Pydantic schemas for categories and categorisation."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

# ── Category ──────────────────────────────────────────────────────────────


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    icon: str
    color: str
    type: str  # "expense" | "income"
    is_custom: bool


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(default="tag", max_length=50)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    type: str = Field(..., pattern=r"^(expense|income)$")


# ── Category Correction ───────────────────────────────────────────────────


class CategoryCorrectionRequest(BaseModel):
    category_id: uuid.UUID


class CategoryCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: uuid.UUID
    old_category_id: uuid.UUID | None
    new_category_id: uuid.UUID
    confidence_score: float
    # Other transactions with the same merchant updated in the same call.
    also_updated: int


class AcceptSuggestionsRequest(BaseModel):
    transaction_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)


class AcceptSuggestionsResponse(BaseModel):
    accepted: int
    skipped: int
    also_updated: int


# ── Categorisation Stats ──────────────────────────────────────────────────


class CategorizationStatsResponse(BaseModel):
    total_transactions: int
    auto_categorized: int
    manually_corrected: int
    uncategorized: int
    merchant_map_coverage: float  # 0.0 - 1.0
    model_accuracy: float | None


# ── Recategorize ──────────────────────────────────────────────────────────


class RecategorizeResponse(BaseModel):
    """Summary returned by the bulk recategorization endpoint."""

    total: int
    rule_based: int = 0
    merchant_map: int
    mcc: int = 0
    global_dict: int = 0
    keyword_rule: int = 0
    keyword_suggested: int = 0
    ml_auto: int
    ml_suggested: int
    uncategorized: int
