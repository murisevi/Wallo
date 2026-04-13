"""Enable Banking API client.

All Enable Banking HTTP calls go through this client — never raw httpx elsewhere.
See: https://enablebanking.com/docs/api/reference/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import jwt as pyjwt

from app.banking.exceptions import (
    EnableBankingAPIError,
    EnableBankingAuthError,
    EnableBankingRateLimitError,
)
from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.enablebanking.com"
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 1.0


# ---------------------------------------------------------------------------
# Response type aliases
# ---------------------------------------------------------------------------
ASPSP = dict[str, Any]
Balance = dict[str, Any]
Transaction = dict[str, Any]


def _build_psu_headers(
    psu_ip: str | None,
    psu_user_agent: str | None,
) -> dict[str, str]:
    """Build PSU headers for Enable Banking requests triggered by an active user.

    When both headers are present the 4/day background-fetch rate limit is
    bypassed entirely.  Only include real values — never send empty strings.
    """
    headers: dict[str, str] = {}
    if psu_ip:
        headers["Psu-Ip-Address"] = psu_ip
    if psu_user_agent:
        headers["Psu-User-Agent"] = psu_user_agent
    return headers


def _parse_amount(raw: dict[str, str]) -> dict[str, Decimal | str]:
    """Convert Enable Banking amount {amount: str, currency: str} → Decimal."""
    return {
        "amount": Decimal(raw["amount"]),
        "currency": raw["currency"],
    }


class EnableBankingClient:
    """Async HTTP client for the Enable Banking PSD2 API.

    Usage::

        async with EnableBankingClient() as eb:
            banks = await eb.list_aspsps("ES")
    """

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._app_id: str = settings.enable_banking_app_id
        key_path = Path(settings.enable_banking_private_key_path)
        if not key_path.is_absolute():
            key_path = Path(__file__).resolve().parents[2] / key_path
        try:
            self._private_key: str = key_path.read_text()
        except FileNotFoundError as exc:
            raise EnableBankingAuthError(
                f"Private key not found at {key_path}. "
                "Download it from the Enable Banking control panel."
            ) from exc

        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def __aenter__(self) -> EnableBankingClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    # ── JWT ───────────────────────────────────────────────────────────────

    def _generate_jwt(self) -> str:
        """Create a short-lived RS256 JWT for Enable Banking."""
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "enablebanking.com",
            "aud": "api.enablebanking.com",
            "iat": now,
            "exp": now.timestamp() + 3600,  # 1 hour
        }
        try:
            token: str = pyjwt.encode(
                payload,
                self._private_key,
                algorithm="RS256",
                headers={"kid": self._app_id},
            )
        except Exception as exc:
            raise EnableBankingAuthError(f"Failed to sign JWT: {exc}") from exc
        return token

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._generate_jwt()}"}

    # ── Low-level request with retry ──────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Send a request with JWT auth, retries and error handling.

        Pass ``extra_headers`` to include PSU headers (Psu-Ip-Address,
        Psu-User-Agent) — required to bypass the 4/day background fetch
        rate limit when the request is triggered by an active user.
        """
        last_exc: Exception | None = None
        backoff = INITIAL_BACKOFF_S

        for attempt in range(1, MAX_RETRIES + 1):
            logger.debug(
                "Enable Banking %s %s (attempt %d/%d)",
                method,
                path,
                attempt,
                MAX_RETRIES,
            )
            headers = self._auth_headers()
            if extra_headers:
                headers.update(extra_headers)
            resp = await self._http.request(
                method,
                path,
                headers=headers,
                params=params,
                json=json,
            )

            # ── Success ──────────────────────────────────────────────
            if resp.is_success:
                data = resp.json()
                logger.debug(
                    "Enable Banking %s %s → %d",
                    method,
                    path,
                    resp.status_code,
                )
                return data

            # ── Rate limit ───────────────────────────────────────────
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", "5"))
                logger.warning(
                    "Enable Banking rate-limited on %s %s, retry after %ds",
                    method,
                    path,
                    retry_after,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(retry_after)
                    last_exc = EnableBankingRateLimitError(retry_after)
                    continue
                raise EnableBankingRateLimitError(retry_after)

            # ── Auth failure ─────────────────────────────────────────
            if resp.status_code in (401, 403):
                detail = resp.text
                logger.error(
                    "Enable Banking auth error on %s %s: %s",
                    method,
                    path,
                    detail,
                )
                raise EnableBankingAuthError(
                    f"Auth failed ({resp.status_code}): {detail}"
                )

            # ── ASPSP / server error → exponential backoff ───────────
            if resp.status_code >= 500:
                detail = resp.text
                logger.warning(
                    "Enable Banking server error %d on %s %s (attempt %d): %s",
                    resp.status_code,
                    method,
                    path,
                    attempt,
                    detail,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    last_exc = EnableBankingAPIError(resp.status_code, detail)
                    continue
                raise EnableBankingAPIError(resp.status_code, detail)

            # ── Other client error → non-retryable ───────────────────
            detail = resp.text
            logger.error(
                "Enable Banking error %d on %s %s: %s",
                resp.status_code,
                method,
                path,
                detail,
            )
            raise EnableBankingAPIError(resp.status_code, detail)

        # Should not reach here, but just in case:
        raise last_exc or EnableBankingAPIError(  # pragma: no cover
            0, "Max retries exceeded"
        )

    # ── Public API methods ────────────────────────────────────────────────

    async def list_aspsps(self, country: str) -> list[ASPSP]:
        """GET /aspsps — list available banks for a country.

        Args:
            country: ISO 3166-1 alpha-2 code (e.g. "ES").

        Returns:
            List of ASPSP dicts with name, country, logo, auth_methods, etc.
        """
        data = await self._request("GET", "/aspsps", params={"country": country})
        return data.get("aspsps", [])

    async def start_authorization(
        self,
        bank_name: str,
        bank_country: str,
        redirect_url: str,
        valid_days: int = 90,
        state: str | None = None,
    ) -> dict[str, str]:
        """POST /auth — start PSD2 authorization with a bank.

        Returns:
            {"url": "https://...", "authorization_id": "uuid"}
        """
        valid_until = datetime.now(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        # Add valid_days worth of days
        from datetime import timedelta

        valid_until += timedelta(days=valid_days)

        body: dict[str, Any] = {
            "aspsp": {"name": bank_name, "country": bank_country},
            "redirect_url": redirect_url,
            "psu_type": "personal",
            "access": {
                "valid_until": valid_until.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "balances": True,
                "transactions": True,
            },
        }
        if state is not None:
            body["state"] = state

        data = await self._request("POST", "/auth", json=body)
        return {
            "url": data["url"],
            "authorization_id": data["authorization_id"],
        }

    async def create_session(self, code: str) -> dict[str, Any]:
        """POST /sessions — exchange auth code for session + accounts.

        Returns:
            {
                "session_id": "uuid",
                "accounts": [{"uid", "iban", "name", "currency", ...}],
                "aspsp": {"name", "country"},
                "access": {"valid_until": "..."},
            }
        """
        data = await self._request("POST", "/sessions", json={"code": code})

        accounts = []
        for acc in data.get("accounts", []):
            account_id_obj = acc.get("account_id") or {}
            accounts.append(
                {
                    "uid": acc["uid"],
                    "iban": account_id_obj.get("iban"),
                    "name": acc.get("name"),
                    "currency": acc.get("currency"),
                    "cash_account_type": acc.get("cash_account_type"),
                    "product": acc.get("product"),
                }
            )

        return {
            "session_id": data["session_id"],
            "accounts": accounts,
            "aspsp": data.get("aspsp"),
            "access": data.get("access"),
        }

    async def get_account_balances(
        self,
        account_uid: str,
        psu_ip: str | None = None,
        psu_user_agent: str | None = None,
    ) -> list[dict[str, Decimal | str | None]]:
        """GET /accounts/{uid}/balances — fetch balances for one account.

        Pass ``psu_ip`` and ``psu_user_agent`` when the request is triggered
        by an active user to bypass the 4/day background fetch rate limit.

        Returns:
            List of balance dicts with amount (Decimal), currency, balance_type.
        """
        psu_headers = _build_psu_headers(psu_ip, psu_user_agent)
        data = await self._request(
            "GET",
            f"/accounts/{account_uid}/balances",
            extra_headers=psu_headers or None,
        )

        balances = []
        for bal in data.get("balances", []):
            amount_obj = bal.get("balance_amount") or {}
            balances.append(
                {
                    "balance_type": bal.get("balance_type"),
                    "amount": (
                        Decimal(amount_obj["amount"])
                        if "amount" in amount_obj
                        else None
                    ),
                    "currency": amount_obj.get("currency"),
                    "reference_date": bal.get("reference_date"),
                    "last_change_date_time": bal.get("last_change_date_time"),
                }
            )
        return balances

    async def get_account_transactions(
        self,
        account_uid: str,
        date_from: date | None = None,
        continuation_key: str | None = None,
        psu_ip: str | None = None,
        psu_user_agent: str | None = None,
    ) -> dict[str, Any]:
        """GET /accounts/{uid}/transactions — fetch one page of transactions.

        Pass ``psu_ip`` and ``psu_user_agent`` when the request is triggered
        by an active user to bypass the 4/day background fetch rate limit.

        Returns:
            {
                "transactions": [parsed transaction dicts],
                "continuation_key": str | None,
            }
        """
        params: dict[str, str] = {}
        if date_from is not None:
            params["date_from"] = date_from.isoformat()
        if continuation_key is not None:
            params["continuation_key"] = continuation_key

        psu_headers = _build_psu_headers(psu_ip, psu_user_agent)
        data = await self._request(
            "GET",
            f"/accounts/{account_uid}/transactions",
            params=params,
            extra_headers=psu_headers or None,
        )

        transactions = []
        for txn in data.get("transactions", []):
            amount_obj = txn.get("transaction_amount") or {}
            parsed: dict[str, Any] = {
                "transaction_id": txn.get("transaction_id"),
                "entry_reference": txn.get("entry_reference"),
                "booking_date": txn.get("booking_date"),
                "transaction_date": txn.get("transaction_date"),
                "value_date": txn.get("value_date"),
                "credit_debit_indicator": txn.get("credit_debit_indicator"),
                "status": txn.get("status"),
                "amount": (
                    Decimal(amount_obj["amount"]) if "amount" in amount_obj else None
                ),
                "currency": amount_obj.get("currency"),
                "debtor_name": (txn.get("debtor") or {}).get("name"),
                "creditor_name": (txn.get("creditor") or {}).get("name"),
                "debtor_iban": (txn.get("debtor_account") or {}).get("iban"),
                "creditor_iban": (txn.get("creditor_account") or {}).get("iban"),
                "remittance_information": txn.get("remittance_information"),
                "merchant_category_code": txn.get("merchant_category_code"),
                "bank_transaction_code": txn.get("bank_transaction_code"),
            }
            transactions.append(parsed)

        return {
            "transactions": transactions,
            "continuation_key": data.get("continuation_key"),
        }

    async def get_all_transactions(
        self,
        account_uid: str,
        date_from: date | None = None,
        psu_ip: str | None = None,
        psu_user_agent: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch ALL transactions for an account, handling pagination.

        Some banks return empty transaction lists with a non-null
        continuation_key — we keep fetching until the key is None.

        Pass ``psu_ip`` and ``psu_user_agent`` when the request is triggered
        by an active user to bypass the 4/day background fetch rate limit.
        """
        all_transactions: list[dict[str, Any]] = []
        continuation_key: str | None = None

        while True:
            page = await self.get_account_transactions(
                account_uid,
                date_from=date_from,
                continuation_key=continuation_key,
                psu_ip=psu_ip,
                psu_user_agent=psu_user_agent,
            )
            all_transactions.extend(page["transactions"])
            continuation_key = page["continuation_key"]

            if continuation_key is None:
                break

            logger.debug(
                "Fetching next transaction page for %s (have %d so far)",
                account_uid,
                len(all_transactions),
            )

        logger.info(
            "Fetched %d total transactions for account %s",
            len(all_transactions),
            account_uid,
        )
        return all_transactions
