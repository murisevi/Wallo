"""Generic keyword-to-category rules for Spanish bank transactions.

Used as a fallback layer after the static merchant dictionary.  Rules match
generic business-type words that appear in descriptions that don't match any
known merchant name (e.g. "CAFETERIA CENTRAL SEVILLA" or "FARMACIA LA PAZ").

Matching uses the same word-boundary regex as merchant_dictionary so that
partial word matches are avoided.
"""

from __future__ import annotations

import re

# ── Keyword rule table ─────────────────────────────────────────────────────────
# Keys: uppercase keyword that appears in cleaned descriptions.
# Values: exact category name from seed.py DEFAULT_CATEGORIES.
# Listed longest-first within each group — the sort at module load handles order.

KEYWORD_RULES: dict[str, str] = {
    # ── Restaurantes y Bares ──────────────────────────────────────────────────
    "HAMBURGUESERIA": "Restaurantes y Bares",
    "CAFETERIA": "Restaurantes y Bares",
    "RESTAURANTE": "Restaurantes y Bares",
    "CERVECERIA": "Restaurantes y Bares",
    "CATERING": "Restaurantes y Bares",
    "VERMUTERIA": "Restaurantes y Bares",
    "TORTILLERIA": "Restaurantes y Bares",
    "HELADERIA": "Restaurantes y Bares",
    "CHURRERIA": "Restaurantes y Bares",
    "PIZZERIA": "Restaurantes y Bares",
    "TAPERIA": "Restaurantes y Bares",
    "BOCAO": "Restaurantes y Bares",
    "KEBAB": "Restaurantes y Bares",
    "TACOS": "Restaurantes y Bares",
    "TACO": "Restaurantes y Bares",
    "TAPAS": "Restaurantes y Bares",
    "CAFE": "Restaurantes y Bares",
    "BODEGAS": "Restaurantes y Bares",
    "BODEGA": "Restaurantes y Bares",
    "CERVEZA": "Restaurantes y Bares",
    "ASADOR": "Restaurantes y Bares",
    "TABERNA": "Restaurantes y Bares",
    "CANTINA": "Restaurantes y Bares",
    "MESÓN": "Restaurantes y Bares",
    "MESON": "Restaurantes y Bares",
    "CHIRINGUITO": "Restaurantes y Bares",

    # ── Alimentación ─────────────────────────────────────────────────────────
    "SUPERMERCADOS": "Alimentación",
    "SUPERMERCADO": "Alimentación",
    "PRIMAPRIX": "Alimentación",
    "COSTCO": "Alimentación",
    "MERCADO": "Alimentación",
    "MARKET": "Alimentación",
    "CARNICERIA": "Alimentación",
    "CARNES": "Alimentación",

    # ── Salud ─────────────────────────────────────────────────────────────────
    "PARAFARMACIA": "Salud",
    "FISIOTERAPIA": "Salud",
    "FISIOTERAPEUTA": "Salud",
    "LABORATORIO": "Salud",
    "PSICOLOGIA": "Salud",
    "PSICOLOGO": "Salud",
    "SANAFARMACIA": "Salud",
    "FARMACIA": "Salud",
    "DENTISTA": "Salud",
    "OCULISTA": "Salud",
    "ORTOPEDIA": "Salud",
    "OPTICA": "Salud",
    "CLINICA": "Salud",
    "HOSPITAL": "Salud",

    # ── Transporte ────────────────────────────────────────────────────────────
    "GASOLINERA": "Transporte",
    "AUTOPISTA": "Transporte",
    "APARCAMIENTO": "Transporte",
    "AUTOLAVADO": "Transporte",
    "PARKING": "Transporte",
    "PEAJE": "Transporte",
    "ESTANCO": "Otros gastos",

    # ── Vivienda ──────────────────────────────────────────────────────────────
    "FERRETERIA": "Vivienda",
    "FONTANERO": "Vivienda",
    "ELECTRICISTA": "Vivienda",
    "CARPINTERO": "Vivienda",
    "REFORMAS": "Vivienda",
    "PINTOR": "Vivienda",
    "CERRAJERO": "Vivienda",
    "COMUNIDAD": "Vivienda",    # "CUOTA COMUNIDAD VECINOS"

    # ── Educación ─────────────────────────────────────────────────────────────
    "AUTOESCUELA": "Educación",
    "ACADEMIA": "Educación",
    "UNIVERSIDAD": "Educación",
    "PAPELERIA": "Educación",
    "LIBRERIA": "Educación",

    # ── Mascotas ──────────────────────────────────────────────────────────────
    "VETERINARIO": "Mascotas",
    "VETERINARIA": "Mascotas",
    "PELUQUERIA CANINA": "Mascotas",

    # ── Ocio ──────────────────────────────────────────────────────────────────
    "POLIDEPORTIVO": "Ocio",
    "ESPECTACULO": "Ocio",
    "CONCIERTO": "Ocio",
    "GIMNASIO": "Ocio",
    "DISCOTECA": "Ocio",
    "LOTERIA": "Ocio",
    "JUEGOS": "Ocio",
    "FERIA": "Ocio",
    "CAMPING": "Ocio",
    "TEATRO": "Ocio",
    "MUSEO": "Ocio",
    "CINE": "Ocio",
}

SUGGESTION_KEYWORD_RULES: dict[str, str] = {
    "EVENTOS": "Ocio",
    "CASETA": "Ocio",
    "VIVEROS": "Vivienda",
    "VIVERO": "Vivienda",
    "TIENDA": "Otros gastos",
    "BAR": "Restaurantes y Bares",
    "SERVICIOS": "Otros gastos",
}

# Pre-sort keys by descending length once at module load — longest wins.
_SORTED_RULES: list[str] = sorted(KEYWORD_RULES, key=len, reverse=True)
_SORTED_SUGGESTION_RULES: list[str] = sorted(
    SUGGESTION_KEYWORD_RULES, key=len, reverse=True
)

# Compiled regex cache.
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _word_match(text: str, keyword: str) -> bool:
    """Return True if *keyword* appears in *text* as a whole-word token."""
    if keyword not in _PATTERN_CACHE:
        _PATTERN_CACHE[keyword] = re.compile(
            r"(?<![A-Z0-9])" + re.escape(keyword) + r"(?![A-Z0-9])"
        )
    return bool(_PATTERN_CACHE[keyword].search(text))


def match_keyword_rule(
    cleaned_description: str,
) -> tuple[str, float] | None:
    """Return (category_name, confidence) for the first matching keyword rule.

    Checks keywords longest-first. Ambiguous rules return medium confidence so
    the service stores them as suggestions instead of confirmed categories.

    Args:
        cleaned_description: Output of clean_bank_description() — uppercase ASCII.

    Returns:
        ``(category_name, confidence)`` on a match, ``None`` otherwise.
    """
    for keyword in _SORTED_RULES:
        if _word_match(cleaned_description, keyword):
            return KEYWORD_RULES[keyword], 0.82
    for keyword in _SORTED_SUGGESTION_RULES:
        if _word_match(cleaned_description, keyword):
            return SUGGESTION_KEYWORD_RULES[keyword], 0.62
    return None
