"""Dashboard domain service — aggregated view of accounts and transactions."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.banking.models import BankAccount, BankConnection
from app.categories.models import Category
from app.categories.schemas import CategoryResponse
from app.core.cache import cached_response, invalidate_cache
from app.dashboard.schemas import AccountSummary, DashboardResponse
from app.goals.schemas import GoalResponse
from app.goals.service import get_active_goal_for_dashboard, get_reserved_for_goals
from app.recurring_charges.service import get_upcoming as get_upcoming_charges
from app.transactions.models import Transaction
from app.transactions.schemas import TransactionResponse

logger = logging.getLogger(__name__)

_CACHE_TTL = 120  # seconds (2 min)
SuggestedCategory = aliased(Category)


class DashboardService:
    def __init__(self, db: AsyncSession, redis: Any | None = None) -> None:
        self._db = db
        self._redis = redis

    # ------------------------------------------------------------------
    # Private query helpers (run in parallel via asyncio.gather)
    # ------------------------------------------------------------------

    async def _fetch_accounts(
        self, user_id: uuid.UUID, user_currency: str
    ) -> tuple[list[AccountSummary], Decimal, datetime | None]:
        """Load all active accounts for the user and compute total balance."""
        stmt = (
            select(
                BankAccount,
                BankConnection.bank_name,
                BankConnection.bank_logo,
            )
            .join(BankConnection, BankAccount.connection_id == BankConnection.id)
            .where(
                BankAccount.user_id == user_id,
                BankConnection.status != "disconnected",
            )
            .order_by(BankConnection.bank_name, BankAccount.name)
        )
        rows = (await self._db.execute(stmt)).all()

        accounts: list[AccountSummary] = []
        total_balance = Decimal("0")
        last_synced_at: datetime | None = None

        for account, bank_name, bank_logo in rows:
            summary = AccountSummary(
                id=account.id,
                iban=account.iban,
                name=account.name,
                bank_name=bank_name,
                bank_logo=bank_logo,
                balance=account.balance_amount,
                currency=account.currency,
            )
            accounts.append(summary)

            if account.currency == user_currency and account.balance_amount is not None:
                total_balance += account.balance_amount

            if account.last_synced_at is not None:
                if last_synced_at is None or account.last_synced_at > last_synced_at:
                    last_synced_at = account.last_synced_at

        if not accounts:
            logger.debug("No accounts found for user %s", user_id)

        return accounts, total_balance, last_synced_at

    async def _fetch_recent_transactions(
        self, user_id: uuid.UUID
    ) -> list[TransactionResponse]:
        """Load the 5 most recent transactions across all connected accounts."""
        txn_stmt = (
            select(Transaction, BankAccount.iban, Category, SuggestedCategory)
            .join(BankAccount, Transaction.account_id == BankAccount.id)
            .join(BankConnection, BankAccount.connection_id == BankConnection.id)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .outerjoin(
                SuggestedCategory,
                Transaction.suggested_category_id == SuggestedCategory.id,
            )
            .where(
                Transaction.user_id == user_id,
                BankConnection.status != "disconnected",
            )
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
            .limit(5)
        )
        txn_rows = (await self._db.execute(txn_stmt)).all()

        recent: list[TransactionResponse] = []
        for txn, iban, category, suggested_category in txn_rows:
            resp = TransactionResponse.model_validate(txn)
            resp.account_iban = iban
            if category is not None:
                resp.category_name = category.name
                resp.category_icon = category.icon
                resp.category = CategoryResponse.model_validate(category)
            if suggested_category is not None:
                resp.suggested_category_name = suggested_category.name
                resp.suggested_category_icon = suggested_category.icon
                resp.suggested_category = CategoryResponse.model_validate(
                    suggested_category
                )
            recent.append(resp)
        return recent

    async def _fetch_active_goal(self, user_id: uuid.UUID) -> GoalResponse | None:
        try:
            return await get_active_goal_for_dashboard(self._db, user_id)
        except Exception:
            return None

    async def _fetch_reserved_for_goals(self, user_id: uuid.UUID) -> Decimal:
        return await get_reserved_for_goals(self._db, user_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_dashboard(
        self, user_id: uuid.UUID, user_currency: str
    ) -> DashboardResponse:
        """Build the unified dashboard view for a user.

        Results are cached in Redis for _CACHE_TTL seconds. The two DB queries
        (accounts + recent transactions) run in parallel via asyncio.gather.
        """
        cache_key = f"dashboard:{user_id}"

        async def _fetch() -> dict[str, object]:
            # Run all queries concurrently on the same async session
            (
                (accounts, total_balance, last_synced_at),
                recent_transactions,
                upcoming_charges,
                active_goal,
                reserved_for_goals,
            ) = await asyncio.gather(
                self._fetch_accounts(user_id, user_currency),
                self._fetch_recent_transactions(user_id),
                get_upcoming_charges(self._db, user_id),
                self._fetch_active_goal(user_id),
                self._fetch_reserved_for_goals(user_id),
            )

            response = DashboardResponse(
                total_balance=total_balance,
                reserved_for_goals=reserved_for_goals,
                available_balance=total_balance - reserved_for_goals,
                currency=user_currency,
                accounts=accounts,
                recent_transactions=recent_transactions,
                last_synced_at=last_synced_at,
                upcoming_charges=upcoming_charges,
                active_goal=active_goal,
            )
            # Return as dict so cached_response can serialise it to JSON
            return response.model_dump(mode="json")

        data = await cached_response(
            redis=self._redis,
            key=cache_key,
            ttl=_CACHE_TTL,
            fetch_fn=_fetch,
        )
        return DashboardResponse.model_validate(data)

    async def invalidate(self, user_id: uuid.UUID) -> None:
        """Bust the dashboard cache for a single user (after syncing transactions)."""
        await invalidate_cache(self._redis, f"dashboard:{user_id}")
