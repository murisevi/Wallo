"""Banking API router — bank connections, accounts, and balance sync."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.banking.client import EnableBankingClient
from app.banking.schemas import (
    ASPSPResponse,
    BankAccountResponse,
    CallbackRequest,
    ConnectBankRequest,
    ConnectBankResponse,
)
from app.banking.service import BankingService
from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/banking", tags=["banking"])


# ── Dependencies ──────────────────────────────────────────────────────────────


def get_eb_client(request: Request) -> EnableBankingClient:
    """Retrieve the Enable Banking client stored on app.state at startup."""
    client: EnableBankingClient | None = getattr(request.app.state, "eb_client", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enable Banking service is not available"
            " — check server configuration.",
        )
    return client


EBClient = Annotated[EnableBankingClient, Depends(get_eb_client)]


def get_banking_service(db: DbSession, eb_client: EBClient) -> BankingService:
    return BankingService(db=db, eb_client=eb_client)


BankingSvc = Annotated[BankingService, Depends(get_banking_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/institutions", response_model=list[ASPSPResponse])
async def list_institutions(
    svc: BankingSvc,
    country: Annotated[
        str, Query(description="ISO 3166-1 alpha-2 country code")
    ] = "ES",
) -> list[ASPSPResponse]:
    """List banks available for connection in a given country (default: Spain)."""
    aspsps = await svc.list_aspsps(country)
    return [ASPSPResponse(**a) for a in aspsps]


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
    result = await svc.initiate_connection(
        user_id=current_user.id,
        bank_name=body.bank_name,
        bank_country=body.bank_country,
    )
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
    return await svc.complete_connection(
        user_id=current_user.id,
        code=body.code,
    )


@router.get("/accounts", response_model=list[BankAccountResponse])
async def list_accounts(
    current_user: CurrentUser,
    svc: BankingSvc,
) -> list[BankAccountResponse]:
    """List all connected bank accounts with their latest balances."""
    return await svc.get_user_accounts(current_user.id)


@router.post("/sync", status_code=status.HTTP_204_NO_CONTENT)
async def sync_balances(
    current_user: CurrentUser,
    svc: BankingSvc,
) -> None:
    """Refresh balances for all connected accounts from Enable Banking."""
    await svc.sync_balances(current_user.id)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
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
