"""Dashboard domain service — aggregated view of accounts and transactions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.models import BankAccount, BankConnection
from app.dashboard.schemas import AccountSummary, DashboardResponse
from app.transactions.models import Transaction
from app.transactions.schemas import TransactionResponse

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_dashboard(
        self, user_id: uuid.UUID, user_currency: str
    ) -> DashboardResponse:
        """Build the unified dashboard view for a user.

        Balances are summed only for accounts whose currency matches the
        user's preferred currency. Accounts in other currencies are still
        listed in `accounts` but excluded from `total_balance`.
        """
        # ── Load accounts + connection metadata ──────────────────────────────
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

            # Accumulate balance only when currency matches user preference
            if account.currency == user_currency and account.balance_amount is not None:
                total_balance += account.balance_amount

            # Track most recent sync timestamp
            if account.last_synced_at is not None:
                if last_synced_at is None or account.last_synced_at > last_synced_at:
                    last_synced_at = account.last_synced_at

        if not accounts:
            logger.debug("No accounts found for user %s", user_id)

        # ── Last 5 transactions across all accounts ───────────────────────────
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

        recent_transactions: list[TransactionResponse] = []
        for txn, iban in txn_rows:
            resp = TransactionResponse.model_validate(txn)
            resp.account_iban = iban
            recent_transactions.append(resp)

        return DashboardResponse(
            total_balance=total_balance,
            currency=user_currency,
            accounts=accounts,
            recent_transactions=recent_transactions,
            last_synced_at=last_synced_at,
        )
