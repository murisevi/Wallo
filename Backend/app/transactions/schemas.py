import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    amount: Decimal
    currency: str
    date: date
    value_date: date | None
    description: str | None
    debtor_name: str | None
    creditor_name: str | None
    credit_debit_indicator: str
    status: str
    category: str | None
    account_iban: str | None = None


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int
