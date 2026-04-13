"""Transactions API router — paginated list with optional filters + category PATCH."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.transactions.schemas import (
    TransactionCategoryUpdate,
    TransactionListResponse,
    TransactionResponse,
)
from app.transactions.service import get_transactions, update_transaction_category

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 20,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter by a specific bank account"),
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Search in description, debtor name, creditor name"),
    ] = None,
    date_from: Annotated[
        date | None, Query(description="Earliest booking date (inclusive)")
    ] = None,
    date_to: Annotated[
        date | None, Query(description="Latest booking date (inclusive)")
    ] = None,
    category_id: Annotated[
        str | None,
        Query(
            description=(
                "Filter by category UUID. "
                "Use the special value 'uncategorized' to return only transactions "
                "without a category."
            )
        ),
    ] = None,
) -> TransactionListResponse:
    """List transactions for the authenticated user.

    Supports pagination and optional filtering by account, date range,
    free-text search, and category.
    """
    return await get_transactions(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        account_id=account_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def patch_transaction_category(
    transaction_id: uuid.UUID,
    body: TransactionCategoryUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> TransactionResponse:
    """Update the category of a single transaction.

    Pass ``category_id: null`` to clear the current category.
    """
    return await update_transaction_category(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
        data=body,
    )
