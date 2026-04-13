"""Tests for the ML categorizer."""
import pandas as pd
import pytest

from app.categories.ml_categorizer import TransactionCategorizer


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"description": "MERCADONA", "amount": -45.0, "category": "Alimentación"},
        {"description": "LIDL", "amount": -32.0, "category": "Alimentación"},
        {"description": "CARREFOUR", "amount": -78.0, "category": "Alimentación"},
        {"description": "REPSOL", "amount": -55.0, "category": "Transporte"},
        {"description": "CEPSA", "amount": -48.0, "category": "Transporte"},
        {"description": "BP GASOLINERA", "amount": -52.0, "category": "Transporte"},
        {"description": "SPOTIFY", "amount": -9.99, "category": "Suscripciones"},
        {"description": "NETFLIX", "amount": -17.99, "category": "Suscripciones"},
        {"description": "NOMINA EMPRESA", "amount": 2200.0, "category": "Nómina"},
        {"description": "PAGO NOMINA", "amount": 1850.0, "category": "Nómina"},
    ] * 5)  # Repeat for minimum samples per class


@pytest.fixture
def trained_categorizer(sample_data: pd.DataFrame) -> TransactionCategorizer:
    cat = TransactionCategorizer()
    cat.train(sample_data)
    return cat


class TestTransactionCategorizer:

    def test_train_returns_metrics(self, sample_data: pd.DataFrame) -> None:
        cat = TransactionCategorizer()
        metrics = cat.train(sample_data)
        assert "accuracy" in metrics
        assert "cv_mean" in metrics
        assert metrics["accuracy"] > 0.5

    def test_predict_returns_tuple(self, trained_categorizer: TransactionCategorizer) -> None:
        category, confidence = trained_categorizer.predict("MERCADONA", -45.0)
        assert isinstance(category, str)
        assert 0.0 <= confidence <= 1.0

    def test_predict_food_category(self, trained_categorizer: TransactionCategorizer) -> None:
        category, _ = trained_categorizer.predict("MERCADONA", -45.0)
        assert category == "Alimentación"

    def test_predict_income_category(self, trained_categorizer: TransactionCategorizer) -> None:
        category, _ = trained_categorizer.predict("NOMINA EMPRESA", 2200.0)
        assert category == "Nómina"

    def test_predict_batch(self, trained_categorizer: TransactionCategorizer) -> None:
        results = trained_categorizer.predict_batch(
            ["MERCADONA", "REPSOL"], [-45.0, -55.0]
        )
        assert len(results) == 2
        assert all(isinstance(r, tuple) for r in results)

    def test_not_trained_raises(self) -> None:
        cat = TransactionCategorizer()
        with pytest.raises(RuntimeError):
            cat.predict("MERCADONA", -45.0)
