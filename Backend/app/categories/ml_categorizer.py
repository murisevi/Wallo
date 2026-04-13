"""ML-based transaction categorizer.

Uses TF-IDF + GradientBoosting for text classification.
Supports training, prediction with confidence scores,
and model persistence via joblib.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, LabelEncoder

from app.categories.text_cleaner import clean_bank_description

logger = logging.getLogger(__name__)

# Default paths for the serialized model artefacts
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "categorizer_model.joblib"
ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"


class TransactionCategorizer:
    """ML categorizer with TF-IDF text features + numerical features.

    Usage:
        categorizer = TransactionCategorizer()
        categorizer.train(training_df)  # DataFrame: description, amount, category
        category, confidence = categorizer.predict("MERCADONA", -45.30)
        categorizer.save()

        # Later...
        categorizer = TransactionCategorizer.load()
        category, confidence = categorizer.predict("REPSOL", -52.00)
    """

    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
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

        Args:
            df: Must have columns 'description', 'amount', 'category'.
            test_size: Fraction of data used for cross-validation reporting.

        Returns:
            Dict with training metrics: accuracy, cv_mean, cv_std,
            n_samples, n_classes, classes, trained_at.
        """
        df = df.copy()
        df["clean_desc"] = df["description"].apply(clean_bank_description)

        # Encode labels
        y = self.label_encoder.fit_transform(df["category"])

        # Numerical feature engineering
        df["abs_amount"] = df["amount"].abs()
        df["log_amount"] = np.log1p(df["abs_amount"])
        df["is_income"] = (df["amount"] > 0).astype(int)

        # Text sub-pipeline
        text_features = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        analyzer="char_wb",
                        ngram_range=(2, 4),
                        max_features=3000,
                        lowercase=True,
                        strip_accents="unicode",
                    ),
                ),
            ]
        )

        # Numeric sub-pipeline (pass-through)
        numeric_features = Pipeline(
            [
                ("passthrough", FunctionTransformer(validate=False)),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("text", text_features, "clean_desc"),
                ("nums", numeric_features, ["log_amount", "is_income"]),
            ],
            remainder="drop",
        )

        self.pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "classifier",
                    GradientBoostingClassifier(
                        n_estimators=200,
                        max_depth=5,
                        learning_rate=0.1,
                        min_samples_leaf=2,
                        random_state=42,
                    ),
                ),
            ]
        )

        X = df[["clean_desc", "log_amount", "is_income"]]

        # Cross-validate before fitting on full data
        n_folds = min(5, len(df) // 5 or 2)
        cv_scores = cross_val_score(self.pipeline, X, y, cv=n_folds, scoring="accuracy")

        # Final fit on entire dataset
        self.pipeline.fit(X, y)
        self._is_trained = True

        metrics = {
            "accuracy": float(self.pipeline.score(X, y)),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "n_samples": len(df),
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

    def predict(self, description: str, amount: float) -> tuple[str, float]:
        """Predict category for a single transaction.

        Args:
            description: Raw or cleaned bank description.
            amount: Transaction amount (negative = expense, positive = income).

        Returns:
            Tuple of (category_name, confidence_score 0-1).

        Raises:
            RuntimeError: If model hasn't been trained or loaded.
        """
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        clean_desc = clean_bank_description(description)
        log_amount = float(np.log1p(abs(amount)))
        is_income = 1 if amount > 0 else 0

        X = pd.DataFrame(
            [
                {
                    "clean_desc": clean_desc,
                    "log_amount": log_amount,
                    "is_income": is_income,
                }
            ]
        )

        proba = self.pipeline.predict_proba(X)[0]
        predicted_idx = int(np.argmax(proba))
        confidence = float(proba[predicted_idx])
        category_name = str(self.label_encoder.inverse_transform([predicted_idx])[0])
        return category_name, confidence

    def predict_batch(
        self, descriptions: list[str], amounts: list[float]
    ) -> list[tuple[str, float]]:
        """Predict categories for a batch of transactions.

        Returns:
            List of (category_name, confidence_score) tuples.
        """
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Model not trained.")

        clean_descs = [clean_bank_description(d) for d in descriptions]
        log_amounts = [float(np.log1p(abs(a))) for a in amounts]
        is_incomes = [1 if a > 0 else 0 for a in amounts]

        X = pd.DataFrame(
            {
                "clean_desc": clean_descs,
                "log_amount": log_amounts,
                "is_income": is_incomes,
            }
        )

        probas = self.pipeline.predict_proba(X)
        results: list[tuple[str, float]] = []
        for proba in probas:
            idx = int(np.argmax(proba))
            conf = float(proba[idx])
            cat = str(self.label_encoder.inverse_transform([idx])[0])
            results.append((cat, conf))
        return results

    def save(
        self,
        model_path: Path | None = None,
        encoder_path: Path | None = None,
    ) -> None:
        """Persist model and label encoder to disk."""
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Nothing to save — model has not been trained.")
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
    ) -> "TransactionCategorizer":
        """Load a trained model from disk.

        Raises:
            FileNotFoundError: If no model file exists at the given path.
        """
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
