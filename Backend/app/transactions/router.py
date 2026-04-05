"""Transactions API router — paginated list with optional filters."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.transactions.schemas import TransactionListResponse
from app.transactions.service import get_transactions

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
) -> TransactionListResponse:
    """List transactions for the authenticated user.

    Supports pagination and optional filtering by account, date range, and
    free-text search across description and counterparty names.
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
    )
