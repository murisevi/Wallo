import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ASPSPResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    country: str
    logo: str | None = None
    auth_methods: list[dict[str, Any]] = []


class ConnectBankRequest(BaseModel):
    bank_name: str
    bank_country: str
    redirect_url: str | None = None  # optional override (e.g. /settings/callback)


class ConnectBankResponse(BaseModel):
    url: str
    authorization_id: str


class CallbackRequest(BaseModel):
    code: str


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iban: str | None
    name: str | None
    account_type: str | None
    currency: str
    balance_amount: Decimal | None
    balance_type: str | None
    last_synced_at: datetime | None


class BankConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_name: str
    bank_country: str
    bank_logo: str | None
    status: str
    accounts_count: int = 0
    last_synced_at: datetime | None = None
    created_at: datetime
