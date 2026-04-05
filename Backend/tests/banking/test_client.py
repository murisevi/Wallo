"""Tests for EnableBankingClient using mocked HTTP responses."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.banking.client import EnableBankingClient
from app.banking.exceptions import (
    EnableBankingAPIError,
    EnableBankingAuthError,
    EnableBankingRateLimitError,
)


@pytest.fixture
def mock_key(tmp_path):
    """Create a fake PEM key file for testing (not used for real signing)."""
    # Generate a real RSA key so PyJWT can sign with it
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_file = tmp_path / "test.pem"
    key_file.write_bytes(pem)
    return str(key_file)


@pytest.fixture
def client(mock_key):
    """Create an EnableBankingClient with mocked config."""
    with patch("app.banking.client.settings") as mock_settings:
        mock_settings.enable_banking_app_id = "test-app-id"
        mock_settings.enable_banking_private_key_path = mock_key
        c = EnableBankingClient()
    return c


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
    headers: dict | None = None,
):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = headers or {}
    return resp


# ── list_aspsps ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_aspsps(client):
    fake_aspsps = [
        {"name": "Mock ASPSP", "country": "ES", "logo": "https://logo.png"},
    ]
    client._http.request = AsyncMock(
        return_value=_mock_response(200, {"aspsps": fake_aspsps})
    )

    result = await client.list_aspsps("ES")

    assert len(result) == 1
    assert result[0]["name"] == "Mock ASPSP"
    client._http.request.assert_called_once()
    call_args = client._http.request.call_args
    assert call_args[0] == ("GET", "/aspsps")
    assert call_args[1]["params"] == {"country": "ES"}


# ── start_authorization ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_authorization(client):
    client._http.request = AsyncMock(
        return_value=_mock_response(
            200,
            {
                "url": "https://bank.example.com/auth",
                "authorization_id": "auth-uuid-123",
            },
        )
    )

    result = await client.start_authorization(
        "BBVA", "ES", "http://localhost:3000/callback"
    )

    assert result["url"] == "https://bank.example.com/auth"
    assert result["authorization_id"] == "auth-uuid-123"
    call_args = client._http.request.call_args
    body = call_args[1]["json"]
    assert body["aspsp"] == {"name": "BBVA", "country": "ES"}
    assert body["psu_type"] == "personal"
    assert body["access"]["balances"] is True
    assert body["access"]["transactions"] is True


# ── create_session ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session(client):
    client._http.request = AsyncMock(
        return_value=_mock_response(
            200,
            {
                "session_id": "sess-uuid",
                "accounts": [
                    {
                        "uid": "acc-uid-1",
                        "account_id": {"iban": "ES1234567890"},
                        "name": "Cuenta corriente",
                        "currency": "EUR",
                        "cash_account_type": "CACC",
                        "product": None,
                    }
                ],
                "aspsp": {"name": "Mock", "country": "ES"},
                "access": {"valid_until": "2026-07-01T00:00:00.000Z"},
            },
        )
    )

    result = await client.create_session("auth-code-xyz")

    assert result["session_id"] == "sess-uuid"
    assert len(result["accounts"]) == 1
    acc = result["accounts"][0]
    assert acc["uid"] == "acc-uid-1"
    assert acc["iban"] == "ES1234567890"
    assert acc["currency"] == "EUR"


# ── get_account_balances ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_account_balances(client):
    client._http.request = AsyncMock(
        return_value=_mock_response(
            200,
            {
                "balances": [
                    {
                        "balance_type": "ITAV",
                        "balance_amount": {"amount": "1234.56", "currency": "EUR"},
                        "reference_date": "2026-04-04",
                    },
                ]
            },
        )
    )

    result = await client.get_account_balances("acc-uid-1")

    assert len(result) == 1
    assert result[0]["balance_type"] == "ITAV"
    assert result[0]["amount"] == Decimal("1234.56")
    assert result[0]["currency"] == "EUR"


# ── get_account_transactions ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_account_transactions(client):
    client._http.request = AsyncMock(
        return_value=_mock_response(
            200,
            {
                "transactions": [
                    {
                        "transaction_id": "txn-1",
                        "booking_date": "2026-04-01",
                        "credit_debit_indicator": "DBIT",
                        "status": "BOOK",
                        "transaction_amount": {"amount": "-15.50", "currency": "EUR"},
                        "creditor": {"name": "Supermercado"},
                        "remittance_information": ["Compra alimentacion"],
                    }
                ],
                "continuation_key": None,
            },
        )
    )

    result = await client.get_account_transactions("acc-uid-1")

    assert result["continuation_key"] is None
    assert len(result["transactions"]) == 1
    txn = result["transactions"][0]
    assert txn["amount"] == Decimal("-15.50")
    assert txn["creditor_name"] == "Supermercado"


# ── get_all_transactions (pagination) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_all_transactions_pagination(client):
    """Verify the client follows continuation_key across multiple pages."""
    txn1 = {
        "transaction_id": "t1",
        "transaction_amount": {"amount": "10.00", "currency": "EUR"},
    }
    txn2 = {
        "transaction_id": "t2",
        "transaction_amount": {"amount": "20.00", "currency": "EUR"},
    }
    page1 = _mock_response(
        200,
        {
            "transactions": [txn1],
            "continuation_key": "page2-key",
        },
    )
    page2 = _mock_response(
        200,
        {
            "transactions": [],  # empty page with key — must keep going
            "continuation_key": "page3-key",
        },
    )
    page3 = _mock_response(
        200,
        {
            "transactions": [txn2],
            "continuation_key": None,  # done
        },
    )
    client._http.request = AsyncMock(side_effect=[page1, page2, page3])

    result = await client.get_all_transactions("acc-uid-1")

    assert len(result) == 2
    assert result[0]["transaction_id"] == "t1"
    assert result[1]["transaction_id"] == "t2"
    assert client._http.request.call_count == 3


# ── Error handling ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_error_raises(client):
    client._http.request = AsyncMock(
        return_value=_mock_response(401, text="Unauthorized")
    )
    with pytest.raises(EnableBankingAuthError):
        await client.list_aspsps("ES")


@pytest.mark.asyncio
async def test_rate_limit_retries_then_raises(client):
    resp_429 = _mock_response(
        429,
        text="Too many requests",
        headers={"retry-after": "1"},
    )
    client._http.request = AsyncMock(return_value=resp_429)

    with pytest.raises(EnableBankingRateLimitError) as exc_info:
        await client.list_aspsps("ES")

    assert exc_info.value.retry_after == 1
    assert client._http.request.call_count == 3  # MAX_RETRIES


@pytest.mark.asyncio
async def test_server_error_retries_then_raises(client):
    resp_500 = _mock_response(500, text="Internal Server Error")
    client._http.request = AsyncMock(return_value=resp_500)

    with pytest.raises(EnableBankingAPIError) as exc_info:
        await client.list_aspsps("ES")

    assert exc_info.value.status_code == 500
    assert client._http.request.call_count == 3


@pytest.mark.asyncio
async def test_client_error_no_retry(client):
    resp_404 = _mock_response(404, text="Not found")
    client._http.request = AsyncMock(return_value=resp_404)

    with pytest.raises(EnableBankingAPIError) as exc_info:
        await client.list_aspsps("ES")

    assert exc_info.value.status_code == 404
    assert client._http.request.call_count == 1  # no retry


# ── JWT generation ───────────────────────────────────────────────────────────


def test_jwt_generation(client):
    """Verify the JWT can be generated and has correct headers."""
    import jwt as pyjwt

    token = client._generate_jwt()
    header = pyjwt.get_unverified_header(token)

    assert header["alg"] == "RS256"
    assert header["kid"] == "test-app-id"
    assert header["typ"] == "JWT"
