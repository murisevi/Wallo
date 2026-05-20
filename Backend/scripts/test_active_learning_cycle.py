"""End-to-end verification of the active-learning cycle.

Tests the full loop:
    correction manual → merchant mapping → reentrenamiento → mejora del modelo

Usage (from /backend):
    python -m scripts.test_active_learning_cycle
    python -m scripts.test_active_learning_cycle --email user@example.com --password secret
    python -m scripts.test_active_learning_cycle --base-url http://localhost:8000/api/v1
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any

import httpx
import pandas as pd
from sqlalchemy import create_engine, text

from app.categories.ml_categorizer import TransactionCategorizer
from app.categories.tasks import retrain_model
from app.categories.text_cleaner import clean_bank_description, extract_merchant_key
from app.config import settings

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)-8s %(name)s — %(message)s",
)

# ── Colour helpers ─────────────────────────────────────────────────────────────

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"


def ok(msg: str) -> str:
    return f"{GREEN}PASS{RESET}  {msg}"


def fail(msg: str) -> str:
    return f"{RED}FAIL{RESET}  {msg}"


def header(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")


def subheader(msg: str) -> None:
    print(f"\n{BOLD}── {msg} {'─'*(60 - len(msg))}{RESET}")


# ── Keyword → category heuristic (mirrors the spec in the task) ───────────────

_KEYWORD_RULES: list[tuple[list[str], str]] = [
    (
        ["CAFETERIA", "COFFEE", "COFFE", "BAR ", "RESTAURANTE", "TAPAS",
         "BURGER", "PIZZA", "KEBAB", "MCDONALDS", "KFC", "TELEPIZZA",
         "GLOVO", "UBER EATS", "JUST EAT", "STARBUCKS"],
        "Restaurantes y Bares",
    ),
    (
        ["MERCADONA", "CARREFOUR", "LIDL", "ALDI", "SUPERMERCADO", "DIA ",
         "MARKET", "HIPERCOR", "EROSKI", "CONSUM", "ALCAMPO", "COVIRAN",
         "SPAR", "BONPREU", "FROIZ"],
        "Alimentación",
    ),
    (
        ["HOTEL", "BOOKING", "AIRBNB", "HOSTEL"],
        "Ocio",
    ),
    (
        ["FARMACIA", "OPTICA", "DENTIST", "CLINICA", "MEDICO", "HOSPITAL",
         "SALUD", "DOCTOR"],
        "Salud",
    ),
    (
        ["GASOLINERA", "REPSOL", "CEPSA", "PARKING", "RENFE", "CABIFY",
         "UBER ", "BOLT", "METRO", "AUTOBUS", "TUSSAM", "PEAJE",
         "COMBUSTIBLE", "GASOLINA"],
        "Transporte",
    ),
    (
        ["PAYPAL", "AMAZON", "ALIEXPRESS", "EBAY"],
        "Otros gastos",
    ),
]


def guess_correct_category(description: str) -> str:
    """Best-effort heuristic to decide the correct category from the description."""
    upper = description.upper()
    for keywords, category in _KEYWORD_RULES:
        if any(kw in upper for kw in keywords):
            return category
    return "Otros gastos"


# ── Sync DB helpers ────────────────────────────────────────────────────────────

def _sync_db_url() -> str:
    url = str(settings.database_url)
    return url.replace("+asyncpg", "+psycopg2")


def make_engine():  # type: ignore[return]
    return create_engine(_sync_db_url(), pool_pre_ping=True)


# ── API helpers ────────────────────────────────────────────────────────────────

@dataclass
class ApiClient:
    base_url: str
    token: str = ""

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def login(self, email: str, password: str) -> bool:
        resp = httpx.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
            return True
        print(f"  {RED}Login failed: {resp.status_code} — {resp.text}{RESET}")
        return False

    def patch_category(self, transaction_id: str, category_id: str) -> dict[str, Any]:
        resp = httpx.patch(
            f"{self.base_url}/categories/transactions/{transaction_id}/category",
            json={"category_id": category_id},
            headers=self.headers(),
            timeout=10,
        )
        return {"status_code": resp.status_code, "body": resp.json()}

    def get_categories(self) -> list[dict[str, Any]]:
        resp = httpx.get(
            f"{self.base_url}/categories/",
            headers=self.headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[return-value]


# ── Main verification logic ────────────────────────────────────────────────────

def run(email: str, password: str, base_url: str) -> bool:  # noqa: C901
    """Execute all 6 phases. Returns True if all checks passed."""

    failures: list[str] = []
    engine = make_engine()

    # ── Pre-flight: authenticate ───────────────────────────────────────────────
    header("Autenticación")
    api = ApiClient(base_url=base_url)
    if not api.login(email, password):
        print(f"\n{RED}No se pudo autenticar. Verifica las credenciales y que el "
              f"backend esté corriendo en {base_url}{RESET}")
        print("  Uso: python -m scripts.test_active_learning_cycle "
              "--email <email> --password <pwd>")
        return False
    print(f"  {GREEN}Login OK{RESET} — token obtenido")

    # Fetch category list from API (to resolve names → UUIDs)
    categories_raw = api.get_categories()
    cat_by_name: dict[str, str] = {c["name"]: c["id"] for c in categories_raw}
    print(f"  {len(cat_by_name)} categorías disponibles")

    # ══════════════════════════════════════════════════════════════════════════
    header("FASE 1 — Estado inicial")
    # ══════════════════════════════════════════════════════════════════════════

    with engine.connect() as conn:
        # 1a. Find poorly categorised transactions
        rows = conn.execute(
            text("""
                SELECT t.id, t.description, t.amount, t.confidence_score,
                       c.name AS category_name, t.categorization_method
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.is_manually_corrected = FALSE
                  AND (t.confidence_score < 0.6 OR t.confidence_score IS NULL)
                ORDER BY t.confidence_score ASC NULLS FIRST
                LIMIT 10
            """)
        ).fetchall()

        candidates = [dict(r._mapping) for r in rows]

        if not candidates:
            print(f"  {YELLOW}No hay transacciones con confianza < 0.6. "
                  "Buscando las 5 de menor confianza en general...{RESET}")
            rows2 = conn.execute(
                text("""
                    SELECT t.id, t.description, t.amount, t.confidence_score,
                           c.name AS category_name, t.categorization_method
                    FROM transactions t
                    LEFT JOIN categories c ON c.id = t.category_id
                    WHERE t.is_manually_corrected = FALSE
                    ORDER BY t.confidence_score ASC NULLS FIRST
                    LIMIT 5
                """)
            ).fetchall()
            candidates = [dict(r._mapping) for r in rows2]

        if not candidates:
            print(f"  {RED}No hay transacciones disponibles para corregir. "
                  "Sincroniza el banco primero.{RESET}")
            return False

        selected = candidates[:5]

        subheader("Transacciones seleccionadas (baja confianza)")
        print(f"  {'Descripción':<45} {'Categoría actual':<25} {'Confianza':>10}  Método")
        print(f"  {'-'*45} {'-'*25} {'-'*10}  {'-'*15}")
        for tx in selected:
            conf = f"{tx['confidence_score']:.2f}" if tx['confidence_score'] is not None else "N/A"
            cat = tx['category_name'] or "(sin categoría)"
            method = tx['categorization_method'] or "—"
            print(f"  {str(tx['description'])[:44]:<45} {cat:<25} {conf:>10}  {method}")

        # 1b. Count merchant_mappings and corrections BEFORE
        initial_mappings = conn.execute(
            text("SELECT COUNT(*) FROM merchant_mappings")
        ).scalar()
        initial_corrections = conn.execute(
            text("SELECT COUNT(*) FROM category_corrections")
        ).scalar()

    subheader("Contadores iniciales")
    print(f"  merchant_mappings     : {initial_mappings}")
    print(f"  category_corrections  : {initial_corrections}")

    # 1c. ML predictions BEFORE corrections
    subheader("Predicciones ML actuales (modelo en disco)")
    try:
        categorizer_before = TransactionCategorizer.load()
        before_predictions: dict[str, tuple[str, float]] = {}
        print(f"  {'Descripción':<45} {'Predicción':<25} {'Confianza':>10}")
        print(f"  {'-'*45} {'-'*25} {'-'*10}")
        for tx in selected:
            desc = tx["description"] or ""
            amount = float(tx["amount"] or 0)
            cat, conf = categorizer_before.predict(desc, amount)
            before_predictions[str(tx["id"])] = (cat, conf)
            print(f"  {desc[:44]:<45} {cat:<25} {conf:>10.2f}")
        model_loaded = True
    except FileNotFoundError:
        print(f"  {YELLOW}Modelo no encontrado — ejecuta train_base_model primero{RESET}")
        before_predictions = {}
        model_loaded = False

    # ══════════════════════════════════════════════════════════════════════════
    header("FASE 2 — Simular correcciones manuales")
    # ══════════════════════════════════════════════════════════════════════════

    corrections_made: list[dict[str, Any]] = []

    for i, tx in enumerate(selected, 1):
        desc = tx["description"] or ""
        correct_cat_name = guess_correct_category(desc)

        # Skip if the guessed category is the same as the current (no point correcting)
        if correct_cat_name == tx["category_name"]:
            # Try a different category to ensure something changes
            for _, cat_name in _KEYWORD_RULES:
                if cat_name != tx["category_name"] and cat_name in cat_by_name:
                    correct_cat_name = cat_name
                    break

        if correct_cat_name not in cat_by_name:
            correct_cat_name = "Otros gastos"

        cat_id = cat_by_name[correct_cat_name]

        result = api.patch_category(str(tx["id"]), cat_id)
        status_code = result["status_code"]

        if status_code == 200:
            status_icon = f"{GREEN}OK{RESET}"
        else:
            status_icon = f"{RED}ERROR {status_code}{RESET}"
            failures.append(f"Corrección #{i} falló con status {status_code}: "
                            f"{result['body']}")

        print(f"  [{i}/5] {status_icon}  {desc[:40]:<40}  →  {correct_cat_name}")

        corrections_made.append({
            "id": str(tx["id"]),
            "description": desc,
            "correct_category": correct_cat_name,
            "correct_category_id": cat_id,
            "status_code": status_code,
        })

    # ══════════════════════════════════════════════════════════════════════════
    header("FASE 3 — Verificar merchant_mappings actualizados")
    # ══════════════════════════════════════════════════════════════════════════

    with engine.connect() as conn:
        final_mappings_count = conn.execute(
            text("SELECT COUNT(*) FROM merchant_mappings")
        ).scalar()

        new_mappings = conn.execute(
            text("""
                SELECT mm.merchant_name, c.name AS category_name,
                       mm.confidence, mm.updated_at
                FROM merchant_mappings mm
                JOIN categories c ON c.id = mm.category_id
                ORDER BY mm.updated_at DESC
                LIMIT 10
            """)
        ).fetchall()
        new_mappings_list = [dict(r._mapping) for r in new_mappings]

    delta_mappings = (final_mappings_count or 0) - (initial_mappings or 0)
    mapping_check = delta_mappings > 0

    print(f"  merchant_mappings antes : {initial_mappings}")
    print(f"  merchant_mappings después: {final_mappings_count}  "
          f"({'+' if delta_mappings >= 0 else ''}{delta_mappings} nuevas)")

    if mapping_check:
        print(f"  {ok('Los merchant_mappings se incrementaron')}")
    else:
        msg = "Los merchant_mappings NO se incrementaron"
        print(f"  {fail(msg)}")
        failures.append(msg)

    subheader("Merchant mappings más recientes")
    print(f"  {'Merchant key':<35} {'Categoría':<25} {'Confianza':>10}")
    print(f"  {'-'*35} {'-'*25} {'-'*10}")
    for m in new_mappings_list:
        print(f"  {m['merchant_name'][:34]:<35} {m['category_name']:<25} {m['confidence']:>10}")

    # 3b. Verify that the next categorization WOULD use merchant_map
    subheader("Verificación: ¿categorize_transaction usaría merchant_map?")
    print(f"  {'Descripción':<45} {'Merchant key':<30} {'Mapeado?':>10}  Resultado")
    print(f"  {'-'*45} {'-'*30} {'-'*10}  {'-'*10}")

    mapped_names = {m["merchant_name"] for m in new_mappings_list}

    for corr in corrections_made:
        if corr["status_code"] != 200:
            continue
        desc = corr["description"]
        cleaned = clean_bank_description(desc)
        merchant_key = extract_merchant_key(cleaned)
        is_mapped = merchant_key in mapped_names
        icon = ok("") if is_mapped else fail("")
        print(f"  {desc[:44]:<45} {merchant_key:<30} {str(is_mapped):>10}  {icon.strip()}")
        if not is_mapped:
            failures.append(
                f"Merchant key '{merchant_key}' no encontrado en merchant_mappings "
                f"después de corregir '{desc[:40]}'"
            )

    # ══════════════════════════════════════════════════════════════════════════
    header("FASE 4 — Verificar correcciones almacenadas en category_corrections")
    # ══════════════════════════════════════════════════════════════════════════

    with engine.connect() as conn:
        final_corrections_count = conn.execute(
            text("SELECT COUNT(*) FROM category_corrections")
        ).scalar()

        correction_rows = conn.execute(
            text("""
                SELECT cc.original_description, cc.cleaned_merchant,
                       pred.name AS predicted_category,
                       corr.name AS corrected_category,
                       cc.created_at
                FROM category_corrections cc
                LEFT JOIN categories pred ON pred.id = cc.predicted_category_id
                JOIN categories corr ON corr.id = cc.corrected_category_id
                ORDER BY cc.created_at DESC
                LIMIT 10
            """)
        ).fetchall()
        correction_records = [dict(r._mapping) for r in correction_rows]

    delta_corrections = (final_corrections_count or 0) - (initial_corrections or 0)
    corrections_check = delta_corrections > 0

    print(f"  category_corrections antes : {initial_corrections}")
    print(f"  category_corrections después: {final_corrections_count}  "
          f"({'+' if delta_corrections >= 0 else ''}{delta_corrections} nuevas)")

    if corrections_check:
        print(f"  {ok('Las correcciones se almacenaron en category_corrections')}")
    else:
        msg = "Las correcciones NO se almacenaron en category_corrections"
        print(f"  {fail(msg)}")
        failures.append(msg)

    subheader("Registros más recientes en category_corrections")
    print(f"  {'Descripción original':<40} {'Merchant key':<25} "
          f"{'Predicha':<20} {'Corregida':<20}")
    print(f"  {'-'*40} {'-'*25} {'-'*20} {'-'*20}")
    for rec in correction_records:
        desc = str(rec["original_description"])[:39]
        merch = str(rec["cleaned_merchant"])[:24]
        pred = str(rec["predicted_category"] or "—")[:19]
        corr = str(rec["corrected_category"])[:19]
        print(f"  {desc:<40} {merch:<25} {pred:<20} {corr:<20}")

    # ══════════════════════════════════════════════════════════════════════════
    header("FASE 5 — Reentrenar y comparar predicciones")
    # ══════════════════════════════════════════════════════════════════════════

    if not model_loaded:
        print(f"  {YELLOW}Saltando — modelo no estaba cargado antes{RESET}")
    else:
        # 5a. Predicciones ANTES (ya capturadas en before_predictions)
        print("  Ejecutando retrain_model()...")
        try:
            metrics = retrain_model()
            print(f"  {GREEN}Reentrenamiento completado{RESET}")
            print(f"    accuracy  : {metrics.get('accuracy', 0):.3f}")
            print(f"    cv_mean   : {metrics.get('cv_mean', 0):.3f} "
                  f"± {metrics.get('cv_std', 0):.3f}")
            print(f"    n_samples : {metrics.get('n_samples', 0)}")
            print(f"    n_classes : {metrics.get('n_classes', 0)}")
            retrain_ok = True
        except Exception as exc:
            print(f"  {fail(f'retrain_model() lanzó excepción: {exc}')}")
            failures.append(f"retrain_model() falló: {exc}")
            retrain_ok = False

        if retrain_ok:
            # 5b. Predicciones DESPUÉS
            categorizer_after = TransactionCategorizer.load()
            after_predictions: dict[str, tuple[str, float]] = {}
            for tx in selected:
                desc = tx["description"] or ""
                amount = float(tx["amount"] or 0)
                cat, conf = categorizer_after.predict(desc, amount)
                after_predictions[str(tx["id"])] = (cat, conf)

            # 5c. Tabla comparativa
            subheader("Tabla comparativa ANTES / DESPUÉS del reentrenamiento")
            col1, col2, col3, col4 = 42, 28, 28, 8
            header_row = (
                f"  {'Descripción':<{col1}} {'ANTES (cat, conf)':<{col2}} "
                f"{'DESPUÉS (cat, conf)':<{col3}} {'Mejoró?':>{col4}}"
            )
            print(header_row)
            print(f"  {'-'*col1} {'-'*col2} {'-'*col3} {'-'*col4}")

            improved = 0
            for tx in selected:
                tx_id = str(tx["id"])
                desc = (tx["description"] or "")[:col1 - 1]

                b_cat, b_conf = before_predictions.get(tx_id, ("—", 0.0))
                a_cat, a_conf = after_predictions.get(tx_id, ("—", 0.0))

                before_str = f"{b_cat[:18]} ({b_conf:.2f})"
                after_str = f"{a_cat[:18]} ({a_conf:.2f})"

                improved_flag = a_conf > b_conf
                if improved_flag:
                    improved += 1
                delta_icon = f"{GREEN}↑{RESET}" if improved_flag else (
                    f"{YELLOW}={RESET}" if abs(a_conf - b_conf) < 0.01 else f"{RED}↓{RESET}"
                )

                print(f"  {desc:<{col1}} {before_str:<{col2}} {after_str:<{col3}} "
                      f"  {delta_icon}")

            print(f"\n  Transacciones con mayor confianza después: {improved}/{len(selected)}")

    # ══════════════════════════════════════════════════════════════════════════
    header("FASE 6 — Resumen final")
    # ══════════════════════════════════════════════════════════════════════════

    print(f"  {'Métrica':<40} {'Antes':>12}  {'Después':>12}")
    print(f"  {'-'*40} {'-'*12}  {'-'*12}")
    print(f"  {'merchant_mappings':<40} {initial_mappings:>12}  {final_mappings_count:>12}")
    print(f"  {'category_corrections':<40} {initial_corrections:>12}  {final_corrections_count:>12}")

    if model_loaded and retrain_ok:
        acc_before = before_predictions  # just to show we had a model
        print(f"  {'Modelo accuracy (post-retrain)':<40} "
              f"{'—':>12}  {metrics.get('accuracy', 0):>12.3f}")
        print(f"  {'Modelo cv_mean (post-retrain)':<40} "
              f"{'—':>12}  {metrics.get('cv_mean', 0):>12.3f}")

    # Count how many of the corrected transactions now resolve via merchant_map
    merchant_map_count = sum(
        1 for c in corrections_made
        if c["status_code"] == 200
        and extract_merchant_key(clean_bank_description(c["description"])) in mapped_names
    )
    print(f"\n  Transacciones que ahora se resolverían via merchant_map: "
          f"{merchant_map_count}/{len([c for c in corrections_made if c['status_code'] == 200])}")

    engine.dispose()

    print()
    if not failures:
        print(f"  {BOLD}{GREEN}✓ El ciclo de active learning funciona correctamente{RESET}")
        return True
    else:
        print(f"  {BOLD}{RED}✗ Algunos pasos fallaron:{RESET}")
        for i, f_msg in enumerate(failures, 1):
            print(f"    {i}. {f_msg}")
        return False


# ── CLI entry point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifica el ciclo completo de active learning en Wallo"
    )
    parser.add_argument(
        "--email",
        default="test@example.com",
        help="Email del usuario de prueba (default: test@example.com)",
    )
    parser.add_argument(
        "--password",
        default="test123",
        help="Contraseña del usuario de prueba (default: test123)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/api/v1",
        help="URL base de la API (default: http://localhost:8000/api/v1)",
    )
    args = parser.parse_args()

    success = run(
        email=args.email,
        password=args.password,
        base_url=args.base_url,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
