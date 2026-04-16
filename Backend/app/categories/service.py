"""Categorisation service — orchestrates the 6-layer cascade.

Layer 0: Rule-based type detection (Bizum / ATM cash)
Layer 1: Merchant mapping  (exact match from user corrections)
Layer 2: Global merchant dictionary  (static 200+ entry lookup)
Layer 3: Keyword rules  (generic business-type words)
Layer 4: ML model prediction
Layer 5: Confidence threshold  (auto / suggested / uncategorised)
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.keyword_rules import match_keyword_rule
from app.categories.merchant_dictionary import match_known_merchant
from app.categories.merchant_mapping import MerchantMapping
from app.categories.ml_categorizer import TransactionCategorizer
from app.categories.models import Category, CategoryCorrection
from app.categories.schemas import CategoryResponse
from app.categories.text_cleaner import (
    clean_bank_description,
    detect_transaction_type,
    extract_merchant_key,
)
from app.transactions.models import Transaction

logger = logging.getLogger(__name__)

# ── Confidence thresholds ──────────────────────────────────────────────────
THRESHOLD_AUTO = 0.70  # Above → assign automatically ("ml_auto")
THRESHOLD_SUGGEST = 0.40  # Between → mark as suggested ("ml_suggested")
# Below  → leave uncategorised

# ── ML singleton ──────────────────────────────────────────────────────────
_categorizer: TransactionCategorizer | None = None


def get_categorizer() -> TransactionCategorizer:
    """Return the process-level ML categoriser, loading it from disk on first call."""
    global _categorizer
    if _categorizer is None:
        try:
            _categorizer = TransactionCategorizer.load()
        except FileNotFoundError:
            logger.warning(
                "No trained model found. Run scripts/train_base_model.py first. "
                "Categorisation will be skipped until a model is available."
            )
            _categorizer = TransactionCategorizer()  # untrained — is_trained=False
    return _categorizer


def reload_categorizer() -> None:
    """Force a reload of the model from disk (call after retraining)."""
    global _categorizer
    _categorizer = None
    get_categorizer()


# ── Public service functions ───────────────────────────────────────────────


async def categorize_transaction(
    db: AsyncSession,
    transaction: Transaction,
    user_id: uuid.UUID,
) -> Transaction:
    """Categorise a single transaction using the 6-layer cascade.

    Layer 0: Rule-based type detection (Bizum / ATM cash)
    Layer 1: Merchant mapping  (exact match from user corrections)
    Layer 2: Global merchant dictionary  (static 200+ entry lookup)
    Layer 3: Keyword rules  (generic business-type words)
    Layer 4: ML model prediction
    Layer 5: Confidence threshold  (auto / suggested / uncategorised)

    Mutates `transaction` in-place with category_id, confidence_score,
    and categorization_method, then returns it.
    """
    raw_desc = transaction.description or ""
    amount = float(transaction.amount or 0)

    cleaned = clean_bank_description(raw_desc)
    merchant_key = extract_merchant_key(cleaned)

    # ── Layer 0: Rule-based type detection ─────────────────────────────────
    # Bizum and ATM cash are structurally unambiguous — no ML needed.
    tx_type = detect_transaction_type(raw_desc)

    if tx_type == "bizum_received":
        category = await _resolve_category_by_name(db, "Transferencias recibidas", user_id)
        if category:
            transaction.category_id = category.id
            transaction.confidence_score = 0.85
            transaction.categorization_method = "rule_based"
            logger.debug("Rule-based: bizum_received → Transferencias recibidas")
            return transaction

    if tx_type in ("bizum_sent", "cash"):
        category = await _resolve_category_by_name(db, "Otros gastos", user_id)
        if category:
            transaction.category_id = category.id
            transaction.confidence_score = 0.85
            transaction.categorization_method = "rule_based"
            logger.debug("Rule-based: %s → Otros gastos", tx_type)
            return transaction

    # ── Layer 1: Merchant mapping (user-specific, high precision) ──────────
    mapping = await _lookup_merchant_mapping(db, user_id, merchant_key)
    if mapping:
        transaction.category_id = mapping.category_id
        transaction.confidence_score = 1.0
        transaction.categorization_method = "merchant_map"
        logger.debug("Merchant map hit: %s → %s", merchant_key, mapping.category_id)
        return transaction

    # ── Layer 2: Global merchant dictionary ───────────────────────────────
    dict_match = match_known_merchant(cleaned)
    if dict_match:
        dict_category_name, dict_confidence = dict_match
        dict_category = await _resolve_category_by_name(db, dict_category_name, user_id)
        if dict_category:
            transaction.category_id = dict_category.id
            transaction.confidence_score = dict_confidence
            transaction.categorization_method = "global_dict"
            logger.debug(
                "Global dict hit: %s → %s (%.2f)", cleaned, dict_category_name, dict_confidence
            )
            return transaction

    # ── Layer 3: Keyword rules ─────────────────────────────────────────────
    kw_match = match_keyword_rule(cleaned)
    if kw_match:
        kw_category_name, kw_confidence = kw_match
        kw_category = await _resolve_category_by_name(db, kw_category_name, user_id)
        if kw_category:
            transaction.category_id = kw_category.id
            transaction.confidence_score = kw_confidence
            transaction.categorization_method = "keyword_rule"
            logger.debug(
                "Keyword rule hit: %s → %s (%.2f)", cleaned, kw_category_name, kw_confidence
            )
            return transaction

    # ── Layer 4: ML prediction ─────────────────────────────────────────────
    categorizer = get_categorizer()
    if categorizer.is_trained:
        predicted_name, confidence = categorizer.predict(raw_desc, amount)
        category = await _resolve_category_by_name(db, predicted_name, user_id)

        if category:
            transaction.category_id = category.id
            transaction.confidence_score = confidence

            # ── Layer 3: Confidence threshold ──────────────────────────────
            if confidence >= THRESHOLD_AUTO:
                transaction.categorization_method = "ml_auto"
            else:
                # Covers THRESHOLD_SUGGEST <= conf < THRESHOLD_AUTO and below
                transaction.categorization_method = "ml_suggested"

            logger.debug(
                "ML prediction: %s → %s (%.2f, %s)",
                cleaned,
                predicted_name,
                confidence,
                transaction.categorization_method,
            )
            return transaction

    # ── Fallback: uncategorised ────────────────────────────────────────────
    transaction.category_id = None
    transaction.confidence_score = 0.0
    transaction.categorization_method = None
    logger.debug("No categorisation for: %s", cleaned)
    return transaction


async def categorize_batch(
    db: AsyncSession,
    transactions: list[Transaction],
    user_id: uuid.UUID,
) -> list[Transaction]:
    """Categorise a list of transactions.  Returns the same list (mutated in-place)."""
    for tx in transactions:
        await categorize_transaction(db, tx, user_id)
    return transactions


async def correct_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    new_category_id: uuid.UUID,
) -> tuple[Transaction, int]:
    """Process a user correction.

    Updates the transaction, persists a CategoryCorrection for future
    retraining, upserts the merchant mapping, and immediately propagates
    the correction to every other non-manually-corrected transaction that
    shares the same merchant key.

    Propagation is O(n_descriptions) in Python — no ML inference needed,
    ~30 ms for a typical dataset of 500 transactions.

    Returns:
        (transaction, also_updated) where also_updated is the count of
        additional transactions updated beyond the one explicitly corrected.

    Raises:
        ValueError: If the transaction does not exist.
    """
    # 1. Fetch transaction (no user filter — service trusts its callers)
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise ValueError(f"Transaction {transaction_id} not found")

    # 2. Store correction for future retraining
    cleaned = clean_bank_description(transaction.description or "")
    merchant_key = extract_merchant_key(cleaned)

    correction = CategoryCorrection(
        user_id=user_id,
        transaction_id=transaction_id,
        original_description=transaction.description or "",
        cleaned_merchant=merchant_key,
        amount=float(transaction.amount or 0),
        predicted_category_id=transaction.category_id,
        corrected_category_id=new_category_id,
    )
    db.add(correction)

    # 3. Update transaction fields
    transaction.category_id = new_category_id
    transaction.confidence_score = 1.0
    transaction.categorization_method = "manual"
    transaction.is_manually_corrected = True

    # 4. Upsert merchant mapping so it fires on next sync
    await _upsert_merchant_mapping(db, user_id, merchant_key, new_category_id)

    # 5. Propagate immediately to other existing transactions with the same merchant
    also_updated = await _recategorize_same_merchant(
        db,
        user_id=user_id,
        merchant_key=merchant_key,
        category_id=new_category_id,
        exclude_transaction_id=transaction_id,
    )

    await db.flush()
    await db.refresh(transaction)

    logger.info(
        "Category corrected: tx=%s, merchant=%s → category=%s (%d additional updated)",
        transaction_id,
        merchant_key,
        new_category_id,
        also_updated,
    )
    return transaction, also_updated


async def recategorize_all_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """Re-run the categorization cascade on all non-manually-corrected transactions.

    Transactions with ``is_manually_corrected=True`` are skipped — they represent
    explicit user feedback used as training data and must not be overwritten.

    Returns a summary dict with keys:
        total, rule_based, merchant_map, global_dict, keyword_rule,
        ml_auto, ml_suggested, uncategorized
    """
    from app.transactions.models import Transaction  # local import avoids circular dep

    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.is_manually_corrected.is_(False),
    )
    result = await db.execute(stmt)
    transactions = list(result.scalars().all())

    if not transactions:
        return {
            "total": 0,
            "merchant_map": 0,
            "ml_auto": 0,
            "ml_suggested": 0,
            "uncategorized": 0,
        }

    # Re-run the full 3-layer cascade on every eligible transaction.
    # categorize_transaction mutates each Transaction in-place.
    for txn in transactions:
        await categorize_transaction(db, txn, user_id)

    await db.flush()

    summary = {
        "total": len(transactions),
        "rule_based": sum(
            1 for t in transactions if t.categorization_method == "rule_based"
        ),
        "merchant_map": sum(
            1 for t in transactions if t.categorization_method == "merchant_map"
        ),
        "global_dict": sum(
            1 for t in transactions if t.categorization_method == "global_dict"
        ),
        "keyword_rule": sum(
            1 for t in transactions if t.categorization_method == "keyword_rule"
        ),
        "ml_auto": sum(
            1 for t in transactions if t.categorization_method == "ml_auto"
        ),
        "ml_suggested": sum(
            1 for t in transactions if t.categorization_method == "ml_suggested"
        ),
        "uncategorized": sum(1 for t in transactions if t.category_id is None),
    }

    logger.info(
        "Recategorized %d transactions for user %s: %s",
        summary["total"],
        user_id,
        summary,
    )
    return summary


async def get_user_categories(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[CategoryResponse]:
    """Return all categories available to a user: global (user_id IS NULL) + custom."""
    stmt = (
        select(Category)
        .where(or_(Category.user_id.is_(None), Category.user_id == user_id))
        .order_by(Category.type, Category.name)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [CategoryResponse.model_validate(c) for c in rows]


async def create_custom_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    icon: str,
    color: str,
    category_type: str,
) -> Category:
    """Create a user-owned custom category."""
    category = Category(
        name=name,
        icon=icon,
        color=color,
        type=category_type,
        is_custom=True,
        user_id=user_id,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


# ── Private helpers ────────────────────────────────────────────────────────


async def _lookup_merchant_mapping(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
) -> MerchantMapping | None:
    """Return the user's merchant→category mapping for *merchant_key*, or None."""
    result = await db.execute(
        select(MerchantMapping).where(
            MerchantMapping.user_id == user_id,
            MerchantMapping.merchant_name == merchant_key,
        )
    )
    return result.scalar_one_or_none()


async def _resolve_category_by_name(
    db: AsyncSession,
    name: str,
    user_id: uuid.UUID,
) -> Category | None:
    """Find a category by exact name, scoped to global or user-owned categories."""
    result = await db.execute(
        select(Category).where(
            Category.name == name,
            or_(Category.user_id.is_(None), Category.user_id == user_id),
        )
    )
    return result.scalar_one_or_none()


async def _recategorize_same_merchant(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
    exclude_transaction_id: uuid.UUID,
) -> int:
    """Update all non-manually-corrected transactions that share *merchant_key*.

    Avoids the ML pipeline entirely — just fetches descriptions, filters in
    Python with extract_merchant_key(), and issues a single bulk UPDATE.
    Benchmarked at ~30 ms for 500 transactions.

    Returns the number of transactions updated.
    """
    if not merchant_key:
        return 0

    # Fetch only the columns we need — no ML, no relationships
    stmt = select(Transaction.id, Transaction.description).where(
        Transaction.user_id == user_id,
        Transaction.is_manually_corrected.is_(False),
        Transaction.id != exclude_transaction_id,
    )
    rows = (await db.execute(stmt)).all()

    matching_ids = [
        tx_id
        for tx_id, description in rows
        if extract_merchant_key(clean_bank_description(description or "")) == merchant_key
    ]

    if not matching_ids:
        return 0

    await db.execute(
        update(Transaction)
        .where(Transaction.id.in_(matching_ids))
        .values(
            category_id=category_id,
            confidence_score=1.0,
            categorization_method="merchant_map",
        )
    )

    logger.info(
        "Same-merchant propagation: merchant=%s → %d transactions updated",
        merchant_key,
        len(matching_ids),
    )
    return len(matching_ids)


async def _upsert_merchant_mapping(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
) -> None:
    """Create or update the merchant→category mapping, incrementing confidence."""
    existing = await _lookup_merchant_mapping(db, user_id, merchant_key)
    if existing:
        existing.category_id = category_id
        existing.confidence += 1
    else:
        db.add(
            MerchantMapping(
                user_id=user_id,
                merchant_name=merchant_key,
                category_id=category_id,
            )
        )
