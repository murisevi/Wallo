"""Categories API router — CRUD for categories + active-learning correction endpoint."""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, status

from app.categories import service
from app.categories.schemas import (
    AcceptSuggestionsRequest,
    AcceptSuggestionsResponse,
    CategoryCorrectionRequest,
    CategoryCorrectionResponse,
    CategoryCreate,
    CategoryResponse,
    RecategorizeResponse,
)
from app.dependencies import CurrentUser, DbSession

# One-thread executor so training never blocks the event loop
_retrain_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="retrain")

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(
    current_user: CurrentUser,
    db: DbSession,
) -> list[CategoryResponse]:
    """List all system categories plus the authenticated user's custom categories."""
    return await service.get_user_categories(db=db, user_id=current_user.id)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CategoryResponse:
    """Create a custom category owned by the authenticated user."""
    category = await service.create_custom_category(
        db=db,
        user_id=current_user.id,
        name=data.name,
        icon=data.icon,
        color=data.color,
        category_type=data.type,
    )
    return CategoryResponse.model_validate(category)


@router.patch(
    "/transactions/{transaction_id}/category",
    response_model=CategoryCorrectionResponse,
)
async def correct_transaction_category(
    transaction_id: uuid.UUID,
    data: CategoryCorrectionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CategoryCorrectionResponse:
    """Correct the category for a transaction (active-learning feedback loop).

    Records a CategoryCorrection and updates the merchant mapping so the same
    merchant is auto-categorised on subsequent syncs.
    """
    transaction, also_updated = await service.correct_category(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
        new_category_id=data.category_id,
    )
    return CategoryCorrectionResponse(
        transaction_id=transaction.id,
        old_category_id=None,  # correct_category does not return the old value
        new_category_id=transaction.category_id,  # type: ignore[arg-type]
        confidence_score=transaction.confidence_score or 1.0,
        also_updated=also_updated,
    )


@router.post("/suggestions/accept", response_model=AcceptSuggestionsResponse)
async def accept_category_suggestions(
    data: AcceptSuggestionsRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AcceptSuggestionsResponse:
    """Accept suggested categories in bulk via the active-learning path."""
    summary = await service.accept_suggestions(
        db=db,
        user_id=current_user.id,
        transaction_ids=data.transaction_ids,
    )
    return AcceptSuggestionsResponse(**summary)


@router.post("/recategorize", response_model=RecategorizeResponse)
async def recategorize_transactions(
    current_user: CurrentUser,
    db: DbSession,
) -> RecategorizeResponse:
    """Re-run the categorization cascade on all non-manually-corrected transactions.

    Skips any transaction where ``is_manually_corrected=True`` to preserve
    user corrections used as active-learning training data.
    """
    summary = await service.recategorize_all_transactions(
        db=db, user_id=current_user.id
    )
    return RecategorizeResponse(**summary)


@router.post(
    "/admin/retrain",
    include_in_schema=False,  # hidden from public OpenAPI docs
    status_code=status.HTTP_200_OK,
)
async def trigger_retrain(
    current_user: CurrentUser,
) -> dict:
    """Manually trigger ML model retraining (MVP admin endpoint).

    Runs the CPU-bound training in a thread pool so the async event loop
    is never blocked.  Returns the training metrics when complete.

    This endpoint is intentionally excluded from the public OpenAPI schema.
    Replace with a Celery task when Celery is configured.
    """
    from app.categories.tasks import retrain_model

    loop = asyncio.get_running_loop()
    metrics: dict = await loop.run_in_executor(_retrain_executor, retrain_model)
    return {"status": "ok", "metrics": metrics}
