"""Recurring charges API router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.recurring_charges import service as svc
from app.recurring_charges.schemas import RecurringChargeResponse, SetInstallmentRequest
from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/recurring-charges", tags=["recurring-charges"])


@router.get("/", response_model=list[RecurringChargeResponse])
async def list_recurring_charges(
    current_user: CurrentUser,
    db: DbSession,
) -> list[RecurringChargeResponse]:
    """List active (possible + confirmed) recurring charges for the authenticated user,
    ordered by next predicted date."""
    return await svc.get_upcoming(db, current_user.id)


@router.patch("/{charge_id}/confirm", response_model=RecurringChargeResponse)
async def confirm_charge(
    charge_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> RecurringChargeResponse:
    """Manually confirm a possible recurring charge."""
    return await svc.confirm(db, current_user.id, charge_id)


@router.patch("/{charge_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_charge(
    charge_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Dismiss a recurring charge (user has unsubscribed).
    The charge will not reappear after future syncs."""
    await svc.dismiss(db, current_user.id, charge_id)


@router.patch("/{charge_id}/installment", response_model=RecurringChargeResponse)
async def set_installment(
    charge_id: uuid.UUID,
    data: SetInstallmentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> RecurringChargeResponse:
    """Mark a recurring charge as a fixed-term installment plan."""
    return await svc.set_installment(
        db, current_user.id, charge_id, data.installment_total
    )


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_charge(
    charge_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Permanently delete a recurring charge (deny — not a real recurring payment)."""
    await svc.delete(db, current_user.id, charge_id)
