"""ML-based transaction categorizer.

Uses calibrated logistic regression over short-text and transaction metadata
features. The public ``predict`` API stays compatible with the original
implementation while ``predict_with_margin`` exposes top-k ambiguity to the
categorization service.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, LabelEncoder, OneHotEncoder

from app.categories.mcc_mapping import normalize_mcc
from app.categories.seed import DEFAULT_CATEGORIES
from app.categories.text_cleaner import (
    clean_bank_description,
    detect_transaction_type,
    extract_merchant_key,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "categorizer_model.joblib"
ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"

CATEGORY_TYPES = {cat["name"]: cat["type"] for cat in DEFAULT_CATEGORIES}


def _amount_bucket(amount: float) -> str:
    absolute = abs(float(amount))
    if absolute < 10:
        return "lt_10"
    if absolute < 30:
        return "10_30"
    if absolute < 100:
        return "30_100"
    if absolute < 500:
        return "100_500"
    return "gte_500"


class TransactionCategorizer:
    """ML categorizer with text, merchant, transaction-type and amount features."""

    def __init__(self) -> None:
        self.pipeline: Pipeline | CalibratedClassifierCV | None = None
        self.label_encoder: LabelEncoder = LabelEncoder()
        self._is_trained = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def train(
        self,
        df: pd.DataFrame,
        *,
        test_size: float = 0.2,
    ) -> dict:
        """Train the categorizer on a DataFrame.

        Required columns are ``description``, ``amount`` and ``category``.
        Optional columns such as ``bank_transaction_code`` and
        ``merchant_category_code`` are used when present.
        """
        del test_size  # kept for backwards-compatible call sites
        prepared = self._prepare_frame(df)
        y = self.label_encoder.fit_transform(prepared["category"])

        text_char = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            max_features=5000,
            lowercase=True,
            strip_accents="unicode",
        )
        text_word = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=2500,
            lowercase=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b\w+\b",  # noqa: S106 - sklearn token regex
        )
        merchant_word = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=1200,
            lowercase=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b\w+\b",  # noqa: S106 - sklearn token regex
        )
        numeric_features = Pipeline(
            [("passthrough", FunctionTransformer(validate=False))]
        )
        categorical_features = OneHotEncoder(handle_unknown="ignore")

        preprocessor = ColumnTransformer(
            transformers=[
                ("text_char", text_char, "clean_desc"),
                ("text_word", text_word, "model_text"),
                ("merchant", merchant_word, "merchant_key"),
                ("nums", numeric_features, ["log_amount", "is_income"]),
                (
                    "cats",
                    categorical_features,
                    [
                        "tx_type",
                        "amount_bucket",
                        "bank_transaction_code",
                        "merchant_category_code",
                    ],
                ),
            ],
            remainder="drop",
        )

        inner_pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "classifier",
                    LogisticRegression(
                        C=2.0,
                        class_weight="balanced",
                        max_iter=2000,
                        solver="liblinear",
                        random_state=42,
                    ),
                ),
            ]
        )

        X = self._feature_columns(prepared)
        n_folds = max(2, min(5, int(pd.Series(y).value_counts().min())))
        cv_strategy = StratifiedKFold(
            n_splits=n_folds,
            shuffle=True,
            random_state=42,
        )
        cv_scores = cross_val_score(
            inner_pipeline,
            X,
            y,
            cv=cv_strategy,
            scoring="accuracy",
        )

        calibrated: Pipeline | CalibratedClassifierCV
        for cv in (n_folds, 3, None):
            try:
                if cv is None:
                    calibrated = inner_pipeline
                    calibrated.fit(X, y)
                else:
                    calibrated = CalibratedClassifierCV(
                        inner_pipeline,
                        cv=min(cv, n_folds),
                        method="sigmoid",
                    )
                    calibrated.fit(X, y)
                break
            except Exception as exc:
                logger.warning(
                    "Calibration with cv=%s failed (%s), trying fallback",
                    cv,
                    exc,
                )
        else:
            calibrated = inner_pipeline
            calibrated.fit(X, y)

        self.pipeline = calibrated
        self._is_trained = True
        train_pred = self.pipeline.predict(X)

        metrics = {
            "accuracy": float(accuracy_score(y, train_pred)),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "n_samples": len(prepared),
            "n_classes": len(self.label_encoder.classes_),
            "classes": list(self.label_encoder.classes_),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "Model trained: accuracy=%.3f, cv=%.3f±%.3f, samples=%d, classes=%d",
            metrics["accuracy"],
            metrics["cv_mean"],
            metrics["cv_std"],
            metrics["n_samples"],
            metrics["n_classes"],
        )
        return metrics

    def predict(
        self,
        description: str,
        amount: float,
        bank_transaction_code: str | None = None,
        merchant_category_code: str | None = None,
    ) -> tuple[str, float]:
        """Predict category for a single transaction."""
        category, confidence, _margin = self.predict_with_margin(
            description,
            amount,
            bank_transaction_code=bank_transaction_code,
            merchant_category_code=merchant_category_code,
        )
        return category, confidence

    def predict_with_margin(
        self,
        description: str,
        amount: float,
        bank_transaction_code: str | None = None,
        merchant_category_code: str | None = None,
    ) -> tuple[str, float, float]:
        """Predict category plus top1-top2 probability margin."""
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        X = self._feature_columns(
            self._prepare_frame(
                pd.DataFrame(
                    [
                        {
                            "description": description,
                            "amount": amount,
                            "category": "__unknown__",
                            "bank_transaction_code": bank_transaction_code,
                            "merchant_category_code": merchant_category_code,
                        }
                    ]
                )
            )
        )

        proba = self.pipeline.predict_proba(X)[0]
        labels = list(self.label_encoder.classes_)
        allowed_type = "income" if amount > 0 else "expense"
        for idx, label in enumerate(labels):
            if CATEGORY_TYPES.get(str(label)) != allowed_type:
                proba[idx] = -1.0

        ranked = np.argsort(proba)[::-1]
        predicted_idx = int(ranked[0])
        confidence = max(float(proba[predicted_idx]), 0.0)
        second = max(float(proba[int(ranked[1])]), 0.0) if len(ranked) > 1 else 0.0
        margin = confidence - second
        category_name = str(self.label_encoder.inverse_transform([predicted_idx])[0])
        return category_name, confidence, margin

    def predict_batch(
        self, descriptions: list[str], amounts: list[float]
    ) -> list[tuple[str, float]]:
        """Predict categories for a batch of transactions."""
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Model not trained.")

        return [
            self.predict(description, amount)
            for description, amount in zip(descriptions, amounts, strict=False)
        ]

    def save(
        self,
        model_path: Path | None = None,
        encoder_path: Path | None = None,
    ) -> None:
        """Persist model and label encoder to disk."""
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Nothing to save - model has not been trained.")
        model_path = model_path or MODEL_PATH
        encoder_path = encoder_path or ENCODER_PATH
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, model_path)
        joblib.dump(self.label_encoder, encoder_path)
        logger.info("Model saved to %s", model_path)

    @classmethod
    def load(
        cls,
        model_path: Path | None = None,
        encoder_path: Path | None = None,
    ) -> TransactionCategorizer:
        """Load a trained model from disk."""
        model_path = model_path or MODEL_PATH
        encoder_path = encoder_path or ENCODER_PATH

        if not model_path.exists():
            raise FileNotFoundError(
                f"No model found at {model_path}. "
                "Run scripts/train_base_model.py first."
            )

        instance = cls()
        instance.pipeline = joblib.load(model_path)
        instance.label_encoder = joblib.load(encoder_path)
        instance._is_trained = True
        logger.info("Model loaded from %s", model_path)
        return instance

    def _prepare_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        prepared = df.copy()
        prepared["description"] = prepared["description"].fillna("").astype(str)
        prepared["amount"] = pd.to_numeric(
            prepared["amount"],
            errors="coerce",
        ).fillna(0)
        prepared["clean_desc"] = prepared["description"].apply(clean_bank_description)
        prepared["merchant_key"] = prepared["clean_desc"].apply(extract_merchant_key)
        prepared["tx_type"] = prepared["description"].apply(detect_transaction_type)
        prepared["abs_amount"] = prepared["amount"].abs()
        prepared["log_amount"] = np.log1p(prepared["abs_amount"])
        prepared["is_income"] = (prepared["amount"] > 0).astype(int)
        prepared["amount_bucket"] = prepared["amount"].apply(_amount_bucket)
        bank_code = (
            prepared["bank_transaction_code"]
            if "bank_transaction_code" in prepared
            else pd.Series([""] * len(prepared), index=prepared.index)
        )
        mcc = (
            prepared["merchant_category_code"]
            if "merchant_category_code" in prepared
            else pd.Series([""] * len(prepared), index=prepared.index)
        )
        prepared["bank_transaction_code"] = bank_code.fillna("").astype(str).str.upper()
        prepared["merchant_category_code"] = mcc.fillna("").apply(
            lambda value: normalize_mcc(value) or ""
        )
        prepared["model_text"] = (
            prepared["clean_desc"]
            + " "
            + prepared["merchant_key"]
            + " "
            + prepared["tx_type"]
            + " "
            + prepared["merchant_category_code"]
        )
        return prepared

    @staticmethod
    def _feature_columns(df: pd.DataFrame) -> pd.DataFrame:
        return df[
            [
                "clean_desc",
                "model_text",
                "merchant_key",
                "log_amount",
                "is_income",
                "tx_type",
                "amount_bucket",
                "bank_transaction_code",
                "merchant_category_code",
            ]
        ]
