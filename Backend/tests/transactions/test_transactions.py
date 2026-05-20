"""Integration tests for the transactions router + service.

The Enable Banking client is mocked so no real HTTP calls or .pem keys are
needed.  Tests exercise the full FastAPI stack (auth → banking → transactions).
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
    "authorization_id": "auth-txn-test",
}

MOCK_SESSION = {
    "session_id": "session-txn-test",
    "accounts": [
        {
            "uid": "acc-txn-001",
            "iban": "ES7620770024003102575766",
            "name": "Cuenta Nómina",
            "currency": "EUR",
            "cash_account_type": "CACC",
        }
    ],
    "aspsp": {"name": "Mock Bank", "country": "ES"},
    "access": {"valid_until": "2026-10-01T00:00:00.000Z"},
}

MOCK_BALANCES = [
    {"balance_type": "ITAV", "amount": Decimal("3000.00"), "currency": "EUR"},
]

MOCK_TRANSACTIONS = [
    {
        "entry_reference": "ref-001",
        "booking_date": "2026-03-15",
        "value_date": "2026-03-15",
        "credit_debit_indicator": "CRDT",
        "status": "BOOK",
        "amount": Decimal("500.00"),
        "currency": "EUR",
        "debtor_name": "Empresa SA",
        "creditor_name": None,
        "remittance_information": ["Salario Marzo 2026"],
        "bank_transaction_code": None,
        "merchant_category_code": None,
        "transaction_id": None,
        "transaction_date": None,
    },
    {
        "entry_reference": "ref-002",
        "booking_date": "2026-03-10",
        "value_date": "2026-03-10",
        "credit_debit_indicator": "DBIT",
        "status": "BOOK",
        "amount": Decimal("45.50"),
        "currency": "EUR",
        "debtor_name": None,
        "creditor_name": "Mercadona",
        "remittance_information": "Compra supermercado",
        "bank_transaction_code": "PMNT",
        "merchant_category_code": "5411",
        "transaction_id": None,
        "transaction_date": None,
    },
    {
        "entry_reference": None,  # No reference — always insertable
        "booking_date": "2026-03-05",
        "value_date": None,
        "credit_debit_indicator": "DBIT",
        "status": "PDNG",
        "amount": Decimal("12.99"),
        "currency": "EUR",
        "debtor_name": None,
        "creditor_name": "Netflix",
        "remittance_information": None,
        "bank_transaction_code": None,
        "merchant_category_code": None,
        "transaction_id": None,
        "transaction_date": None,
    },
]


def make_mock_eb_client(transactions: list | None = None) -> MagicMock:
    mock = MagicMock()
    mock.list_aspsps = AsyncMock(return_value=[])
    mock.start_authorization = AsyncMock(return_value=MOCK_AUTH)
    mock.create_session = AsyncMock(return_value=MOCK_SESSION)
    mock.get_account_balances = AsyncMock(return_value=MOCK_BALANCES)
    mock.get_all_transactions = AsyncMock(
        return_value=transactions if transactions is not None else MOCK_TRANSACTIONS
    )
    return mock


@pytest.fixture(autouse=True)
def override_eb_client():
    mock_client = make_mock_eb_client()
    app.dependency_overrides[get_eb_client] = lambda: mock_client
    yield mock_client
    app.dependency_overrides.pop(get_eb_client, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER = {"email": "txn_user@example.com", "name": "Txn User", "password": "TxnPass1!"}


async def register_and_login(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/register", json=USER)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": USER["password"]},
    )
    return resp.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def connect_bank(client: AsyncClient, token: str) -> None:
    """Helper: initiate + complete a bank connection (populates transactions)."""
    headers = auth(token)
    await client.post(
        "/api/v1/banking/connect",
        json={"bank_name": "Mock Bank", "bank_country": "ES"},
        headers=headers,
    )
    await client.post(
        "/api/v1/banking/callback",
        json={"code": "code-txn"},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Tests — GET /transactions/ basic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_transactions_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/transactions/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_transactions_empty_before_connection(client: AsyncClient) -> None:
    token = await register_and_login(client)
    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["transactions"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["page_size"] == 20


@pytest.mark.asyncio
async def test_list_transactions_after_connection(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["transactions"]) == 3


# ---------------------------------------------------------------------------
# Tests — signed amounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crdt_transaction_is_positive(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    txn_list = resp.json()["transactions"]
    crdt = next(t for t in txn_list if t["credit_debit_indicator"] == "CRDT")
    assert Decimal(crdt["amount"]) > 0


@pytest.mark.asyncio
async def test_dbit_transaction_is_negative(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    dbit_txns = [
        t for t in resp.json()["transactions"] if t["credit_debit_indicator"] == "DBIT"
    ]
    assert all(Decimal(t["amount"]) < 0 for t in dbit_txns)


# ---------------------------------------------------------------------------
# Tests — deduplication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_duplicate_on_resync(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    """Reconnecting with the same transactions must not create duplicates."""
    token = await register_and_login(client)
    await connect_bank(client, token)

    # Reconnect (callback with a different code but same mock transactions)
    headers = auth(token)
    await client.post(
        "/api/v1/banking/connect",
        json={"bank_name": "Mock Bank", "bank_country": "ES"},
        headers=headers,
    )
    await client.post(
        "/api/v1/banking/callback",
        json={"code": "code-txn-2"},
        headers=headers,
    )

    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    # ref-001 and ref-002 must not be duplicated; the None-reference one may repeat
    txns = resp.json()["transactions"]
    ref_001_count = sum(1 for t in txns if t.get("description") == "Salario Marzo 2026")
    assert ref_001_count == 1


# ---------------------------------------------------------------------------
# Tests — pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_page_size(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?page=1&page_size=2", headers=auth(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["transactions"]) == 2
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2


@pytest.mark.asyncio
async def test_pagination_second_page(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?page=2&page_size=2", headers=auth(token)
    )
    body = resp.json()
    assert len(body["transactions"]) == 1


# ---------------------------------------------------------------------------
# Tests — ordering (date DESC)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transactions_ordered_by_date_desc(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    dates = [t["date"] for t in resp.json()["transactions"]]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# Tests — filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_by_date_from(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?date_from=2026-03-10", headers=auth(token)
    )
    body = resp.json()
    assert all(t["date"] >= "2026-03-10" for t in body["transactions"])
    assert body["total"] == 2  # ref-001 (2026-03-15) and ref-002 (2026-03-10)


@pytest.mark.asyncio
async def test_filter_by_date_to(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?date_to=2026-03-10", headers=auth(token)
    )
    body = resp.json()
    assert all(t["date"] <= "2026-03-10" for t in body["transactions"])


@pytest.mark.asyncio
async def test_search_by_description(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/?search=Salario", headers=auth(token))
    body = resp.json()
    assert body["total"] == 1
    assert "Salario" in body["transactions"][0]["description"]


@pytest.mark.asyncio
async def test_search_by_creditor_name(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?search=Mercadona", headers=auth(token)
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["transactions"][0]["creditor_name"] == "Mercadona"


@pytest.mark.asyncio
async def test_filter_by_account_id(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    # Get account id
    accounts_resp = await client.get("/api/v1/banking/accounts", headers=auth(token))
    account_id = accounts_resp.json()[0]["id"]

    resp = await client.get(
        f"/api/v1/transactions/?account_id={account_id}", headers=auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


@pytest.mark.asyncio
async def test_filter_account_id_not_owned_returns_empty(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    """Filtering by another user's account returns empty, not 403."""
    token = await register_and_login(client)
    # Register a second user to get a different account
    import uuid

    resp = await client.get(
        f"/api/v1/transactions/?account_id={uuid.uuid4()}", headers=auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Tests — remittance_information parsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remittance_list_joined_as_description(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/?search=Salario", headers=auth(token))
    # The mock has remittance_information as a list ["Salario Marzo 2026"]
    assert resp.json()["transactions"][0]["description"] == "Salario Marzo 2026"


@pytest.mark.asyncio
async def test_remittance_string_stored_as_description(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?search=supermercado", headers=auth(token)
    )
    assert resp.json()["transactions"][0]["description"] == "Compra supermercado"


# ---------------------------------------------------------------------------
# Tests — account_iban in response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_iban_present_in_response(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get("/api/v1/transactions/", headers=auth(token))
    for txn in resp.json()["transactions"]:
        assert txn["account_iban"] == "ES7620770024003102575766"


@pytest.mark.asyncio
async def test_bank_detail_fields_present_in_response(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    token = await register_and_login(client)
    await connect_bank(client, token)

    resp = await client.get(
        "/api/v1/transactions/?search=supermercado",
        headers=auth(token),
    )
    txn = resp.json()["transactions"][0]

    assert txn["entry_reference"] == "ref-002"
    assert txn["bank_transaction_code"] == "PMNT"
    assert txn["merchant_category_code"] == "5411"


# ---------------------------------------------------------------------------
# Tests — transaction sync failure tolerance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transaction_sync_failure_does_not_abort_connection(
    client: AsyncClient, override_eb_client: MagicMock
) -> None:
    """If transaction sync fails, the bank connection still completes."""
    from app.banking.exceptions import EnableBankingAPIError

    override_eb_client.get_all_transactions = AsyncMock(
        side_effect=EnableBankingAPIError(503, "Unavailable")
    )
    token = await register_and_login(client)
    headers = auth(token)

    await client.post(
        "/api/v1/banking/connect",
        json={"bank_name": "Mock Bank", "bank_country": "ES"},
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/banking/callback",
        json={"code": "code-fail"},
        headers=headers,
    )
    # Connection completes with the account list even if transactions failed
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # No transactions were synced
    txn_resp = await client.get("/api/v1/transactions/", headers=auth(token))
    assert txn_resp.json()["total"] == 0
