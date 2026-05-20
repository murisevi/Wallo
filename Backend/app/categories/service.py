"""Categorisation service - orchestrates the transaction classification cascade."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.keyword_rules import match_keyword_rule
from app.categories.mcc_mapping import match_mcc_category
from app.categories.merchant_dictionary import match_known_merchant
from app.categories.merchant_mapping import MerchantMapping
from app.categories.ml_categorizer import TransactionCategorizer
from app.categories.models import Category, CategoryCorrection
from app.categories.schemas import CategoryResponse
from app.categories.text_cleaner import (
    clean_bank_description,
    detect_transaction_type,
    extract_merchant_key,
    normalize_text,
)
from app.transactions.models import Transaction

logger = logging.getLogger(__name__)

# Confidence thresholds:
# >= 0.70 -> confirmed ML category
# 0.40..0.70 -> suggestion only (does not affect reports/budgets)
# < 0.40 -> uncategorised, no suggestion
THRESHOLD_AUTO = 0.70
THRESHOLD_SUGGEST = 0.40
THRESHOLD_AUTO_MARGIN = 0.12

BLOCKED_MERCHANT_KEYS: frozenset[str] = frozenset(
    {
        "",
        "K",
        "K 2",
        "SAN JUAN",
        "SERVICIOS",
        "CAMPANA",
        "CAMPANA CONTRATO",
    }
)

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
            _categorizer = TransactionCategorizer()
        except Exception as exc:
            logger.warning(
                "Could not load trained categorisation model (%s). "
                "Categorisation will skip ML until the model is retrained.",
                exc,
            )
            _categorizer = TransactionCategorizer()
    return _categorizer


def reload_categorizer() -> None:
    """Force a reload of the model from disk (call after retraining)."""
    global _categorizer
    _categorizer = None
    get_categorizer()


async def categorize_transaction(
    db: AsyncSession,
    transaction: Transaction,
    user_id: uuid.UUID,
) -> Transaction:
    """Categorise a single transaction using deterministic layers before ML."""
    raw_desc = _categorization_text(transaction)
    amount = float(transaction.amount or 0)
    category_type = _category_type_for_amount(amount)

    cleaned = clean_bank_description(raw_desc)
    merchant_key = extract_merchant_key(cleaned)
    tx_type = detect_transaction_type(raw_desc)

    income_rule = _income_rule_category_name(raw_desc, amount, tx_type)
    if income_rule is not None:
        category = await _resolve_category_by_name(
            db, income_rule, user_id, category_type="income"
        )
        if category:
            _assign_category(transaction, category.id, 0.88, "rule_based")
            logger.debug("Rule-based income: %s -> %s", cleaned, income_rule)
            return transaction

    if tx_type == "bizum_received":
        category = await _resolve_category_by_name(
            db, "Transferencias recibidas", user_id, category_type="income"
        )
        if category:
            _assign_category(transaction, category.id, 0.85, "rule_based")
            logger.debug("Rule-based: bizum_received -> Transferencias recibidas")
            return transaction

    if tx_type in ("bizum_sent", "cash"):
        category = await _resolve_category_by_name(
            db, "Otros gastos", user_id, category_type="expense"
        )
        if category:
            _assign_category(transaction, category.id, 0.85, "rule_based")
            logger.debug("Rule-based: %s -> Otros gastos", tx_type)
            return transaction

    mapping = await _lookup_merchant_mapping(db, user_id, merchant_key)
    if mapping:
        mapped_category = await _resolve_category_by_id(
            db, mapping.category_id, user_id, category_type=category_type
        )
        if mapped_category:
            _assign_category(transaction, mapping.category_id, 1.0, "merchant_map")
            logger.debug(
                "Merchant map hit: %s -> %s",
                merchant_key,
                mapping.category_id,
            )
            return transaction

    mcc_match = match_mcc_category(transaction.merchant_category_code)
    if mcc_match:
        mcc_category_name, mcc_confidence = mcc_match
        mcc_category = await _resolve_category_by_name(
            db, mcc_category_name, user_id, category_type=category_type
        )
        if mcc_category:
            _assign_category(transaction, mcc_category.id, mcc_confidence, "mcc")
            logger.debug(
                "MCC hit: %s -> %s (%.2f)",
                transaction.merchant_category_code,
                mcc_category_name,
                mcc_confidence,
            )
            return transaction

    dict_match = match_known_merchant(cleaned)
    if dict_match:
        dict_category_name, dict_confidence = dict_match
        dict_category = await _resolve_category_by_name(
            db, dict_category_name, user_id, category_type=category_type
        )
        if dict_category:
            _assign_category(
                transaction,
                dict_category.id,
                dict_confidence,
                "global_dict",
            )
            logger.debug(
                "Global dict hit: %s -> %s (%.2f)",
                cleaned,
                dict_category_name,
                dict_confidence,
            )
            return transaction

    kw_match = match_keyword_rule(cleaned)
    if kw_match:
        kw_category_name, kw_confidence = kw_match
        kw_category = await _resolve_category_by_name(
            db, kw_category_name, user_id, category_type=category_type
        )
        if kw_category:
            if kw_confidence >= THRESHOLD_AUTO:
                _assign_category(
                    transaction,
                    kw_category.id,
                    kw_confidence,
                    "keyword_rule",
                )
            else:
                _assign_suggestion(
                    transaction,
                    kw_category.id,
                    kw_confidence,
                    "keyword_suggested",
                )
            logger.debug(
                "Keyword rule hit: %s -> %s (%.2f)",
                cleaned,
                kw_category_name,
                kw_confidence,
            )
            return transaction

    categorizer = get_categorizer()
    if categorizer.is_trained:
        if hasattr(categorizer, "predict_with_margin"):
            predicted_name, confidence, margin = categorizer.predict_with_margin(
                raw_desc,
                amount,
                bank_transaction_code=transaction.bank_transaction_code,
                merchant_category_code=transaction.merchant_category_code,
            )
        else:
            predicted_name, confidence = categorizer.predict(raw_desc, amount)
            margin = 1.0
        category = await _resolve_category_by_name(
            db, predicted_name, user_id, category_type=category_type
        )

        if category:
            if confidence >= THRESHOLD_AUTO and margin >= THRESHOLD_AUTO_MARGIN:
                _assign_category(transaction, category.id, confidence, "ml_auto")
            elif confidence >= THRESHOLD_SUGGEST:
                _assign_suggestion(transaction, category.id, confidence, "ml_suggested")
            else:
                _clear_category_and_suggestion(transaction)

            logger.debug(
                "ML prediction: %s -> %s (%.2f, margin=%.2f, method=%s, suggestion=%s)",
                cleaned,
                predicted_name,
                confidence,
                margin,
                transaction.categorization_method,
                transaction.suggested_categorization_method,
            )
            return transaction

    _clear_category_and_suggestion(transaction)
    logger.debug("No categorisation for: %s", cleaned)
    return transaction


async def categorize_batch(
    db: AsyncSession,
    transactions: list[Transaction],
    user_id: uuid.UUID,
) -> list[Transaction]:
    """Categorise a list of transactions. Returns the same list mutated in-place."""
    for tx in transactions:
        await categorize_transaction(db, tx, user_id)
    return transactions


async def correct_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    new_category_id: uuid.UUID,
) -> tuple[Transaction, int]:
    """Process a user correction and teach the merchant mapping layer."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise ValueError(f"Transaction {transaction_id} not found")

    correction_text = _categorization_text(transaction)
    cleaned = clean_bank_description(correction_text)
    merchant_key = extract_merchant_key(cleaned)
    mapping_conflict = await _has_conflicting_correction(
        db,
        user_id,
        merchant_key,
        new_category_id,
    )

    correction = CategoryCorrection(
        user_id=user_id,
        transaction_id=transaction_id,
        original_description=transaction.description or correction_text,
        cleaned_merchant=merchant_key,
        amount=transaction.amount or 0,
        predicted_category_id=(
            transaction.category_id or transaction.suggested_category_id
        ),
        corrected_category_id=new_category_id,
    )
    db.add(correction)

    _assign_category(transaction, new_category_id, 1.0, "manual")
    transaction.is_manually_corrected = True

    await _upsert_merchant_mapping(
        db,
        user_id,
        merchant_key,
        new_category_id,
        is_ambiguous=mapping_conflict,
    )

    also_updated = 0
    if not mapping_conflict and _can_use_merchant_key(merchant_key):
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
        "Category corrected: tx=%s, merchant=%s -> category=%s (%d additional updated)",
        transaction_id,
        merchant_key,
        new_category_id,
        also_updated,
    )
    return transaction, also_updated


async def accept_suggestions(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_ids: list[uuid.UUID],
) -> dict[str, int]:
    """Accept suggested categories for a bounded list of transactions."""
    accepted = 0
    skipped = 0
    total_also_updated = 0

    for transaction_id in transaction_ids:
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        transaction = result.scalar_one_or_none()
        if transaction is None or transaction.suggested_category_id is None:
            skipped += 1
            continue

        _transaction, also_updated = await correct_category(
            db,
            user_id,
            transaction_id,
            transaction.suggested_category_id,
        )
        accepted += 1
        total_also_updated += also_updated

    return {
        "accepted": accepted,
        "skipped": skipped,
        "also_updated": total_also_updated,
    }


async def recategorize_all_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """Re-run the categorization cascade on all non-manual transactions."""
    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.is_manually_corrected.is_(False),
    )
    result = await db.execute(stmt)
    transactions = list(result.scalars().all())

    if not transactions:
        return {
            "total": 0,
            "rule_based": 0,
            "merchant_map": 0,
            "mcc": 0,
            "global_dict": 0,
            "keyword_rule": 0,
            "keyword_suggested": 0,
            "ml_auto": 0,
            "ml_suggested": 0,
            "uncategorized": 0,
        }

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
        "mcc": sum(1 for t in transactions if t.categorization_method == "mcc"),
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
            1
            for t in transactions
            if t.suggested_categorization_method == "ml_suggested"
        ),
        "keyword_suggested": sum(
            1
            for t in transactions
            if t.suggested_categorization_method == "keyword_suggested"
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
    """Return all categories available to a user: global + custom."""
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


async def _lookup_merchant_mapping(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
) -> MerchantMapping | None:
    if not _can_use_merchant_key(merchant_key):
        return None
    result = await db.execute(
        select(MerchantMapping).where(
            MerchantMapping.user_id == user_id,
            MerchantMapping.merchant_name == merchant_key,
            MerchantMapping.is_ambiguous.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def _lookup_any_merchant_mapping(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
) -> MerchantMapping | None:
    if not _can_use_merchant_key(merchant_key):
        return None
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
    category_type: str | None = None,
) -> Category | None:
    filters = [
        Category.name == name,
        or_(Category.user_id.is_(None), Category.user_id == user_id),
    ]
    if category_type is not None:
        filters.append(Category.type == category_type)
    result = await db.execute(select(Category).where(*filters))
    return result.scalar_one_or_none()


async def _resolve_category_by_id(
    db: AsyncSession,
    category_id: uuid.UUID,
    user_id: uuid.UUID,
    category_type: str | None = None,
) -> Category | None:
    filters = [
        Category.id == category_id,
        or_(Category.user_id.is_(None), Category.user_id == user_id),
    ]
    if category_type is not None:
        filters.append(Category.type == category_type)
    result = await db.execute(select(Category).where(*filters))
    return result.scalar_one_or_none()


async def _recategorize_same_merchant(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
    exclude_transaction_id: uuid.UUID,
) -> int:
    """Update all non-manual transactions that share a merchant key."""
    if not _can_use_merchant_key(merchant_key):
        return 0

    stmt = select(
        Transaction.id,
        Transaction.description,
        Transaction.creditor_name,
        Transaction.debtor_name,
        Transaction.bank_transaction_code,
    ).where(
        Transaction.user_id == user_id,
        Transaction.is_manually_corrected.is_(False),
        Transaction.id != exclude_transaction_id,
    )
    rows = (await db.execute(stmt)).all()

    matching_ids = [
        tx_id
        for tx_id, description, creditor, debtor, bank_code in rows
        if extract_merchant_key(
            clean_bank_description(
                _join_text_parts(description, creditor, debtor, bank_code)
            )
        )
        == merchant_key
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
            suggested_category_id=None,
            suggested_confidence_score=None,
            suggested_categorization_method=None,
        )
    )

    logger.info(
        "Same-merchant propagation: merchant=%s -> %d transactions updated",
        merchant_key,
        len(matching_ids),
    )
    return len(matching_ids)


async def _upsert_merchant_mapping(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
    *,
    is_ambiguous: bool = False,
) -> None:
    """Create or update the merchant -> category mapping."""
    if not _can_use_merchant_key(merchant_key):
        return None
    existing = await _lookup_any_merchant_mapping(db, user_id, merchant_key)
    if existing:
        if is_ambiguous:
            existing.is_ambiguous = True
            existing.confidence = 0
        else:
            existing.category_id = category_id
            existing.confidence += 1
            existing.is_ambiguous = False
    else:
        db.add(
            MerchantMapping(
                user_id=user_id,
                merchant_name=merchant_key,
                category_id=category_id,
                confidence=0 if is_ambiguous else 1,
                is_ambiguous=is_ambiguous,
            )
        )


async def _has_conflicting_correction(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
) -> bool:
    if not _can_use_merchant_key(merchant_key):
        return False
    result = await db.execute(
        select(CategoryCorrection.id).where(
            CategoryCorrection.user_id == user_id,
            CategoryCorrection.cleaned_merchant == merchant_key,
            CategoryCorrection.corrected_category_id != category_id,
        )
    )
    return result.first() is not None


def _category_type_for_amount(amount: float) -> str:
    return "income" if amount > 0 else "expense"


def _join_text_parts(*parts: object) -> str:
    return " ".join(str(part).strip() for part in parts if part)


def _categorization_text(transaction: Transaction) -> str:
    """Build the richest safe text available for categorisation."""
    return _join_text_parts(
        transaction.description,
        transaction.creditor_name,
        transaction.debtor_name,
        transaction.bank_transaction_code,
        transaction.merchant_category_code,
    )


def _can_use_merchant_key(merchant_key: str) -> bool:
    normalized = normalize_text(merchant_key)
    if normalized in BLOCKED_MERCHANT_KEYS:
        return False
    words = normalized.split()
    return any(len(word) > 2 for word in words)


def _income_rule_category_name(
    raw_desc: str,
    amount: float,
    tx_type: str,
) -> str | None:
    """Return a deterministic income category for unambiguous patterns."""
    if amount <= 0:
        return None

    normalized = normalize_text(raw_desc)
    if re.search(r"\b(?:ABONO\s+)?NOMINA\b|\bSALARIO\b", normalized):
        return "Nómina"
    if re.search(
        r"\b(?:DEVOLUCION|REEMBOLSO|RETROCESION|BONIFICACION|LIQUIDACION)\b",
        normalized,
    ):
        return "Devoluciones"
    if tx_type in {"transfer", "bizum_received"} or re.search(
        r"\bTRANSFERENCIA\b", normalized
    ):
        return "Transferencias recibidas"
    return None


def _assign_category(
    transaction: Transaction,
    category_id: uuid.UUID,
    confidence: float,
    method: str,
) -> None:
    transaction.category_id = category_id
    transaction.confidence_score = confidence
    transaction.categorization_method = method
    _clear_suggestion(transaction)


def _assign_suggestion(
    transaction: Transaction,
    category_id: uuid.UUID,
    confidence: float,
    method: str,
) -> None:
    transaction.category_id = None
    transaction.confidence_score = 0.0
    transaction.categorization_method = None
    transaction.suggested_category_id = category_id
    transaction.suggested_confidence_score = confidence
    transaction.suggested_categorization_method = method


def _clear_suggestion(transaction: Transaction) -> None:
    transaction.suggested_category_id = None
    transaction.suggested_confidence_score = None
    transaction.suggested_categorization_method = None


def _clear_category_and_suggestion(transaction: Transaction) -> None:
    transaction.category_id = None
    transaction.confidence_score = 0.0
    transaction.categorization_method = None
    _clear_suggestion(transaction)
