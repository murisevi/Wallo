"""Banking API router — bank connections, accounts, and balance sync."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.banking.client import EnableBankingClient
from app.banking.exceptions import EnableBankingAPIError, EnableBankingAuthError
from app.banking.schemas import (
    ASPSPResponse,
    BankAccountResponse,
    BankConnectionResponse,
    CallbackRequest,
    ConnectBankRequest,
    ConnectBankResponse,
)
from app.banking.service import BankingService
from app.dependencies import CurrentUser, DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/banking", tags=["banking"])

# ── Sandbox fallback institutions ─────────────────────────────────────────────
# Returned when Enable Banking credentials are not configured.

_SANDBOX_RAW: list[dict[str, Any]] = [
    {"name": "Mock ASPSP", "country": "XX", "logo": None, "auth_methods": []},
    {"name": "BBVA", "country": "ES", "logo": None, "auth_methods": []},
    {"name": "Banco Santander", "country": "ES", "logo": None, "auth_methods": []},
    {"name": "CaixaBank", "country": "ES", "logo": None, "auth_methods": []},
]

SANDBOX_INSTITUTIONS: list[ASPSPResponse] = [ASPSPResponse(**b) for b in _SANDBOX_RAW]

# ── Supplementary institutions (production banks not active in this sandbox) ──
# Enable Banking supports these in production. We surface them here so the UI
# shows a realistic bank list. The exact names must match Enable Banking's
# catalogue (used verbatim in POST /auth → aspsp.name).

_SUPPLEMENTARY_RAW: list[dict[str, Any]] = [
    {
        "name": "Banco Santander",
        "country": "ES",
        "logo": "https://enablebanking.com/brands/ES/Banco%20Santander/",
        "auth_methods": [],
    },
]

_SUPPLEMENTARY: list[ASPSPResponse] = [ASPSPResponse(**b) for b in _SUPPLEMENTARY_RAW]


# ── Dependencies ──────────────────────────────────────────────────────────────


def get_eb_client_or_none(request: Request) -> EnableBankingClient | None:
    """Return the Enable Banking client or None if not configured.

    Used only by endpoints that can degrade gracefully (e.g. listing
    institutions with a sandbox fallback).
    """
    return getattr(request.app.state, "eb_client", None)


EBClientOrNone = Annotated[EnableBankingClient | None, Depends(get_eb_client_or_none)]


def get_eb_client(request: Request) -> EnableBankingClient:
    """Return the Enable Banking client or raise 503 if not configured.

    Used by endpoints that need real Enable Banking access (connect, callback,
    sync, etc.).
    """
    client: EnableBankingClient | None = getattr(request.app.state, "eb_client", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Enable Banking service is not available — check that "
                "ENABLE_BANKING_APP_ID and ENABLE_BANKING_PRIVATE_KEY_PATH "
                "are set correctly in your .env file."
            ),
        )
    return client


EBClient = Annotated[EnableBankingClient, Depends(get_eb_client)]


def get_banking_service(db: DbSession, eb_client: EBClient) -> BankingService:
    return BankingService(db=db, eb_client=eb_client)


BankingSvc = Annotated[BankingService, Depends(get_banking_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/institutions", response_model=list[ASPSPResponse])
async def list_institutions(
    eb_client: EBClientOrNone,
    db: DbSession,
    country: Annotated[
        str, Query(description="ISO 3166-1 alpha-2 country code")
    ] = "ES",
) -> list[ASPSPResponse]:
    """List banks available for connection in a given country (default: Spain).

    Falls back to a hardcoded sandbox list when Enable Banking credentials
    are not configured, so development can continue without real API keys.
    """
    country_upper = country.upper()

    # ── Sandbox fallback ──────────────────────────────────────────────────────
    if eb_client is None:
        logger.warning(
            "Enable Banking client not configured — returning sandbox fallback "
            "institutions (country=%s). To use real banks set "
            "ENABLE_BANKING_APP_ID and ENABLE_BANKING_PRIVATE_KEY_PATH in .env.",
            country_upper,
        )
        return SANDBOX_INSTITUTIONS

    # ── Real API path ─────────────────────────────────────────────────────────
    svc = BankingService(db=db, eb_client=eb_client)
    try:
        aspsps = await svc.list_aspsps(country)
    except EnableBankingAuthError as exc:
        logger.error(
            "Enable Banking auth failed while listing institutions: %s — "
            "check that your .pem private key and APP_ID are correct.",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Enable Banking authentication failed: {exc}",
        ) from exc
    except EnableBankingAPIError as exc:
        logger.error("Enable Banking API error listing institutions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Enable Banking API error: {exc}",
        ) from exc

    result: list[ASPSPResponse] = []
    for aspsp in aspsps:
        try:
            result.append(ASPSPResponse(**aspsp))
        except Exception:
            logger.warning("Skipping malformed ASPSP entry: %r", aspsp)

    # Merge supplementary banks that are not already in the API response
    api_names = {r.name.lower() for r in result}
    for extra in _SUPPLEMENTARY:
        if extra.country.upper() == country_upper and extra.name.lower() not in api_names:
            result.append(extra)

    logger.info(
        "Returned %d institutions for country=%s (%d from API, %d supplementary)",
        len(result),
        country_upper,
        len(aspsps),
        len(result) - len(aspsps),
    )
    return result


@router.get("/connections", response_model=list[BankConnectionResponse])
async def list_connections(
    current_user: CurrentUser,
    svc: BankingSvc,
) -> list[BankConnectionResponse]:
    """List all active bank connections for the authenticated user."""
    return await svc.get_connections(current_user.id)


@router.post("/connect", response_model=ConnectBankResponse)
async def connect_bank(
    body: ConnectBankRequest,
    current_user: CurrentUser,
    svc: BankingSvc,
) -> ConnectBankResponse:
    """Initiate PSD2 bank authorization.

    Returns a redirect URL — the frontend must redirect the user there.
    After bank authentication, Enable Banking redirects to the configured
    callback URL with `?code=xxx`.
    """
    try:
        result = await svc.initiate_connection(
            user_id=current_user.id,
            bank_name=body.bank_name,
            bank_country=body.bank_country,
            redirect_url=body.redirect_url,
        )
    except EnableBankingAuthError as exc:
        logger.error("Enable Banking auth error on /connect: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Enable Banking authentication failed: {exc}",
        ) from exc
    except EnableBankingAPIError as exc:
        logger.error("Enable Banking API error on /connect: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return ConnectBankResponse(**result)


@router.post("/callback", response_model=list[BankAccountResponse])
async def bank_callback(
    body: CallbackRequest,
    current_user: CurrentUser,
    svc: BankingSvc,
) -> list[BankAccountResponse]:
    """Complete bank connection after OAuth redirect.

    Exchange the one-time `code` from Enable Banking for a session,
    store the accounts, and fetch initial balances.
    """
    try:
        return await svc.complete_connection(
            user_id=current_user.id,
            code=body.code,
        )
    except EnableBankingAuthError as exc:
        logger.error("Enable Banking auth error on /callback: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Enable Banking authentication failed: {exc}",
        ) from exc
    except EnableBankingAPIError as exc:
        logger.error("Enable Banking API error on /callback: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/accounts", response_model=list[BankAccountResponse])
async def list_accounts(
    current_user: CurrentUser,
    svc: BankingSvc,
) -> list[BankAccountResponse]:
    """List all connected bank accounts with their latest balances."""
    return await svc.get_user_accounts(current_user.id)


@router.post("/sync", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def sync_all(
    request: Request,
    current_user: CurrentUser,
    svc: BankingSvc,
) -> None:
    """Refresh balances and transactions for all connected accounts.

    Forwards PSU headers (user IP + User-Agent) to Enable Banking so that
    the request is treated as a PSU-triggered fetch, bypassing the 4/day
    background fetch rate limit.
    """
    psu_ip: str | None = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )
    psu_user_agent: str | None = request.headers.get("User-Agent")
    await svc.sync_all(
        current_user.id,
        psu_ip=psu_ip or None,
        psu_user_agent=psu_user_agent or None,
    )


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def disconnect_bank(
    connection_id: uuid.UUID,
    current_user: CurrentUser,
    svc: BankingSvc,
) -> None:
    """Disconnect a bank — deletes the connection and all its accounts."""
    await svc.disconnect_bank(
        user_id=current_user.id,
        connection_id=connection_id,
    )
