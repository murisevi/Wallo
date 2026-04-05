"""Unit tests for BankingService.

All Enable Banking HTTP calls are mocked via AsyncMock so no network or
database is needed — the service logic is tested in isolation.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.banking.models import BankAccount, BankConnection
from app.banking.service import BankingService, _pick_balance

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(
    scalar_one_or_none: object = None,
    scalars_all: list | None = None,
) -> AsyncMock:
    """Return a minimal async SQLAlchemy session mock.

    SQLAlchemy session methods like add/delete are synchronous — we override
    them with plain MagicMock to avoid "coroutine never awaited" warnings.
    """
    db = AsyncMock()
    db.add = MagicMock()  # session.add() is synchronous in SQLAlchemy
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalars.return_value.all.return_value = scalars_all or []
    db.execute.return_value = result
    return db


def _make_eb() -> AsyncMock:
    """Return a minimal Enable Banking client mock."""
    return AsyncMock()


def _make_service(
    db: AsyncMock | None = None,
    eb: AsyncMock | None = None,
) -> BankingService:
    return BankingService(db=db or _make_db(), eb_client=eb or _make_eb())


# ---------------------------------------------------------------------------
# _pick_balance — pure logic, no mocks needed
# ---------------------------------------------------------------------------


class TestPickBalance:
    def test_prefers_itav(self) -> None:
        balances = [
            {"balance_type": "CLBD", "amount": Decimal("100.00"), "currency": "EUR"},
            {"balance_type": "ITAV", "amount": Decimal("95.50"), "currency": "EUR"},
            {"balance_type": "XPCD", "amount": Decimal("90.00"), "currency": "EUR"},
        ]
        amount, btype = _pick_balance(balances)
        assert amount == Decimal("95.50")
        assert btype == "ITAV"

    def test_falls_back_to_xpcd_when_no_itav(self) -> None:
        balances = [
            {"balance_type": "CLBD", "amount": Decimal("100.00"), "currency": "EUR"},
            {"balance_type": "XPCD", "amount": Decimal("90.00"), "currency": "EUR"},
        ]
        amount, btype = _pick_balance(balances)
        assert amount == Decimal("90.00")
        assert btype == "XPCD"

    def test_falls_back_to_clbd_as_last_resort(self) -> None:
        balances = [
            {"balance_type": "CLBD", "amount": Decimal("80.00"), "currency": "EUR"},
        ]
        amount, btype = _pick_balance(balances)
        assert amount == Decimal("80.00")
        assert btype == "CLBD"

    def test_empty_list_returns_none(self) -> None:
        amount, btype = _pick_balance([])
        assert amount is None
        assert btype is None

    def test_first_entry_used_when_type_unknown(self) -> None:
        balances = [
            {"balance_type": "UNKN", "amount": Decimal("50.00"), "currency": "EUR"},
        ]
        amount, btype = _pick_balance(balances)
        assert amount == Decimal("50.00")
        assert btype == "UNKN"


# ---------------------------------------------------------------------------
# BankingService.list_aspsps
# ---------------------------------------------------------------------------


class TestListAspsps:
    async def test_returns_bank_list(self) -> None:
        eb = _make_eb()
        eb.list_aspsps.return_value = [
            {"name": "BBVA", "country": "ES", "logo": None},
            {"name": "Santander", "country": "ES", "logo": None},
        ]
        svc = _make_service(eb=eb)

        result = await svc.list_aspsps("es")

        eb.list_aspsps.assert_called_once_with("ES")
        assert len(result) == 2
        assert result[0]["name"] == "BBVA"

    async def test_uppercases_country_code(self) -> None:
        eb = _make_eb()
        eb.list_aspsps.return_value = []
        svc = _make_service(eb=eb)

        await svc.list_aspsps("es")

        eb.list_aspsps.assert_called_once_with("ES")


# ---------------------------------------------------------------------------
# BankingService.initiate_connection
# ---------------------------------------------------------------------------


class TestInitiateConnection:
    async def test_returns_url_and_authorization_id(self) -> None:
        eb = _make_eb()
        eb.start_authorization.return_value = {
            "url": "https://sandbox.enablebanking.com/connect?session=abc",
            "authorization_id": "auth-123",
        }
        db = _make_db()
        svc = _make_service(db=db, eb=eb)

        result = await svc.initiate_connection(
            user_id=uuid.uuid4(),
            bank_name="BBVA",
            bank_country="es",
        )

        assert result["url"] == "https://sandbox.enablebanking.com/connect?session=abc"
        assert result["authorization_id"] == "auth-123"

    async def test_persists_pending_connection_to_db(self) -> None:
        eb = _make_eb()
        eb.start_authorization.return_value = {
            "url": "https://example.com",
            "authorization_id": "auth-456",
        }
        db = _make_db()
        svc = _make_service(db=db, eb=eb)
        user_id = uuid.uuid4()

        await svc.initiate_connection(
            user_id=user_id,
            bank_name="BBVA",
            bank_country="ES",
        )

        # A BankConnection must have been added to the session
        db.add.assert_called_once()
        added: BankConnection = db.add.call_args[0][0]
        assert isinstance(added, BankConnection)
        assert added.status == "pending"
        assert added.user_id == user_id
        assert added.bank_name == "BBVA"
        assert added.authorization_id == "auth-456"

    async def test_uppercases_bank_country(self) -> None:
        eb = _make_eb()
        eb.start_authorization.return_value = {
            "url": "https://example.com",
            "authorization_id": "x",
        }
        db = _make_db()
        svc = _make_service(db=db, eb=eb)

        await svc.initiate_connection(
            user_id=uuid.uuid4(),
            bank_name="BBVA",
            bank_country="es",
        )

        _, kwargs = eb.start_authorization.call_args
        assert kwargs["bank_country"] == "ES"


# ---------------------------------------------------------------------------
# BankingService.complete_connection
# ---------------------------------------------------------------------------


def _mock_account_row(
    uid: str = "acc-uid-1",
    iban: str = "ES12 3456 7890",
    currency: str = "EUR",
) -> dict:
    return {
        "uid": uid,
        "iban": iban,
        "name": "Cuenta corriente",
        "currency": currency,
        "cash_account_type": "CACC",
    }


class TestCompleteConnection:
    async def test_activates_pending_connection(self) -> None:
        pending_conn = BankConnection(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            bank_name="BBVA",
            bank_country="ES",
            status="pending",
        )

        # complete_connection calls execute() twice:
        #  1. find the pending BankConnection
        #  2. check for an existing BankAccount by external_uid (should be None)
        result_conn = MagicMock()
        result_conn.scalar_one_or_none.return_value = pending_conn

        result_no_account = MagicMock()
        result_no_account.scalar_one_or_none.return_value = None

        db = AsyncMock()

        # Simulate DB flush assigning a UUID to newly-added ORM objects
        def _assign_id(obj: object) -> None:
            if isinstance(obj, BankAccount) and obj.id is None:
                obj.id = uuid.uuid4()

        db.add = MagicMock(side_effect=_assign_id)
        db.execute.side_effect = [result_conn, result_no_account]

        eb = _make_eb()
        eb.create_session.return_value = {
            "session_id": "sess-abc",
            "accounts": [_mock_account_row()],
            "aspsp": {"name": "BBVA", "country": "ES"},
            "access": {"valid_until": "2026-12-31T00:00:00.000Z"},
        }
        eb.get_account_balances.return_value = [
            {"balance_type": "ITAV", "amount": Decimal("1500.00"), "currency": "EUR"},
        ]

        svc = BankingService(db=db, eb_client=eb)

        mock_sync = AsyncMock(return_value=0)
        with patch("app.transactions.service.sync_transactions", new=mock_sync):
            accounts = await svc.complete_connection(
                user_id=pending_conn.user_id,
                code="oauth-code-xyz",
            )

        assert pending_conn.status == "active"
        assert pending_conn.session_id == "sess-abc"
        assert len(accounts) == 1
        eb.create_session.assert_called_once_with("oauth-code-xyz")

    async def test_creates_connection_when_no_pending_exists(self) -> None:
        """complete_connection should recover gracefully if no pending row exists."""
        db = _make_db(scalar_one_or_none=None)

        eb = _make_eb()
        eb.create_session.return_value = {
            "session_id": "sess-new",
            "accounts": [],
            "aspsp": {"name": "Santander", "country": "ES"},
            "access": {},
        }

        svc = BankingService(db=db, eb_client=eb)

        mock_sync = AsyncMock(return_value=0)
        with patch("app.transactions.service.sync_transactions", new=mock_sync):
            accounts = await svc.complete_connection(
                user_id=uuid.uuid4(),
                code="code-no-pending",
            )

        assert accounts == []
        # A new BankConnection must have been added
        assert db.add.called


# ---------------------------------------------------------------------------
# BankingService.sync_balances
# ---------------------------------------------------------------------------


class TestSyncBalances:
    async def test_updates_balance_for_each_account(self) -> None:
        user_id = uuid.uuid4()
        account = BankAccount(
            id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            user_id=user_id,
            external_uid="uid-1",
            currency="EUR",
        )
        db = _make_db(scalars_all=[account])
        eb = _make_eb()
        eb.get_account_balances.return_value = [
            {"balance_type": "ITAV", "amount": Decimal("999.99"), "currency": "EUR"},
        ]
        svc = _make_service(db=db, eb=eb)

        await svc.sync_balances(user_id)

        assert account.balance_amount == Decimal("999.99")
        assert account.balance_type == "ITAV"
        assert account.last_synced_at is not None
        eb.get_account_balances.assert_called_once_with("uid-1")

    async def test_skips_account_when_balance_fetch_fails(self) -> None:
        """A failing balance fetch should be swallowed, not propagated."""
        user_id = uuid.uuid4()
        account = BankAccount(
            id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            user_id=user_id,
            external_uid="uid-fail",
            currency="EUR",
        )
        db = _make_db(scalars_all=[account])
        eb = _make_eb()
        eb.get_account_balances.side_effect = RuntimeError("network error")
        svc = _make_service(db=db, eb=eb)

        # Should not raise — errors are caught and logged
        await svc.sync_balances(user_id)

        assert account.balance_amount is None


# ---------------------------------------------------------------------------
# BankingService.disconnect_bank
# ---------------------------------------------------------------------------


class TestDisconnectBank:
    async def test_deletes_connection(self) -> None:
        user_id = uuid.uuid4()
        connection_id = uuid.uuid4()
        connection = BankConnection(
            id=connection_id,
            user_id=user_id,
            bank_name="BBVA",
            bank_country="ES",
            status="active",
        )
        db = _make_db(scalar_one_or_none=connection)
        svc = _make_service(db=db)

        await svc.disconnect_bank(user_id=user_id, connection_id=connection_id)

        db.delete.assert_called_once_with(connection)

    async def test_raises_404_when_not_found(self) -> None:
        from fastapi import HTTPException

        db = _make_db(scalar_one_or_none=None)
        svc = _make_service(db=db)

        with pytest.raises(HTTPException) as exc_info:
            await svc.disconnect_bank(user_id=uuid.uuid4(), connection_id=uuid.uuid4())

        assert exc_info.value.status_code == 404
