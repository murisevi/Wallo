"""Banking domain service — orchestrates Enable Banking client + DB."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.client import EnableBankingClient
from app.banking.models import BankAccount, BankConnection
from app.banking.schemas import BankAccountResponse, BankConnectionResponse
from app.config import settings

logger = logging.getLogger(__name__)

# Balance type priority: best → worst
_BALANCE_PRIORITY = ["ITAV", "XPCD", "CLBD"]

# Banks that are not directly available in the Enable Banking SANDBOX are mapped
# to a sandbox ASPSP that can process the OAuth flow on their behalf.
# This map is ONLY applied when ENABLE_BANKING_ENVIRONMENT=sandbox.
# In production every bank name is sent as-is to Enable Banking.
# Key: (display_name_lower, country_upper)  →  (aspsp_name, aspsp_country)
_SANDBOX_ASPSP_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("banco santander", "ES"): ("Mock ASPSP", "ES"),
}


def _pick_balance(
    balances: list[dict],
) -> tuple[Decimal | None, str | None]:
    """Return (amount, balance_type) using ITAV > XPCD > CLBD priority."""
    by_type = {b["balance_type"]: b for b in balances if b.get("balance_type")}
    for bt in _BALANCE_PRIORITY:
        if bt in by_type:
            bal = by_type[bt]
            return bal.get("amount"), bt
    # Fallback: first available
    if balances:
        bal = balances[0]
        return bal.get("amount"), bal.get("balance_type")
    return None, None


class BankingService:
    def __init__(self, db: AsyncSession, eb_client: EnableBankingClient) -> None:
        self._db = db
        self._eb = eb_client

    # ── ASPSP listing ─────────────────────────────────────────────────────────

    async def list_aspsps(self, country: str = "es") -> list[dict]:
        """List available banks from Enable Banking for a country."""
        return await self._eb.list_aspsps(country.upper())

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def get_connections(
        self, user_id: uuid.UUID
    ) -> list[BankConnectionResponse]:
        """Return all non-disconnected bank connections for a user, with account stats."""
        conn_result = await self._db.execute(
            select(BankConnection).where(
                BankConnection.user_id == user_id,
                BankConnection.status != "disconnected",
            )
        )
        connections = conn_result.scalars().all()

        responses: list[BankConnectionResponse] = []
        for conn in connections:
            acc_result = await self._db.execute(
                select(BankAccount).where(BankAccount.connection_id == conn.id)
            )
            accounts = acc_result.scalars().all()
            last_synced_at = max(
                (a.last_synced_at for a in accounts if a.last_synced_at),
                default=None,
            )
            responses.append(
                BankConnectionResponse(
                    id=conn.id,
                    bank_name=conn.bank_name,
                    bank_country=conn.bank_country,
                    bank_logo=conn.bank_logo,
                    status=conn.status,
                    accounts_count=len(accounts),
                    last_synced_at=last_synced_at,
                    created_at=conn.created_at,
                )
            )
        return responses

    async def initiate_connection(
        self,
        user_id: uuid.UUID,
        bank_name: str,
        bank_country: str,
        redirect_url: str | None = None,
    ) -> dict[str, str]:
        """Start PSD2 authorization. Persists a pending BankConnection.

        Returns:
            {"url": "...", "authorization_id": "..."}
        """
        effective_redirect_url = redirect_url or settings.enable_banking_redirect_url
        country_upper = bank_country.upper()

        # Resolve sandbox proxy: some banks are not in the sandbox catalogue but
        # can be tested via Mock ASPSP.  We keep the user-facing name in the DB
        # and only use the proxy name for the Enable Banking API call.
        is_sandbox = settings.enable_banking_environment.lower() == "sandbox"
        aspsp_key = (bank_name.lower(), country_upper)
        if is_sandbox and aspsp_key in _SANDBOX_ASPSP_MAP:
            eb_name, eb_country = _SANDBOX_ASPSP_MAP[aspsp_key]
            logger.info(
                "Sandbox proxy: routing '%s' → '%s' for Enable Banking API call",
                bank_name,
                eb_name,
            )
        else:
            eb_name, eb_country = bank_name, country_upper

        result = await self._eb.start_authorization(
            bank_name=eb_name,
            bank_country=eb_country,
            redirect_url=effective_redirect_url,
            state=str(user_id),
        )
        connection = BankConnection(
            user_id=user_id,
            bank_name=bank_name,        # store display name, not proxy name
            bank_country=country_upper,
            authorization_id=result["authorization_id"],
            status="pending",
        )
        self._db.add(connection)
        await self._db.flush()
        logger.info(
            "Initiated bank connection for user %s → %s %s (auth_id=%s)",
            user_id,
            bank_name,
            bank_country,
            result["authorization_id"],
        )
        return {
            "url": result["url"],
            "authorization_id": result["authorization_id"],
        }

    async def complete_connection(
        self,
        user_id: uuid.UUID,
        code: str,
    ) -> list[BankAccountResponse]:
        """Exchange OAuth code for a session; create accounts + fetch balances.

        Matches the most recent pending BankConnection for this user.
        """
        session_data = await self._eb.create_session(code)
        session_id: str = session_data["session_id"]
        accounts_data: list[dict] = session_data.get("accounts", [])
        aspsp: dict = session_data.get("aspsp") or {}
        access: dict = session_data.get("access") or {}

        # Parse session validity
        session_valid_until: datetime | None = None
        valid_until_str = access.get("valid_until")
        if valid_until_str:
            try:
                session_valid_until = datetime.fromisoformat(
                    valid_until_str.replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning(
                    "Could not parse session valid_until: %s",
                    valid_until_str,
                )

        # Find the most recent pending connection for this user
        result = await self._db.execute(
            select(BankConnection)
            .where(
                BankConnection.user_id == user_id,
                BankConnection.status == "pending",
            )
            .order_by(BankConnection.created_at.desc())
            .limit(1)
        )
        connection = result.scalar_one_or_none()

        if connection is None:
            # No pending connection found — create one from session metadata
            connection = BankConnection(
                user_id=user_id,
                bank_name=aspsp.get("name", "Unknown"),
                bank_country=aspsp.get("country", ""),
                status="pending",
            )
            self._db.add(connection)
            await self._db.flush()

        # Activate the connection
        connection.session_id = session_id
        connection.status = "active"
        connection.session_valid_until = session_valid_until
        if aspsp.get("name"):
            connection.bank_name = aspsp["name"]
        if aspsp.get("country"):
            connection.bank_country = aspsp["country"]
        await self._db.flush()

        # Create/update accounts and fetch their balances
        created_accounts: list[BankAccount] = []
        for acc_data in accounts_data:
            uid = acc_data["uid"]

            # Upsert by external_uid (account may already exist from a re-connect)
            existing = await self._db.execute(
                select(BankAccount).where(BankAccount.external_uid == uid)
            )
            account = existing.scalar_one_or_none()

            if account is None:
                account = BankAccount(
                    connection_id=connection.id,
                    user_id=user_id,
                    external_uid=uid,
                    iban=acc_data.get("iban"),
                    name=acc_data.get("name"),
                    account_type=acc_data.get("cash_account_type"),
                    currency=acc_data.get("currency") or "EUR",
                )
                self._db.add(account)
                await self._db.flush()

            await self._fetch_and_store_balance(account)
            created_accounts.append(account)

        # Sync initial transaction history for each new account
        from app.transactions.service import sync_transactions

        for account in created_accounts:
            try:
                n = await sync_transactions(self._db, self._eb, account)
                logger.info(
                    "Initial transaction sync for account %s: %d new",
                    account.external_uid,
                    n,
                )
            except Exception:
                logger.warning(
                    "Failed to sync transactions for account %s — skipping",
                    account.external_uid,
                    exc_info=True,
                )

        await self._db.flush()
        logger.info(
            "Completed connection for user %s — session %s, %d accounts",
            user_id,
            session_id,
            len(created_accounts),
        )
        return [BankAccountResponse.model_validate(a) for a in created_accounts]

    # ── Balance sync ──────────────────────────────────────────────────────────

    async def sync_balances(self, user_id: uuid.UUID) -> None:
        """Re-fetch and store latest balances for all active accounts.

        Kept for backwards compatibility — prefer ``sync_all`` which also
        refreshes transactions.
        """
        result = await self._db.execute(
            select(BankAccount)
            .join(BankConnection, BankAccount.connection_id == BankConnection.id)
            .where(
                BankAccount.user_id == user_id,
                BankConnection.status != "disconnected",
            )
        )
        accounts = result.scalars().all()
        for account in accounts:
            await self._fetch_and_store_balance(account)
        await self._db.flush()
        logger.info("Synced balances for user %s (%d accounts)", user_id, len(accounts))

    async def sync_all(
        self,
        user_id: uuid.UUID,
        psu_ip: str | None = None,
        psu_user_agent: str | None = None,
    ) -> None:
        """Refresh balances AND transactions for all active accounts.

        Pass ``psu_ip`` and ``psu_user_agent`` when the sync is triggered
        explicitly by the user — Enable Banking lifts the 4/day background
        fetch rate limit when PSU headers are present.
        """
        from app.transactions.service import sync_transactions

        result = await self._db.execute(
            select(BankAccount)
            .join(BankConnection, BankAccount.connection_id == BankConnection.id)
            .where(
                BankAccount.user_id == user_id,
                BankConnection.status != "disconnected",
            )
        )
        accounts = result.scalars().all()

        for account in accounts:
            await self._fetch_and_store_balance(
                account, psu_ip=psu_ip, psu_user_agent=psu_user_agent
            )
            try:
                n = await sync_transactions(
                    self._db,
                    self._eb,
                    account,
                    psu_ip=psu_ip,
                    psu_user_agent=psu_user_agent,
                )
                logger.info(
                    "Transaction sync for account %s: %d new",
                    account.external_uid,
                    n,
                )
            except Exception:
                logger.warning(
                    "Failed to sync transactions for account %s — skipping",
                    account.external_uid,
                    exc_info=True,
                )

        await self._db.flush()
        logger.info(
            "Full sync (balances + transactions) for user %s (%d accounts)",
            user_id,
            len(accounts),
        )

    async def _fetch_and_store_balance(
        self,
        account: BankAccount,
        psu_ip: str | None = None,
        psu_user_agent: str | None = None,
    ) -> None:
        """Fetch balances from Enable Banking and update the account row."""
        try:
            balances = await self._eb.get_account_balances(
                account.external_uid,
                psu_ip=psu_ip,
                psu_user_agent=psu_user_agent,
            )
            amount, bal_type = _pick_balance(balances)
            account.balance_amount = amount
            account.balance_type = bal_type
            account.last_synced_at = datetime.now(timezone.utc)
        except Exception:
            logger.warning(
                "Failed to fetch balances for account %s — skipping",
                account.external_uid,
                exc_info=True,
            )

    # ── Account queries ───────────────────────────────────────────────────────

    async def get_user_accounts(self, user_id: uuid.UUID) -> list[BankAccountResponse]:
        """Return all BankAccounts belonging to a user on active connections."""
        result = await self._db.execute(
            select(BankAccount)
            .join(BankConnection, BankAccount.connection_id == BankConnection.id)
            .where(
                BankAccount.user_id == user_id,
                BankConnection.status != "disconnected",
            )
        )
        accounts = result.scalars().all()
        return [BankAccountResponse.model_validate(a) for a in accounts]

    # ── Disconnection ─────────────────────────────────────────────────────────

    async def disconnect_bank(
        self, user_id: uuid.UUID, connection_id: uuid.UUID
    ) -> None:
        """Soft-delete a BankConnection (sets status=disconnected, preserves history)."""
        result = await self._db.execute(
            select(BankConnection).where(
                BankConnection.id == connection_id,
                BankConnection.user_id == user_id,
            )
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank connection not found",
            )
        connection.status = "disconnected"
        await self._db.flush()
        logger.info(
            "Soft-disconnected bank connection %s for user %s", connection_id, user_id
        )
