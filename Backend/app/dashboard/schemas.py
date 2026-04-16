import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.recurring_charges.schemas import RecurringChargeResponse
from app.transactions.schemas import TransactionResponse


class AccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iban: str | None
    name: str | None
    bank_name: str
    bank_logo: str | None
    balance: Decimal | None
    currency: str


class DashboardResponse(BaseModel):
    total_balance: Decimal
    currency: str
    accounts: list[AccountSummary]
    recent_transactions: list[TransactionResponse]
    last_synced_at: datetime | None
    upcoming_charges: list[RecurringChargeResponse] = []
