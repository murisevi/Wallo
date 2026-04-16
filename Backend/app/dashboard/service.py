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

from app.banking.models import BankAccount, BankConnection
from app.core.cache import cached_response, invalidate_cache
from app.dashboard.schemas import AccountSummary, DashboardResponse
from app.transactions.models import Transaction
from app.transactions.schemas import TransactionResponse

logger = logging.getLogger(__name__)

_CACHE_TTL = 120  # seconds (2 min)


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
            select(Transaction, BankAccount.iban)
            .join(BankAccount, Transaction.account_id == BankAccount.id)
            .join(BankConnection, BankAccount.connection_id == BankConnection.id)
            .where(
                Transaction.user_id == user_id,
                BankConnection.status != "disconnected",
            )
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
            .limit(5)
        )
        txn_rows = (await self._db.execute(txn_stmt)).all()

        recent: list[TransactionResponse] = []
        for txn, iban in txn_rows:
            resp = TransactionResponse.model_validate(txn)
            resp.account_iban = iban
            recent.append(resp)
        return recent

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
            # Run both queries concurrently on the same async session
            (accounts, total_balance, last_synced_at), recent_transactions = (
                await asyncio.gather(
                    self._fetch_accounts(user_id, user_currency),
                    self._fetch_recent_transactions(user_id),
                )
            )

            response = DashboardResponse(
                total_balance=total_balance,
                currency=user_currency,
                accounts=accounts,
                recent_transactions=recent_transactions,
                last_synced_at=last_synced_at,
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
