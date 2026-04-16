"""One-time script to train the base categorisation model.

Usage (from /backend):
    python -m scripts.train_base_model
"""
from pathlib import Path

import pandas as pd

from app.categories.ml_categorizer import TransactionCategorizer

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "training_data.csv"


def main() -> None:
    print("Loading training data...")
    df = pd.read_csv(DATA_PATH)
    print(f"  {len(df)} samples, {df['category'].nunique()} categories")
    print(f"  Categories: {sorted(df['category'].unique())}")

    print("\nTraining model...")
    categorizer = TransactionCategorizer()
    metrics = categorizer.train(df)

    print(f"\nTraining results:")
    print(f"  Train accuracy : {metrics['accuracy']:.3f}")
    print(f"  Cross-val      : {metrics['cv_mean']:.3f} ± {metrics['cv_std']:.3f}")
    print(f"  Classes        : {metrics['n_classes']}")

    print("\nSaving model...")
    categorizer.save()
    print("  Saved to data/models/")

    print("\nQuick test predictions:")
    print(f"  {'Description':<45} {'Amount':>10}  ->  Category (confidence)")
    print(f"  {'-'*45} {'-'*10}     {'-'*30}")
    tests = [
        ("MERCADONA S.A. SEVILLA",               -65.30),
        ("COMPRA TARJ LIDL TRIANA",               -32.10),
        ("SPOTIFY TECHNOLOGY",                    -9.99),
        ("ADEUDO DIRECTO SEPA NETFLIX",           -17.99),
        ("RECIBO DOMICILIADO ENDESA ENERGIA S.A.", -85.30),
        ("REPSOL GASOLINERA",                     -52.00),
        ("TRANSFERENCIA NOMINA EMPRESA S.L.",    2200.00),
        ("NOMINA MENSUAL",                       1950.00),
        ("BIZUM DE JUAN",                          15.00),
        ("CLINICA DENTAL SEVILLA",               -120.00),
    ]
    for desc, amount in tests:
        cat, conf = categorizer.predict(desc, amount)
        arrow = "OK" if conf >= 0.70 else "~" if conf >= 0.40 else "?"
        print(f"  {desc:<45} {amount:>10.2f}EUR  ->  {cat:<30} {conf:.1%} {arrow}")


if __name__ == "__main__":
    main()
