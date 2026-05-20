"""Merchant Category Code (MCC) to Wallo category mapping."""

from __future__ import annotations

import re

_EXACT_MCC_CATEGORIES: dict[str, str] = {
    "5411": "Alimentación",
    "5422": "Alimentación",
    "5441": "Alimentación",
    "5451": "Alimentación",
    "5462": "Alimentación",
    "5499": "Alimentación",
    "5811": "Restaurantes y Bares",
    "5812": "Restaurantes y Bares",
    "5813": "Restaurantes y Bares",
    "5814": "Restaurantes y Bares",
    "4111": "Transporte",
    "4112": "Transporte",
    "4121": "Transporte",
    "4131": "Transporte",
    "4511": "Transporte",
    "4784": "Transporte",
    "5541": "Transporte",
    "5542": "Transporte",
    "7523": "Transporte",
    "4900": "Suministros",
    "4814": "Suministros",
    "4899": "Suministros",
    "5211": "Vivienda",
    "5231": "Vivienda",
    "5251": "Vivienda",
    "5712": "Vivienda",
    "5912": "Salud",
    "8011": "Salud",
    "8021": "Salud",
    "8043": "Salud",
    "8062": "Salud",
    "8099": "Salud",
    "5941": "Ocio",
    "7832": "Ocio",
    "7991": "Ocio",
    "7996": "Ocio",
    "7997": "Ocio",
    "7999": "Ocio",
    "5651": "Ropa",
    "5661": "Ropa",
    "5691": "Ropa",
    "5942": "Educación",
    "8211": "Educación",
    "8220": "Educación",
    "8299": "Educación",
    "5968": "Suscripciones",
    "6300": "Seguros",
    "5995": "Mascotas",
    "5947": "Regalos",
    "5993": "Otros gastos",
}


def normalize_mcc(value: object) -> str | None:
    """Return a four-digit MCC string if one can be extracted."""
    if value is None:
        return None
    match = re.search(r"\d{4}", str(value))
    return match.group(0) if match else None


def match_mcc_category(value: object) -> tuple[str, float] | None:
    """Return (category_name, confidence) for a known MCC."""
    mcc = normalize_mcc(value)
    if mcc is None:
        return None
    category = _EXACT_MCC_CATEGORIES.get(mcc)
    if category is None:
        return None
    return category, 0.95
