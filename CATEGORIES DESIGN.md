# Guía de Implementación: Categorización Inteligente de Transacciones — Wallo

## Índice

1. [Visión General](#1-visión-general)
2. [Paso 1: Modelos de Base de Datos](#2-paso-1-modelos-de-base-de-datos)
3. [Paso 2: Dataset Base de Entrenamiento](#3-paso-2-dataset-base-de-entrenamiento)
4. [Paso 3: Limpieza de Texto Bancario](#4-paso-3-limpieza-de-texto-bancario)
5. [Paso 4: Motor ML (ml_categorizer)](#5-paso-4-motor-ml)
6. [Paso 5: Servicio de Categorización](#6-paso-5-servicio-de-categorización)
7. [Paso 6: API Endpoints](#7-paso-6-api-endpoints)
8. [Paso 7: Tarea Celery de Reentrenamiento](#8-paso-7-tarea-celery-de-reentrenamiento)
9. [Paso 8: Integración con Sincronización Bancaria](#9-paso-8-integración-con-sincronización)
10. [Paso 9: Frontend](#10-paso-9-frontend)
11. [Paso 10: Tests](#11-paso-10-tests)
12. [Resumen de Archivos a Crear/Modificar](#12-resumen-de-archivos)

---

## 1. Visión General

El sistema de categorización funciona en **3 capas en cascada**:

```
Transacción nueva
       │
       ▼
┌──────────────────┐
│ Capa 1: Merchant │──→ ¿Comercio conocido? ──→ SÍ → Categoría directa (confianza 1.0)
│    Mapping        │
└──────────────────┘
       │ NO
       ▼
┌──────────────────┐
│ Capa 2: Modelo   │──→ TF-IDF + Gradient Boosting → Predicción + confidence_score
│      ML          │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Capa 3: Umbral   │──→ score > 0.7 → auto    │ 0.4-0.7 → sugerida │ < 0.4 → sin categoría
│  de confianza    │
└──────────────────┘
       │
       ▼
  Usuario corrige → 1. Actualiza esa transacción (method="manual", confidence=1.0)
                  → 2. Upsert merchant mapping (próximo sync)
                  → 3. Propaga a TODAS las transacciones existentes del mismo merchant
                       (_recategorize_same_merchant, ~30ms, sin ML)
                  → 4. Almacena CategoryCorrection para reentrenamiento futuro
```

### Dependencias nuevas (añadir a requirements.txt)

```
scikit-learn==1.5.2
joblib==1.4.2
celery[redis]==5.4.0
```

---

## 2. Paso 1: Modelos de Base de Datos

Necesitas crear 2 tablas nuevas (`categories` y `category_corrections`) y modificar la tabla `transactions` existente.

### 2.1 Crear `app/categories/models.py`

```python
"""Category and CategoryCorrection SQLAlchemy models."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    """Predefined and user-custom transaction categories."""

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="tag")
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6B7280")
    type: Mapped[str] = mapped_column(
        String(10), nullable=False  # "expense" | "income"
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # NULL = categoría global del sistema
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category"
    )
    corrections: Mapped[list["CategoryCorrection"]] = relationship(
        foreign_keys="CategoryCorrection.corrected_category_id",
        back_populates="corrected_category",
    )


class CategoryCorrection(Base):
    """Stores user corrections for active learning."""

    __tablename__ = "category_corrections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_merchant: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    predicted_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    corrected_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    corrected_category: Mapped["Category"] = relationship(
        foreign_keys=[corrected_category_id],
        back_populates="corrections",
    )
```

### 2.2 Crear `app/categories/merchant_mapping.py` (modelo para el mapeo)

```python
"""Merchant mapping model — stores learned merchant→category associations."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MerchantMapping(Base):
    """Maps cleaned merchant names to categories, per user."""

    __tablename__ = "merchant_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    merchant_name: Mapped[str] = mapped_column(
        String(255), nullable=False  # cleaned/normalized merchant
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    confidence: Mapped[int] = mapped_column(
        Integer, default=1  # increments with each confirmation
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

### 2.3 Modificar el modelo Transaction existente

Añade estos campos a tu modelo `Transaction` en `app/transactions/models.py`:

```python
# Añadir a los imports:
from sqlalchemy import ForeignKey, Float, String
from sqlalchemy.dialects.postgresql import UUID

# Añadir estas columnas al modelo Transaction:
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    categorization_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True  # "merchant_map" | "ml_auto" | "ml_suggested" | "manual"
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float, nullable=True  # 0.0 - 1.0
    )
    is_manually_corrected: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    # Relationship
    category: Mapped["Category | None"] = relationship(back_populates="transactions")
```

### 2.4 Migración

```bash
# Desde /backend
alembic revision --autogenerate -m "add categories and categorization fields"
alembic upgrade head
```

> **IMPORTANTE**: Asegúrate de importar los nuevos modelos en `alembic/env.py` para que autogenerate los detecte.

---

## 3. Paso 2: Dataset Base de Entrenamiento

### 3.1 Categorías semilla del sistema

Crea `app/categories/seed.py`:

```python
"""Seed default categories and training data."""
from app.categories.models import Category


DEFAULT_CATEGORIES: list[dict] = [
    # --- GASTOS ---
    {"name": "Alimentación", "icon": "shopping-cart", "color": "#22C55E", "type": "expense"},
    {"name": "Restaurantes y Bares", "icon": "utensils", "color": "#F97316", "type": "expense"},
    {"name": "Transporte", "icon": "car", "color": "#3B82F6", "type": "expense"},
    {"name": "Vivienda", "icon": "home", "color": "#8B5CF6", "type": "expense"},
    {"name": "Suministros", "icon": "zap", "color": "#EAB308", "type": "expense"},
    {"name": "Salud", "icon": "heart-pulse", "color": "#EF4444", "type": "expense"},
    {"name": "Ocio", "icon": "gamepad-2", "color": "#EC4899", "type": "expense"},
    {"name": "Ropa", "icon": "shirt", "color": "#A855F7", "type": "expense"},
    {"name": "Educación", "icon": "graduation-cap", "color": "#06B6D4", "type": "expense"},
    {"name": "Suscripciones", "icon": "repeat", "color": "#F59E0B", "type": "expense"},
    {"name": "Seguros", "icon": "shield", "color": "#64748B", "type": "expense"},
    {"name": "Mascotas", "icon": "dog", "color": "#D946EF", "type": "expense"},
    {"name": "Regalos", "icon": "gift", "color": "#F43F5E", "type": "expense"},
    {"name": "Otros gastos", "icon": "circle-dot", "color": "#6B7280", "type": "expense"},
    # --- INGRESOS ---
    {"name": "Nómina", "icon": "banknote", "color": "#10B981", "type": "income"},
    {"name": "Freelance", "icon": "laptop", "color": "#14B8A6", "type": "income"},
    {"name": "Transferencias recibidas", "icon": "arrow-down-left", "color": "#0EA5E9", "type": "income"},
    {"name": "Devoluciones", "icon": "rotate-ccw", "color": "#84CC16", "type": "income"},
    {"name": "Otros ingresos", "icon": "plus-circle", "color": "#6B7280", "type": "income"},
]


async def seed_default_categories(db) -> dict[str, str]:
    """Insert default categories if they don't exist.
    Returns mapping of category_name → category_id.
    """
    from sqlalchemy import select

    existing = (await db.execute(select(Category).where(Category.is_custom == False))).scalars().all()
    if existing:
        return {c.name: str(c.id) for c in existing}

    name_to_id = {}
    for cat_data in DEFAULT_CATEGORIES:
        cat = Category(**cat_data, is_custom=False, user_id=None)
        db.add(cat)
        await db.flush()
        name_to_id[cat.name] = str(cat.id)

    await db.commit()
    return name_to_id
```

### 3.2 Dataset de entrenamiento

Crea `backend/data/training_data.csv` con descripciones típicas de bancos españoles:

```csv
description,amount,category
MERCADONA,-45.30,Alimentación
LIDL,-32.10,Alimentación
CARREFOUR,-78.50,Alimentación
DIA,-15.20,Alimentación
ALDI,-28.90,Alimentación
ALCAMPO,-55.00,Alimentación
SUPERMERCADO EL CORTE INGLES,-92.30,Alimentación
CONSUM,-41.20,Alimentación
EROSKI,-37.80,Alimentación
HIPERCOR,-63.40,Alimentación
MCDONALDS,-12.50,Restaurantes y Bares
BURGER KING,-9.80,Restaurantes y Bares
TELEPIZZA,-18.90,Restaurantes y Bares
JUST EAT,-22.50,Restaurantes y Bares
GLOVO,-15.70,Restaurantes y Bares
UBER EATS,-19.30,Restaurantes y Bares
RESTAURANTE,-35.00,Restaurantes y Bares
BAR CAFETERIA,-8.50,Restaurantes y Bares
STARBUCKS,-5.40,Restaurantes y Bares
REPSOL,-55.00,Transporte
CEPSA,-48.30,Transporte
BP GASOLINERA,-52.00,Transporte
RENFE,-32.50,Transporte
CABIFY,-12.80,Transporte
UBER,-15.60,Transporte
BOLT,-8.90,Transporte
EMT AUTOBUS,-1.50,Transporte
METRO MADRID,-1.50,Transporte
PARKING,-4.50,Transporte
ALQUILER MENSUAL,-750.00,Vivienda
HIPOTECA,-680.00,Vivienda
COMUNIDAD PROPIETARIOS,-95.00,Vivienda
LEROY MERLIN,-45.30,Vivienda
IKEA,-120.50,Vivienda
ENDESA,-85.30,Suministros
IBERDROLA,-92.10,Suministros
NATURGY,-65.40,Suministros
CANAL ISABEL II,-28.50,Suministros
VODAFONE,-45.00,Suministros
MOVISTAR,-55.00,Suministros
ORANGE,-42.00,Suministros
DIGI,-10.00,Suministros
FARMACIA,-12.50,Salud
OPTICA,-85.00,Salud
DENTISTA,-120.00,Salud
FISIOTERAPIA,-45.00,Salud
SEGURO DENTAL,-23.00,Salud
SPOTIFY,-9.99,Suscripciones
NETFLIX,-17.99,Suscripciones
HBO MAX,-8.99,Suscripciones
AMAZON PRIME,-4.99,Suscripciones
DISNEY PLUS,-8.99,Suscripciones
YOUTUBE PREMIUM,-11.99,Suscripciones
APPLE ICLOUD,-2.99,Suscripciones
CHATGPT PLUS,-20.00,Suscripciones
GIMNASIO,-39.90,Suscripciones
CINE,-9.50,Ocio
STEAM,-29.99,Ocio
PLAYSTATION STORE,-14.99,Ocio
FNAC,-25.00,Ocio
CONCIERTO,-55.00,Ocio
ZARA,-45.00,Ropa
PULL AND BEAR,-32.00,Ropa
HM,-28.50,Ropa
MANGO,-55.00,Ropa
PRIMARK,-22.00,Ropa
AMAZON,-35.00,Otros gastos
EL CORTE INGLES,-85.00,Otros gastos
ALIEXPRESS,-12.50,Otros gastos
MAPFRE,-185.00,Seguros
LINEA DIRECTA,-120.00,Seguros
MUTUA MADRILENA,-95.00,Seguros
ZURICH,-150.00,Seguros
NOMINA EMPRESA,-2200.00,Nómina
TRANSFERENCIA NOMINA,-1850.00,Nómina
PAGO NOMINA,-2450.00,Nómina
BIZUM RECIBIDO,-25.00,Transferencias recibidas
TRANSFERENCIA RECIBIDA,-150.00,Transferencias recibidas
DEVOLUCION AMAZON,-35.00,Devoluciones
DEVOLUCION COMPRA,-22.50,Devoluciones
```

> **Nota**: Este es un dataset mínimo (~80 filas). Para un modelo robusto, amplía a 300-500 filas con variaciones (mayúsculas, con/sin S.A., con ciudad, etc.). Por ejemplo: "MERCADONA S.A. SEVILLA", "MERCADONA MAIRENA", "COMPRA MERCADONA", etc.

---

## 4. Paso 3: Limpieza de Texto Bancario

Crea `app/categories/text_cleaner.py`:

```python
"""Bank description text cleaner for categorization.

Removes noise from raw bank descriptions (card numbers, dates,
operation codes) and extracts the merchant name.
"""
import re
import unicodedata


# Prefijos habituales de operaciones bancarias españolas
BANK_PREFIXES = [
    r"COMPRA\s+(?:CON\s+)?TARJ(?:ETA)?\.?\s*\d*",
    r"PAGO\s+(?:EN\s+)?COMERCIO",
    r"PAGO\s+(?:CON\s+)?TARJ(?:ETA)?",
    r"RECIBO\s+(?:DOMICILIADO)?",
    r"ADEUDO\s+(?:DIRECTO\s+)?SEPA",
    r"TRANSFERENCIA\s+(?:A|DE|EMITIDA|RECIBIDA)?",
    r"BIZUM\s+(?:A|DE|ENVIADO|RECIBIDO)?",
    r"RETIRADA\s+(?:DE\s+)?EFECTIVO",
    r"COMISION(?:ES)?",
    r"CARGO\s+POR",
    r"PAGO\s+MOVIL",
    r"OPERACION\s+ONLINE",
    r"COBRO\s+EN",
]

# Patrones de ruido
NOISE_PATTERNS = [
    r"\b\d{4}\s*\*{4,}\s*\d{4}\b",  # Números de tarjeta: 4921 **** 1234
    r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b",  # Fechas: 10/04/2025
    r"\b\d{2}\.\d{2}\.\d{2,4}\b",  # Fechas: 10.04.2025
    r"\bREF[\s.:]*\w+\b",  # Referencias: REF123456
    r"\bN[ºO]?\s*\d+\b",  # Números de operación: Nº 123456
    r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",  # IBAN
    r"\bES\d{18,22}\b",
    r"\bCONCEPTO[\s:]+",
    r"\bCOM\.\s*\d+[.,]\d+\b",  # Comisiones embebidas
    r"\b\d{6,}\b",  # Secuencias largas de dígitos (>= 6)
    r"\bOFICINA\s+\d+\b",
    r"\bSUCURSAL\s+\d+\b",
]

# Sufijos corporativos
CORPORATE_SUFFIXES = [
    r"\s+S\.?A\.?U?\.?$",
    r"\s+S\.?L\.?U?\.?$",
    r"\s+S\.?C\.?$",
    r"\s+SOCIEDAD\s+\w+$",
    r"\s+COOP\.?$",
]


def normalize_text(text: str) -> str:
    """Remove accents and convert to uppercase ASCII."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text.upper().strip()


def clean_bank_description(raw_description: str) -> str:
    """Clean a raw bank transaction description.

    Steps:
    1. Normalize (uppercase, remove accents)
    2. Remove bank operation prefixes
    3. Remove noise (card numbers, dates, references)
    4. Remove corporate suffixes
    5. Strip extra whitespace

    Args:
        raw_description: Raw description from the bank API.

    Returns:
        Cleaned merchant name, e.g. "MERCADONA"
    """
    text = normalize_text(raw_description)

    # Remove bank prefixes
    for pattern in BANK_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove noise patterns
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove corporate suffixes
    for pattern in CORPORATE_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove extra whitespace and special chars at edges
    text = re.sub(r"[*/#\-_.,;:()]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_merchant_key(cleaned_description: str) -> str:
    """Generate a normalized key for merchant mapping lookups.

    Takes the first 2 significant words (ignoring 1-2 char words).
    E.g., "MERCADONA MAIRENA DEL ALJARAFE" → "MERCADONA MAIRENA"
    """
    words = cleaned_description.split()
    significant = [w for w in words if len(w) > 2]
    key_words = significant[:2] if len(significant) >= 2 else significant[:1]
    return " ".join(key_words).upper()
```

---

## 5. Paso 4: Motor ML (`ml_categorizer`)

Crea `app/categories/ml_categorizer.py`:

```python
"""ML-based transaction categorizer.

Uses TF-IDF + GradientBoosting for text classification.
Supports training, prediction with confidence scores,
and model persistence via joblib.
"""
import logging
import os
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, LabelEncoder

from app.categories.text_cleaner import clean_bank_description

logger = logging.getLogger(__name__)

# Default path for the serialized model
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "categorizer_model.joblib"
ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"


class TransactionCategorizer:
    """ML categorizer with TF-IDF text features + numerical features.

    Usage:
        categorizer = TransactionCategorizer()
        categorizer.train(training_df)  # DataFrame with columns: description, amount, category
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
            test_size: Fraction of data for cross-validation.

        Returns:
            Dict with training metrics: accuracy, cv_mean, cv_std, n_samples, n_classes.
        """
        # Clean descriptions
        df = df.copy()
        df["clean_desc"] = df["description"].apply(clean_bank_description)

        # Encode labels
        y = self.label_encoder.fit_transform(df["category"])

        # Feature engineering
        df["abs_amount"] = df["amount"].abs()
        df["log_amount"] = np.log1p(df["abs_amount"])
        df["is_income"] = (df["amount"] > 0).astype(int)

        # Build pipeline
        text_features = Pipeline([
            ("tfidf", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 4),
                max_features=3000,
                lowercase=True,
                strip_accents="unicode",
            )),
        ])

        numeric_features = Pipeline([
            ("passthrough", FunctionTransformer(validate=False)),
        ])

        preprocessor = ColumnTransformer(
            transformers=[
                ("text", text_features, "clean_desc"),
                ("nums", numeric_features, ["log_amount", "is_income"]),
            ],
            remainder="drop",
        )

        self.pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                min_samples_leaf=2,
                random_state=42,
            )),
        ])

        # Prepare feature DataFrame
        X = df[["clean_desc", "log_amount", "is_income"]]

        # Cross-validate
        cv_scores = cross_val_score(self.pipeline, X, y, cv=min(5, len(df) // 5 or 2), scoring="accuracy")

        # Train on full dataset
        self.pipeline.fit(X, y)
        self._is_trained = True

        # Metrics
        metrics = {
            "accuracy": float(self.pipeline.score(X, y)),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "n_samples": len(df),
            "n_classes": len(self.label_encoder.classes_),
            "classes": list(self.label_encoder.classes_),
            "trained_at": datetime.utcnow().isoformat(),
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
        self, description: str, amount: float
    ) -> tuple[str, float]:
        """Predict category for a single transaction.

        Args:
            description: Raw or cleaned bank description.
            amount: Transaction amount (negative for expenses).

        Returns:
            Tuple of (category_name, confidence_score).

        Raises:
            RuntimeError: If model hasn't been trained/loaded.
        """
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        clean_desc = clean_bank_description(description)
        abs_amount = abs(amount)
        log_amount = np.log1p(abs_amount)
        is_income = 1 if amount > 0 else 0

        X = pd.DataFrame([{
            "clean_desc": clean_desc,
            "log_amount": log_amount,
            "is_income": is_income,
        }])

        # Get prediction probabilities
        proba = self.pipeline.predict_proba(X)[0]
        predicted_idx = int(np.argmax(proba))
        confidence = float(proba[predicted_idx])

        category_name = self.label_encoder.inverse_transform([predicted_idx])[0]
        return category_name, confidence

    def predict_batch(
        self, descriptions: list[str], amounts: list[float]
    ) -> list[tuple[str, float]]:
        """Predict categories for a batch of transactions."""
        if not self._is_trained or self.pipeline is None:
            raise RuntimeError("Model not trained.")

        clean_descs = [clean_bank_description(d) for d in descriptions]
        abs_amounts = [abs(a) for a in amounts]
        log_amounts = [np.log1p(a) for a in abs_amounts]
        is_incomes = [1 if a > 0 else 0 for a in amounts]

        X = pd.DataFrame({
            "clean_desc": clean_descs,
            "log_amount": log_amounts,
            "is_income": is_incomes,
        })

        probas = self.pipeline.predict_proba(X)
        results = []
        for proba in probas:
            idx = int(np.argmax(proba))
            conf = float(proba[idx])
            cat = self.label_encoder.inverse_transform([idx])[0]
            results.append((cat, conf))
        return results

    def save(self, model_path: Path | None = None, encoder_path: Path | None = None) -> None:
        """Persist model and label encoder to disk."""
        model_path = model_path or MODEL_PATH
        encoder_path = encoder_path or ENCODER_PATH
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, model_path)
        joblib.dump(self.label_encoder, encoder_path)
        logger.info("Model saved to %s", model_path)

    @classmethod
    def load(cls, model_path: Path | None = None, encoder_path: Path | None = None) -> "TransactionCategorizer":
        """Load a trained model from disk."""
        model_path = model_path or MODEL_PATH
        encoder_path = encoder_path or ENCODER_PATH

        if not model_path.exists():
            raise FileNotFoundError(f"No model found at {model_path}. Train first.")

        instance = cls()
        instance.pipeline = joblib.load(model_path)
        instance.label_encoder = joblib.load(encoder_path)
        instance._is_trained = True
        logger.info("Model loaded from %s", model_path)
        return instance
```

### Script para entrenar el modelo base

Crea `backend/scripts/train_base_model.py`:

```python
"""One-time script to train the base categorization model.

Usage:
    cd backend
    python -m scripts.train_base_model
"""
import pandas as pd
from pathlib import Path

from app.categories.ml_categorizer import TransactionCategorizer

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "training_data.csv"


def main() -> None:
    print("Loading training data...")
    df = pd.read_csv(DATA_PATH)
    print(f"  {len(df)} samples, {df['category'].nunique()} categories")

    print("Training model...")
    categorizer = TransactionCategorizer()
    metrics = categorizer.train(df)

    print(f"\nTraining results:")
    print(f"  Accuracy: {metrics['accuracy']:.3f}")
    print(f"  Cross-val: {metrics['cv_mean']:.3f} ± {metrics['cv_std']:.3f}")
    print(f"  Classes: {metrics['n_classes']}")

    print("\nSaving model...")
    categorizer.save()
    print("Done! Model saved to data/models/")

    # Quick test
    print("\nQuick test predictions:")
    tests = [
        ("MERCADONA S.A. SEVILLA", -65.30),
        ("SPOTIFY TECHNOLOGY", -9.99),
        ("REPSOL GASOLINERA", -52.00),
        ("TRANSFERENCIA NOMINA EMPRESA S.L.", 2200.00),
        ("BIZUM DE JUAN", 15.00),
    ]
    for desc, amount in tests:
        cat, conf = categorizer.predict(desc, amount)
        print(f"  {desc:45s} {amount:>10.2f}€ → {cat:25s} ({conf:.2%})")


if __name__ == "__main__":
    main()
```

---

## 6. Paso 5: Servicio de Categorización

Crea `app/categories/service.py`:

```python
"""Categorization service — orchestrates the 3-layer cascade.

Layer 1: Merchant mapping (exact match from user corrections)
Layer 2: ML model prediction
Layer 3: Confidence threshold (auto / suggested / uncategorized)
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.ml_categorizer import TransactionCategorizer
from app.categories.models import Category, CategoryCorrection
from app.categories.merchant_mapping import MerchantMapping
from app.categories.text_cleaner import clean_bank_description, extract_merchant_key
from app.transactions.models import Transaction

logger = logging.getLogger(__name__)

# Confidence thresholds
THRESHOLD_AUTO = 0.70       # Above → assign automatically
THRESHOLD_SUGGEST = 0.40    # Between suggest and auto → mark as "suggested"
                             # Below suggest → uncategorized

# Singleton: loaded once, reloaded on retrain
_categorizer: TransactionCategorizer | None = None


def get_categorizer() -> TransactionCategorizer:
    """Get or load the ML categorizer singleton."""
    global _categorizer
    if _categorizer is None:
        try:
            _categorizer = TransactionCategorizer.load()
        except FileNotFoundError:
            logger.warning("No trained model found. Run train_base_model.py first.")
            _categorizer = TransactionCategorizer()
    return _categorizer


def reload_categorizer() -> None:
    """Force reload of the model (called after retraining)."""
    global _categorizer
    _categorizer = None
    get_categorizer()


async def categorize_transaction(
    db: AsyncSession,
    transaction: Transaction,
    user_id: uuid.UUID,
) -> Transaction:
    """Categorize a single transaction using the 3-layer cascade.

    Modifies the transaction in place and returns it.
    """
    raw_desc = transaction.description or ""
    amount = float(transaction.amount or 0)

    cleaned = clean_bank_description(raw_desc)
    merchant_key = extract_merchant_key(cleaned)

    # ── Layer 1: Merchant mapping ──
    mapping = await _lookup_merchant_mapping(db, user_id, merchant_key)
    if mapping:
        transaction.category_id = mapping.category_id
        transaction.confidence_score = 1.0
        transaction.categorization_method = "merchant_map"
        logger.debug("Merchant map hit: %s → %s", merchant_key, mapping.category_id)
        return transaction

    # ── Layer 2: ML prediction ──
    categorizer = get_categorizer()
    if categorizer.is_trained:
        predicted_name, confidence = categorizer.predict(raw_desc, amount)

        # Resolve category name → id
        category = await _resolve_category_by_name(db, predicted_name, user_id)
        if category:
            transaction.category_id = category.id
            transaction.confidence_score = confidence

            # ── Layer 3: Threshold ──
            if confidence >= THRESHOLD_AUTO:
                transaction.categorization_method = "ml_auto"
            elif confidence >= THRESHOLD_SUGGEST:
                transaction.categorization_method = "ml_suggested"
            else:
                transaction.categorization_method = "ml_suggested"
                # Still assign the prediction, but mark low confidence

            logger.debug(
                "ML prediction: %s → %s (%.2f, %s)",
                cleaned, predicted_name, confidence, transaction.categorization_method,
            )
            return transaction

    # ── Fallback: uncategorized ──
    transaction.category_id = None
    transaction.confidence_score = 0.0
    transaction.categorization_method = None
    logger.debug("No categorization for: %s", cleaned)
    return transaction


async def categorize_batch(
    db: AsyncSession,
    transactions: list[Transaction],
    user_id: uuid.UUID,
) -> list[Transaction]:
    """Categorize a list of transactions."""
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

    Steps:
      1. Update the corrected transaction (manual, confidence=1.0).
      2. Persist a CategoryCorrection for future model retraining.
      3. Upsert merchant mapping (fires on next bank sync).
      4. Propagate immediately to every other non-manually-corrected
         transaction that shares the same merchant key via
         _recategorize_same_merchant().

    Returns:
        (transaction, also_updated) — also_updated is the count of
        additional transactions updated beyond the one corrected.

    Propagation performance: ~30 ms for 500 transactions (no ML inference).
    """
    # 1. Fetch transaction
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    # 2. Store correction for retraining
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

    # 3. Update transaction
    transaction.category_id = new_category_id
    transaction.confidence_score = 1.0
    transaction.categorization_method = "manual"
    transaction.is_manually_corrected = True

    # 4. Upsert merchant mapping (future syncs)
    await _upsert_merchant_mapping(db, user_id, merchant_key, new_category_id)

    # 5. Propagate to existing transactions with the same merchant
    also_updated = await _recategorize_same_merchant(
        db, user_id=user_id, merchant_key=merchant_key,
        category_id=new_category_id, exclude_transaction_id=transaction_id,
    )

    await db.flush()
    await db.refresh(transaction)

    logger.info(
        "Category corrected: tx=%s, merchant=%s → category=%s (%d additional updated)",
        transaction_id, merchant_key, new_category_id, also_updated,
    )
    return transaction, also_updated


async def _recategorize_same_merchant(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
    exclude_transaction_id: uuid.UUID,
) -> int:
    """Update all non-manually-corrected transactions that share *merchant_key*.

    Avoids the ML pipeline entirely — fetches descriptions, filters in Python
    with extract_merchant_key(), and issues a single bulk UPDATE.
    Benchmarked at ~30 ms for 500 transactions.

    Returns the number of transactions updated.
    """
    if not merchant_key:
        return 0

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
    return len(matching_ids)


async def get_user_categories(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Category]:
    """Get all categories available to a user (global + custom)."""
    result = await db.execute(
        select(Category).where(
            (Category.user_id == None) | (Category.user_id == user_id)  # noqa: E711
        ).order_by(Category.type, Category.name)
    )
    return list(result.scalars().all())


async def create_custom_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    icon: str,
    color: str,
    type: str,
) -> Category:
    """Create a custom category for a user."""
    category = Category(
        name=name,
        icon=icon,
        color=color,
        type=type,
        is_custom=True,
        user_id=user_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# ── Private helpers ──

async def _lookup_merchant_mapping(
    db: AsyncSession, user_id: uuid.UUID, merchant_key: str
) -> MerchantMapping | None:
    """Look up a merchant→category mapping for a user."""
    result = await db.execute(
        select(MerchantMapping).where(
            MerchantMapping.user_id == user_id,
            MerchantMapping.merchant_name == merchant_key,
        )
    )
    return result.scalar_one_or_none()


async def _resolve_category_by_name(
    db: AsyncSession, name: str, user_id: uuid.UUID
) -> Category | None:
    """Find a category by name (global or user-owned)."""
    result = await db.execute(
        select(Category).where(
            Category.name == name,
            (Category.user_id == None) | (Category.user_id == user_id),  # noqa: E711
        )
    )
    return result.scalar_one_or_none()


async def _upsert_merchant_mapping(
    db: AsyncSession,
    user_id: uuid.UUID,
    merchant_key: str,
    category_id: uuid.UUID,
) -> None:
    """Create or update a merchant mapping."""
    existing = await _lookup_merchant_mapping(db, user_id, merchant_key)
    if existing:
        existing.category_id = category_id
        existing.confidence += 1
    else:
        mapping = MerchantMapping(
            user_id=user_id,
            merchant_name=merchant_key,
            category_id=category_id,
        )
        db.add(mapping)
```

---

## 7. Paso 6: API Endpoints

### 7.1 Schemas — `app/categories/schemas.py`

```python
"""Pydantic schemas for categories and categorization."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Category ──

class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    icon: str
    color: str
    type: str  # "expense" | "income"
    is_custom: bool

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(default="tag", max_length=50)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    type: str = Field(..., pattern=r"^(expense|income)$")


# ── Category Correction ──

class CategoryCorrectionRequest(BaseModel):
    category_id: uuid.UUID


class CategoryCorrectionResponse(BaseModel):
    transaction_id: uuid.UUID
    old_category_id: uuid.UUID | None
    new_category_id: uuid.UUID
    confidence_score: float

    model_config = {"from_attributes": True}


# ── Categorization Stats ──

class CategorizationStatsResponse(BaseModel):
    total_transactions: int
    auto_categorized: int
    manually_corrected: int
    uncategorized: int
    merchant_map_coverage: float  # 0.0 - 1.0
    model_accuracy: float | None
```

### 7.2 Router — `app/categories/router.py`

```python
"""Categories and categorization API endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.auth.models import User
from app.categories import service
from app.categories.schemas import (
    CategoryCorrectionRequest,
    CategoryCreate,
    CategoryResponse,
)

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all categories available to the current user."""
    return await service.get_user_categories(db, current_user.id)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a custom category."""
    return await service.create_custom_category(
        db,
        user_id=current_user.id,
        name=data.name,
        icon=data.icon,
        color=data.color,
        type=data.type,
    )


@router.patch(
    "/transactions/{transaction_id}/category",
    response_model=dict,
)
async def correct_transaction_category(
    transaction_id: uuid.UUID,
    data: CategoryCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Correct the category of a transaction (active learning)."""
    try:
        tx = await service.correct_category(
            db,
            user_id=current_user.id,
            transaction_id=transaction_id,
            new_category_id=data.category_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "transaction_id": str(tx.id),
        "category_id": str(tx.category_id),
        "confidence_score": tx.confidence_score,
        "method": tx.categorization_method,
    }
```

### 7.3 Registrar el router en `app/main.py`

```python
from app.categories.router import router as categories_router

app.include_router(categories_router)
```

---

## 8. Paso 7: Tarea Celery de Reentrenamiento

Crea `app/categories/tasks.py`:

```python
"""Celery tasks for ML model retraining.

NOTE: If Celery is not yet configured in the project,
this can be run as a standalone script initially.
See the sync version at the bottom.
"""
import logging
from datetime import datetime

import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

from app.categories.ml_categorizer import TransactionCategorizer
from app.categories.service import reload_categorizer
from app.config import settings

logger = logging.getLogger(__name__)

# Base training data
BASE_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "training_data.csv"


def retrain_model() -> dict:
    """Retrain the categorization model with base data + all user corrections.

    This is a SYNC function (ML training is CPU-bound).
    Can be called from Celery or directly.

    Returns:
        Training metrics dict.
    """
    # Use sync database connection for training
    sync_db_url = str(settings.DATABASE_URL).replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
    # Alternatively, use a dedicated sync URL in config
    engine = create_engine(sync_db_url)

    # 1. Load base training data
    base_df = pd.read_csv(BASE_DATA_PATH)
    logger.info("Base training data: %d rows", len(base_df))

    # 2. Load user corrections from database
    with engine.connect() as conn:
        corrections_query = text("""
            SELECT
                cc.original_description AS description,
                cc.amount,
                c.name AS category
            FROM category_corrections cc
            JOIN categories c ON c.id = cc.corrected_category_id
        """)
        corrections_df = pd.read_sql(corrections_query, conn)
    logger.info("User corrections: %d rows", len(corrections_df))

    # 3. Combine datasets (corrections have higher weight)
    # Duplicate corrections to give them more influence
    if not corrections_df.empty:
        weighted_corrections = pd.concat([corrections_df] * 3, ignore_index=True)
        combined_df = pd.concat([base_df, weighted_corrections], ignore_index=True)
    else:
        combined_df = base_df

    logger.info("Combined training data: %d rows", len(combined_df))

    # 4. Train
    categorizer = TransactionCategorizer()
    metrics = categorizer.train(combined_df)

    # 5. Save
    categorizer.save()

    # 6. Reload singleton in memory
    reload_categorizer()

    logger.info("Model retrained successfully: %s", metrics)
    return metrics


# ── Celery task wrapper (when Celery is configured) ──

# from celery import shared_task
#
# @shared_task(name="retrain_categorization_model")
# def retrain_categorization_model_task():
#     """Celery task to retrain the model."""
#     return retrain_model()


# ── Standalone execution ──

if __name__ == "__main__":
    """Run retraining directly: python -m app.categories.tasks"""
    logging.basicConfig(level=logging.INFO)
    metrics = retrain_model()
    print(f"Retraining complete: {metrics}")
```

### Cuándo disparar el reentrenamiento

Tienes varias opciones (implementa la que mejor se ajuste a tu fase):

**Opción A — Manual (MVP):**
Añade un endpoint admin:

```python
@router.post("/admin/retrain", include_in_schema=False)
async def trigger_retrain(current_user: User = Depends(get_current_user)):
    """Manually trigger model retraining."""
    from app.categories.tasks import retrain_model
    metrics = retrain_model()
    return {"status": "ok", "metrics": metrics}
```

**Opción B — Cada N correcciones:**
En `service.py`, después de guardar una corrección, cuenta las correcciones pendientes:

```python
# En correct_category(), después del commit:
correction_count = await _count_corrections_since_last_train(db)
if correction_count >= 50:  # threshold configurable
    # Si tienes Celery:
    # retrain_categorization_model_task.delay()
    # Si no, ejecutar en background thread:
    import threading
    threading.Thread(target=retrain_model, daemon=True).start()
```

**Opción C — Celery Beat (producción):**
Programar reentrenamiento nocturno (ej: 3:00 AM).

---

## 9. Paso 8: Integración con Sincronización Bancaria

Modifica `app/transactions/service.py` para que las transacciones nuevas se categoricen automáticamente al sincronizar.

Busca la función que guarda nuevas transacciones (probablemente algo como `sync_transactions` o `fetch_and_store_transactions`) y añade la categorización:

```python
# Al final de la función que crea/guarda nuevas transacciones:

from app.categories.service import categorize_batch

async def sync_account_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    raw_transactions: list[dict],
) -> list[Transaction]:
    """Sync transactions from bank and categorize them."""

    new_transactions = []
    for raw_tx in raw_transactions:
        # ... tu lógica existente de crear Transaction ...
        tx = Transaction(
            # ... campos existentes ...
        )
        db.add(tx)
        new_transactions.append(tx)

    await db.flush()  # Para que tengan IDs asignados

    # ── CATEGORIZACIÓN AUTOMÁTICA ──
    await categorize_batch(db, new_transactions, user_id)

    await db.commit()
    return new_transactions
```

---

## 10. Paso 9: Frontend

### 10.1 Tipos TypeScript — `src/types/categories.ts`

```typescript
export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
  type: "expense" | "income";
  is_custom: boolean;
}

export interface TransactionWithCategory {
  id: string;
  description: string;
  amount: number;
  currency: string;
  date: string;
  account_id: string;
  category?: Category | null;
  categorization_method?: "merchant_map" | "ml_auto" | "ml_suggested" | "manual" | null;
  confidence_score?: number | null;
  is_manually_corrected: boolean;
}
```

### 10.2 API calls — `src/lib/api.ts`

Añade estas funciones a tu módulo de API existente:

```typescript
// Categories
export async function getCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/categories");
}

export async function createCategory(data: {
  name: string;
  icon: string;
  color: string;
  type: "expense" | "income";
}): Promise<Category> {
  return apiFetch<Category>("/categories", { method: "POST", body: data });
}

export async function correctTransactionCategory(
  transactionId: string,
  categoryId: string
): Promise<void> {
  return apiFetch(`/categories/transactions/${transactionId}/category`, {
    method: "PATCH",
    body: { category_id: categoryId },
  });
}
```

### 10.3 Hook — `src/hooks/useCategories.ts`

```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCategories, correctTransactionCategory } from "@/lib/api";

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
    staleTime: 1000 * 60 * 10, // 10 min cache
  });
}

export function useCorrectionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      categoryId,
    }: {
      transactionId: string;
      categoryId: string;
    }) => correctTransactionCategory(transactionId, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}
```

### 10.4 Componente CategoryBadge — `src/components/features/CategoryBadge.tsx`

```tsx
"use client";

interface CategoryBadgeProps {
  name: string;
  color: string;
  icon?: string;
  confidence?: number | null;
  method?: string | null;
}

export function CategoryBadge({
  name,
  color,
  confidence,
  method,
}: CategoryBadgeProps) {
  const isLowConfidence = method === "ml_suggested" && (confidence ?? 0) < 0.7;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium
        ${isLowConfidence ? "border border-dashed border-current opacity-70" : ""}`}
      style={{
        backgroundColor: `${color}20`,
        color: color,
      }}
    >
      {name}
      {isLowConfidence && (
        <span title="Categoría sugerida — haz clic para confirmar o cambiar">
          ?
        </span>
      )}
    </span>
  );
}
```

### 10.5 Selector de categoría en TransactionRow

En tu componente de fila de transacción (`TransactionRow` o similar), añade la funcionalidad de edición:

```tsx
"use client";

import { useState } from "react";
import { useCategories, useCorrectionMutation } from "@/hooks/useCategories";
import { CategoryBadge } from "./CategoryBadge";
import type { TransactionWithCategory, Category } from "@/types/categories";

interface TransactionRowProps {
  transaction: TransactionWithCategory;
}

export function TransactionRow({ transaction }: TransactionRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const { data: categories } = useCategories();
  const correction = useCorrectionMutation();

  const handleCategorySelect = (categoryId: string) => {
    correction.mutate(
      { transactionId: transaction.id, categoryId },
      {
        onSuccess: () => setIsEditing(false),
      }
    );
  };

  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="px-4 py-3 text-sm text-gray-600">
        {new Date(transaction.date).toLocaleDateString("es-ES")}
      </td>
      <td className="px-4 py-3 text-sm font-medium">
        {transaction.description}
      </td>
      <td className="px-4 py-3">
        {isEditing ? (
          <div className="flex flex-wrap gap-1">
            {categories
              ?.filter(
                (c) =>
                  c.type ===
                  (transaction.amount < 0 ? "expense" : "income")
              )
              .map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => handleCategorySelect(cat.id)}
                  className="rounded-full px-2 py-0.5 text-xs hover:opacity-80 transition"
                  style={{
                    backgroundColor: `${cat.color}20`,
                    color: cat.color,
                  }}
                >
                  {cat.name}
                </button>
              ))}
            <button
              onClick={() => setIsEditing(false)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Cancelar
            </button>
          </div>
        ) : (
          <button onClick={() => setIsEditing(true)} className="group">
            {transaction.category ? (
              <CategoryBadge
                name={transaction.category.name}
                color={transaction.category.color}
                confidence={transaction.confidence_score}
                method={transaction.categorization_method}
              />
            ) : (
              <span className="text-xs text-gray-400 group-hover:text-blue-500">
                + Categorizar
              </span>
            )}
          </button>
        )}
      </td>
      <td
        className={`px-4 py-3 text-sm font-semibold text-right ${
          transaction.amount > 0 ? "text-green-600" : "text-gray-900"
        }`}
      >
        {transaction.amount > 0 ? "+" : ""}
        {transaction.amount.toFixed(2)} €
      </td>
    </tr>
  );
}
```

---

## 11. Paso 10: Tests

### 11.1 Test del text cleaner — `tests/categories/test_text_cleaner.py`

```python
"""Tests for bank description text cleaner."""
import pytest

from app.categories.text_cleaner import clean_bank_description, extract_merchant_key


class TestCleanBankDescription:

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("COMPRA TARJ 4921*****1234 MERCADONA S.A. SEVILLA", "MERCADONA SEVILLA"),
            ("RECIBO DOMICILIADO ENDESA ENERGIA S.A.", "ENDESA ENERGIA"),
            ("BIZUM A JUAN GARCIA REF123456", "JUAN GARCIA"),
            ("PAGO MOVIL SPOTIFY TECHNOLOGY 12/04/2025", "SPOTIFY TECHNOLOGY"),
            ("TRANSFERENCIA NOMINA EMPRESA SL", "NOMINA EMPRESA"),
            ("ADEUDO DIRECTO SEPA NETFLIX", "NETFLIX"),
        ],
    )
    def test_removes_noise(self, raw: str, expected: str) -> None:
        result = clean_bank_description(raw)
        assert expected in result or result in expected

    def test_normalizes_accents(self) -> None:
        result = clean_bank_description("Café París")
        assert "CAFE" in result
        assert "PARIS" in result


class TestExtractMerchantKey:

    def test_takes_first_two_significant_words(self) -> None:
        assert extract_merchant_key("MERCADONA MAIRENA DEL ALJARAFE") == "MERCADONA MAIRENA"

    def test_skips_short_words(self) -> None:
        assert extract_merchant_key("EL CORTE INGLES SEVILLA") == "CORTE INGLES"

    def test_single_word(self) -> None:
        assert extract_merchant_key("NETFLIX") == "NETFLIX"
```

### 11.2 Test del ML categorizer — `tests/categories/test_ml_categorizer.py`

```python
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
    ] * 5)  # Repeat for minimum samples


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
```

---

## 12. Resumen de Archivos

### Archivos nuevos a crear

| Archivo | Propósito |
|---------|-----------|
| `app/categories/__init__.py` | Paquete del dominio de categorías |
| `app/categories/models.py` | Modelos Category, CategoryCorrection |
| `app/categories/merchant_mapping.py` | Modelo MerchantMapping |
| `app/categories/schemas.py` | Schemas Pydantic de la API |
| `app/categories/router.py` | Endpoints REST |
| `app/categories/service.py` | Lógica de negocio (cascada 3 capas) |
| `app/categories/text_cleaner.py` | Limpieza de texto bancario |
| `app/categories/ml_categorizer.py` | Motor ML (TF-IDF + GradientBoosting) |
| `app/categories/seed.py` | Categorías predefinidas del sistema |
| `app/categories/tasks.py` | Tarea de reentrenamiento |
| `backend/data/training_data.csv` | Dataset base de entrenamiento |
| `backend/scripts/train_base_model.py` | Script para entrenar modelo inicial |
| `frontend/src/types/categories.ts` | Tipos TypeScript |
| `frontend/src/hooks/useCategories.ts` | React Query hooks |
| `frontend/src/components/features/CategoryBadge.tsx` | Badge visual |
| `tests/categories/test_text_cleaner.py` | Tests de limpieza de texto |
| `tests/categories/test_ml_categorizer.py` | Tests del modelo ML |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `app/transactions/models.py` | Añadir campos: category_id, confidence_score, categorization_method, is_manually_corrected |
| `app/transactions/service.py` | Integrar categorize_batch() tras sincronizar |
| `app/transactions/schemas.py` | Incluir category en TransactionResponse |
| `app/main.py` | Incluir categories_router |
| `alembic/env.py` | Importar nuevos modelos |
| `backend/requirements.txt` | Añadir scikit-learn, joblib |
| `frontend/src/lib/api.ts` | Añadir funciones de categorías |
| `CLAUDE.md` | Actualizar fase y estructura |

### Orden de ejecución

1. Instalar dependencias: `pip install scikit-learn joblib`
2. Crear todos los archivos del dominio `app/categories/`
3. Modificar `app/transactions/models.py`
4. Crear y ejecutar migración Alembic
5. Crear `data/training_data.csv`
6. Ejecutar seed de categorías (en un script o al arrancar la app)
7. Entrenar modelo base: `python -m scripts.train_base_model`
8. Registrar router en `main.py`
9. Integrar categorización en sincronización bancaria
10. Implementar componentes frontend
11. Ejecutar tests
