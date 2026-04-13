"""ML model retraining — sync function (CPU-bound).

Can be invoked:
  • Directly:  python -m app.categories.tasks
  • Admin API: POST /api/v1/categories/admin/retrain
  • Celery:    uncomment the @shared_task wrapper at the bottom
               (requires celery[redis] to be installed and a worker running)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from app.categories.ml_categorizer import TransactionCategorizer
from app.categories.service import reload_categorizer
from app.config import settings

logger = logging.getLogger(__name__)

# Path to the base CSV that seeds training data
BASE_DATA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "training_data.csv"
)


def _sync_db_url() -> str:
    """Derive a synchronous SQLAlchemy URL from the async DATABASE_URL.

    asyncpg  → psycopg2
    Example: postgresql+asyncpg://u:p@host/db → postgresql+psycopg2://u:p@host/db
    """
    url = str(settings.database_url)
    return url.replace("+asyncpg", "+psycopg2")


def retrain_model() -> dict:
    """Retrain the categorization model with base data + all user corrections.

    This is a **synchronous** function (ML training is CPU-bound).
    It can be called from Celery, a background thread, or directly.

    Steps:
    1. Load the base CSV dataset.
    2. Load every CategoryCorrection row from the DB via a sync connection.
    3. Combine both datasets, giving corrections 3x weight.
    4. Train a new TransactionCategorizer.
    5. Persist the model to disk.
    6. Reload the in-process singleton so live requests immediately use the new model.

    Returns:
        dict with training metrics (accuracy, cv_mean, cv_std, n_samples, n_classes).
    """
    # ── 1. Base CSV ────────────────────────────────────────────────────────────
    base_df = pd.read_csv(BASE_DATA_PATH)
    logger.info("Base training data: %d rows", len(base_df))

    # ── 2. User corrections from DB (sync connection) ─────────────────────────
    engine = create_engine(_sync_db_url(), pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            corrections_df = pd.read_sql(
                text(
                    """
                    SELECT
                        cc.original_description AS description,
                        cc.amount,
                        c.name AS category
                    FROM category_corrections cc
                    JOIN categories c ON c.id = cc.corrected_category_id
                    """
                ),
                conn,
            )
    finally:
        engine.dispose()

    logger.info("User corrections: %d rows", len(corrections_df))

    # ── 3. Combine (corrections carry 3x weight) ────────────────────────────────
    if not corrections_df.empty:
        weighted_corrections = pd.concat([corrections_df] * 3, ignore_index=True)
        combined_df = pd.concat([base_df, weighted_corrections], ignore_index=True)
    else:
        combined_df = base_df

    logger.info("Combined training data: %d rows", len(combined_df))

    # ── 4. Train ───────────────────────────────────────────────────────────────
    categorizer = TransactionCategorizer()
    metrics = categorizer.train(combined_df)

    # ── 5. Save to disk ────────────────────────────────────────────────────────
    categorizer.save()

    # ── 6. Reload in-process singleton ────────────────────────────────────────
    reload_categorizer()

    logger.info("Model retrained successfully: %s", metrics)
    return metrics


# ── Celery task wrapper ────────────────────────────────────────────────────────
# Uncomment once celery[redis] is installed and a worker is configured.

# from celery import shared_task
#
# @shared_task(name="retrain_categorization_model")
# def retrain_categorization_model_task() -> dict:
#     """Celery task wrapper — delegates to the sync retrain_model()."""
#     return retrain_model()


# ── Standalone execution ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
    metrics = retrain_model()
    print("\nRetraining complete:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    sys.exit(0)
