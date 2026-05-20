"""Integration tests for GET /dashboard/.

The Enable Banking client is mocked so no real .pem keys are needed.
Tests verify balance aggregation, account listing, recent transactions,
and multi-currency handling.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.banking.router import get_eb_client
from app.main import app

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_AUTH = {
    "url": "https://connect.enablebanking.com/mock",
    "authorization_id": "auth-dash",
}

MOCK_SESSION_EUR = {
    "session_id": "session-dash-eur",
    "accounts": [
        {
            "uid": "acc-dash-001",
            "iban": "ES1234567890123456789012",
            "name": "Cuenta Corriente",
            "currency": "EUR",
            "cash_account_type": "CACC",
        }
    ],
    "aspsp": {"name": "Banco Mock", "country": "ES"},
    "access": {"valid_until": "2026-10-01T00:00:00.000Z"},
}

MOCK_SESSION_USD = {
    "session_id": "session-dash-usd",
    "accounts": [
        {
            "uid": "acc-dash-002",
            "iban": "US12345678901234567890",
            "name": "USD Account",
            "currency": "USD",
            "cash_account_type": "CACC",
        }
    ],
    "aspsp": {"name": "US Bank", "country": "US"},
    "access": {"valid_until": "2026-10-01T00:00:00.000Z"},
}

MOCK_BALANCES_EUR = [
    {"balance_type": "ITAV", "amount": Decimal("2000.00"), "currency": "EUR"},
]
MOCK_BALANCES_USD = [
    {"balance_type": "ITAV", "amount": Decimal("500.00"), "currency": "USD"},
]

MOCK_TRANSACTIONS = [
    {
        "entry_reference": f"ref-{i}",
        "booking_date": f"2026-03-{15 - i:02d}",
        "value_date": None,
        "credit_debit_indicator": "CRDT",
        "status": "BOOK",
        "amount": Decimal(f"{100 * (i + 1)}.00"),
        "currency": "EUR",
        "debtor_name": f"Payer {i}",
        "creditor_name": None,
        "remittance_information": f"Transfer {i}",
        "bank_transaction_code": None,
        "transaction_id": None,
        "transaction_date": None,
    }
    for i in range(7)  # 7 transactions — dashboard shows only 5
]


def make_mock_eb_client(session_data: dict, balances: list) -> MagicMock:
    mock = MagicMock()
    mock.list_aspsps = AsyncMock(return_value=[])
    mock.start_authorization = AsyncMock(return_value=MOCK_AUTH)
    mock.create_session = AsyncMock(return_value=session_data)
    mock.get_account_balances = AsyncMock(return_value=balances)
    mock.get_all_transactions = AsyncMock(return_value=MOCK_TRANSACTIONS)
    return mock


@pytest.fixture
def mock_eur_client() -> MagicMock:
    return make_mock_eb_client(MOCK_SESSION_EUR, MOCK_BALANCES_EUR)


@pytest.fixture
def mock_usd_client() -> MagicMock:
    return make_mock_eb_client(MOCK_SESSION_USD, MOCK_BALANCES_USD)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER = {"email": "dash_user@example.com", "name": "Dash User", "password": "DashPass1!"}


async def register_and_login(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/register", json=USER)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": USER["password"]},
    )
    return resp.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def connect_bank(
    client: AsyncClient, token: str, mock_client: MagicMock, code: str = "code-dash"
) -> None:
    app.dependency_overrides[get_eb_client] = lambda: mock_client
    headers = auth(token)
    await client.post(
        "/api/v1/banking/connect",
        json={"bank_name": "Mock Bank", "bank_country": "ES"},
        headers=headers,
    )
    await client.post(
        "/api/v1/banking/callback",
        json={"code": code},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_empty_state(client: AsyncClient) -> None:
    """No connected accounts → zero balance, empty lists."""
    token = await register_and_login(client)
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_balance"] == "0"
    assert data["reserved_for_goals"] == "0"
    assert data["available_balance"] == "0"
    assert data["currency"] == "EUR"
    assert data["accounts"] == []
    assert data["recent_transactions"] == []
    assert data["last_synced_at"] is None


@pytest.mark.asyncio
async def test_dashboard_total_balance(
    client: AsyncClient,
    mock_eur_client: MagicMock,
) -> None:
    """Total balance equals the sum of EUR account balances."""
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_balance"]) == Decimal("2000.00")
    assert Decimal(data["reserved_for_goals"]) == Decimal("0")
    assert Decimal(data["available_balance"]) == Decimal("2000.00")
    assert data["currency"] == "EUR"


@pytest.mark.asyncio
async def test_dashboard_available_balance_subtracts_active_goal_reserves(
    client: AsyncClient,
    mock_eur_client: MagicMock,
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)
    headers = auth(token)

    goal_resp = await client.post(
        "/api/v1/goals/",
        json={"name": "Viaje", "target_amount": "1000"},
        headers=headers,
    )
    goal_id = goal_resp.json()["id"]
    await client.post(
        f"/api/v1/goals/{goal_id}/contributions",
        json={"amount": "500"},
        headers=headers,
    )

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=headers)
    app.dependency_overrides.pop(get_eb_client, None)

    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_balance"]) == Decimal("2000.00")
    assert Decimal(data["reserved_for_goals"]) == Decimal("500.00")
    assert Decimal(data["available_balance"]) == Decimal("1500.00")


@pytest.mark.asyncio
async def test_dashboard_accounts_have_bank_metadata(
    client: AsyncClient, mock_eur_client: MagicMock
) -> None:
    """AccountSummary includes bank_name from the connection."""
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    accounts = resp.json()["accounts"]
    assert len(accounts) == 1
    acc = accounts[0]
    assert acc["bank_name"] == "Banco Mock"
    assert acc["iban"] == "ES1234567890123456789012"
    assert acc["name"] == "Cuenta Corriente"
    assert acc["currency"] == "EUR"
    assert Decimal(acc["balance"]) == Decimal("2000.00")


@pytest.mark.asyncio
async def test_dashboard_recent_transactions_capped_at_5(
    client: AsyncClient, mock_eur_client: MagicMock
) -> None:
    """Dashboard returns at most 5 transactions even when more exist."""
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)  # syncs 7 transactions

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    assert len(resp.json()["recent_transactions"]) == 5


@pytest.mark.asyncio
async def test_dashboard_recent_transactions_ordered_newest_first(
    client: AsyncClient, mock_eur_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    dates = [t["date"] for t in resp.json()["recent_transactions"]]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_dashboard_last_synced_at_populated(
    client: AsyncClient, mock_eur_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    assert resp.json()["last_synced_at"] is not None


@pytest.mark.asyncio
async def test_dashboard_multi_currency_excludes_foreign_from_total(
    client: AsyncClient, mock_eur_client: MagicMock, mock_usd_client: MagicMock
) -> None:
    """USD account balance must NOT be added to the EUR total."""
    token = await register_and_login(client)

    # Connect EUR account
    await connect_bank(client, token, mock_eur_client, code="code-eur")

    # Connect USD account
    await connect_bank(client, token, mock_usd_client, code="code-usd")

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    data = resp.json()
    # Both accounts listed
    assert len(data["accounts"]) == 2
    # Only EUR balance (2000) in total — USD (500) excluded
    assert Decimal(data["total_balance"]) == Decimal("2000.00")
    assert Decimal(data["available_balance"]) == Decimal("2000.00")
    assert data["currency"] == "EUR"


@pytest.mark.asyncio
async def test_dashboard_account_iban_in_recent_transactions(
    client: AsyncClient, mock_eur_client: MagicMock
) -> None:
    """Each recent transaction carries the IBAN of its account."""
    token = await register_and_login(client)
    await connect_bank(client, token, mock_eur_client)

    app.dependency_overrides[get_eb_client] = lambda: mock_eur_client
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))
    app.dependency_overrides.pop(get_eb_client, None)

    for txn in resp.json()["recent_transactions"]:
        assert txn["account_iban"] == "ES1234567890123456789012"


@pytest.mark.asyncio
async def test_dashboard_no_accounts_no_transactions(client: AsyncClient) -> None:
    """New user with no connections sees sensible defaults."""
    token = await register_and_login(client)
    resp = await client.get("/api/v1/dashboard/", headers=auth(token))

    data = resp.json()
    assert data["total_balance"] == "0"
    assert data["reserved_for_goals"] == "0"
    assert data["available_balance"] == "0"
    assert data["recent_transactions"] == []
    assert data["last_synced_at"] is None
