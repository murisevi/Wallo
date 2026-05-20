"""Diagnostic script for transaction categorization quality.

Run from Backend/:
    python -m scripts.diagnose_categorization

Outputs a console summary and data/diagnostico_categorizacion.csv including
confirmed categories, uncategorised transactions, and ML suggestions.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.categories.keyword_rules import match_keyword_rule  # noqa: E402
from app.categories.mcc_mapping import match_mcc_category  # noqa: E402
from app.categories.merchant_dictionary import match_known_merchant  # noqa: E402
from app.categories.text_cleaner import (  # noqa: E402
    clean_bank_description,
    extract_merchant_key,
)


def trunc(text: str | None, n: int) -> str:
    if not text:
        return ""
    return text[:n] if len(text) <= n else text[: n - 1] + "..."


def confidence_bucket(score: float | None) -> str:
    if score is None:
        return "None"
    if score < 0.3:
        return "0.0-0.3"
    if score < 0.5:
        return "0.3-0.5"
    if score < 0.7:
        return "0.5-0.7"
    if score < 0.9:
        return "0.7-0.9"
    return "0.9-1.0"


def get_db_url() -> str:
    for env_file in [_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env"]:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://wallo:wallo@localhost:5432/wallo",
    )


def url_to_psycopg2(url: str) -> str:
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def fetch_rows(dsn: str) -> list[dict]:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("ERROR: psycopg2 not found. Install psycopg2-binary.")
        sys.exit(1)

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    t.description AS raw_description,
                    t.creditor_name,
                    t.debtor_name,
                    t.bank_transaction_code,
                    t.merchant_category_code,
                    t.amount,
                    t.confidence_score,
                    t.categorization_method,
                    c.name AS category_name,
                    sc.name AS suggested_category_name,
                    t.suggested_confidence_score,
                    t.suggested_categorization_method
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                LEFT JOIN categories sc ON sc.id = t.suggested_category_id
                ORDER BY t.date DESC, t.created_at DESC
                """
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    db_url = url_to_psycopg2(get_db_url())
    print(f"Conectando a la BD... ({db_url[:40]}...)")

    raw_rows = fetch_rows(db_url)
    print(f"\nTotal transacciones: {len(raw_rows)}\n")
    if not raw_rows:
        return

    rows: list[dict] = []
    for raw in raw_rows:
        raw_description = raw["raw_description"] or ""
        categorization_text = " ".join(
            str(part).strip()
            for part in (
                raw_description,
                raw["creditor_name"],
                raw["debtor_name"],
                raw["bank_transaction_code"],
                raw["merchant_category_code"],
            )
            if part
        )
        cleaned = clean_bank_description(categorization_text)
        rows.append(
            {
                "raw_description": raw_description,
                "cleaned_description": cleaned,
                "merchant_key": extract_merchant_key(cleaned),
                "assigned_category": raw["category_name"] or "",
                "confidence_score": raw["confidence_score"],
                "method": raw["categorization_method"] or "",
                "suggested_category": raw["suggested_category_name"] or "",
                "suggested_confidence_score": raw["suggested_confidence_score"],
                "suggested_method": raw["suggested_categorization_method"] or "",
                "merchant_category_code": raw["merchant_category_code"] or "",
            }
        )

    print("=" * 128)
    print("PRIMERAS 100 TRANSACCIONES")
    print("=" * 128)
    print(
        f"{'DESCRIPCION':<45} | {'MERCHANT':<22} | {'CATEGORIA':<20} | "
        f"{'CONF':>6} | {'METODO':<14} | {'SUGERENCIA':<20} | {'CONF SUG':>8}"
    )
    print("-" * 128)
    for row in rows[:100]:
        conf = (
            f"{row['confidence_score']:.3f}"
            if row["confidence_score"] is not None
            else ""
        )
        suggested_conf = (
            f"{row['suggested_confidence_score']:.3f}"
            if row["suggested_confidence_score"] is not None
            else ""
        )
        print(
            f"{trunc(row['raw_description'], 45):<45} | "
            f"{trunc(row['merchant_key'], 22):<22} | "
            f"{trunc(row['assigned_category'] or 'Sin categoria', 20):<20} | "
            f"{conf:>6} | {trunc(row['method'], 14):<14} | "
            f"{trunc(row['suggested_category'], 20):<20} | {suggested_conf:>8}"
        )

    print("\nESTADISTICAS")
    print("-" * 60)
    for label, key in (
        ("Metodo confirmado", "method"),
        ("Metodo sugerido", "suggested_method"),
        ("Categoria confirmada", "assigned_category"),
        ("Categoria sugerida", "suggested_category"),
    ):
        print(f"\n--- {label} ---")
        for value, count in Counter(row[key] for row in rows).most_common(12):
            pct = 100 * count / len(rows)
            fallback = "Sin categoria" if "Categoria" in label else "sin metodo"
            print(f"  {value or fallback:<25} {count:>5} ({pct:>5.1f}%)")

    print("\n--- Confianza confirmada ---")
    buckets = Counter(confidence_bucket(row["confidence_score"]) for row in rows)
    for bucket in ["0.0-0.3", "0.3-0.5", "0.5-0.7", "0.7-0.9", "0.9-1.0", "None"]:
        count = buckets.get(bucket, 0)
        pct = 100 * count / len(rows)
        print(f"  {bucket:<10} {count:>5} ({pct:>5.1f}%)")

    no_category_no_suggestion = sum(
        1
        for row in rows
        if not row["assigned_category"] and not row["suggested_category"]
    )
    print("\n--- ML descartado / pendiente de usuario ---")
    print(f"  Sin categoria ni sugerencia: {no_category_no_suggestion}")

    uncategorized = [row for row in rows if not row["assigned_category"]]
    print("\n--- Top merchant keys sin categoria ---")
    uncat_merchants = Counter(row["merchant_key"] for row in uncategorized)
    for merchant, count in uncat_merchants.most_common(15):
        print(f"  {merchant or '(vacio)':<25} {count:>5}")

    print("\n--- Simulacion reglas actuales sobre no categorizadas ---")
    simulated = []
    for row in uncategorized:
        mcc_match = match_mcc_category(row["merchant_category_code"])
        dict_match = match_known_merchant(row["cleaned_description"])
        keyword_match = match_keyword_rule(row["cleaned_description"])
        if mcc_match:
            simulated.append(("mcc", *mcc_match, row["merchant_key"]))
        elif dict_match:
            simulated.append(("global_dict", *dict_match, row["merchant_key"]))
        elif keyword_match:
            method = "keyword_rule" if keyword_match[1] >= 0.70 else "keyword_suggested"
            simulated.append((method, *keyword_match, row["merchant_key"]))

    if simulated:
        simulation_counts = Counter(
            (method, category, round(confidence, 2), merchant)
            for method, category, confidence, merchant in simulated
        )
        for (
            method,
            category,
            confidence,
            merchant,
        ), count in simulation_counts.most_common(20):
            print(
                f"  {count:>3}  {method:<18} {category:<24} "
                f"{confidence:>4.2f}  {merchant or '(vacio)'}"
            )
    else:
        print("  Sin nuevos matches deterministas para el estado actual.")

    output_path = _BACKEND_DIR / "data" / "diagnostico_categorizacion.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV exportado a: {output_path}")
    print(f"Total filas: {len(rows)}\n")


if __name__ == "__main__":
    main()
