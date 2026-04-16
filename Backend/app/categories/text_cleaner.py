"""Bank description text cleaner for categorization.

Removes noise from raw bank descriptions (operation prefixes, card numbers,
dates, city/location data, reference numbers) and extracts the merchant name.

Designed for real Spanish bank transaction descriptions (BBVA/Enable Banking).

Typical raw formats handled:
  "PAGO MOVIL EN MERCADONA CASIN, TOMARES ES, TARJ. :*428024"
  "BIZUM A FAVOR DE LUCIA AMIAN LOPEZ CONCEPTO: Sin concepto"
  "BIZUM DE Alvaro Ruiz Moreno CONCEPTO b"
  "COMPRA INTERNET EN AREAFIT MAIRENA, VILLAVERDE DEES, TARJ."
  "COMPRA eDreams, Madrid, TARJETA 5489010532428024, COMISION 0.00"
  "RECIBO PayPal Europe S.a.r.l. et Cie S.C.A Nº RECIBO 000123"
  "TRANSFERENCIA INMEDIATA DE PAYPAL, CONCEPTO INSTANT TRANSFER"
  "RETIRADA DE EFECTIVO EN CAJERO AUTOMATICO 0049737..."
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

# ── Transaction type ─────────────────────────────────────────────────────────

TransactionType = Literal[
    "bizum_sent",
    "bizum_received",
    "card_payment",
    "direct_debit",
    "transfer",
    "cash",
    "other",
]

# Matched against the NORMALIZED (uppercase, ASCII) description, in order.
# First match wins.
_TYPE_RULES: list[tuple[str, TransactionType]] = [
    (r"^BIZUM\s+A\s+FAVOR\s+DE\b", "bizum_sent"),
    (r"^BIZUM\s+DE\b", "bizum_received"),
    (
        r"^(?:ANULACION\s+)?(?:PAGO\s+MOVIL\s+EN|COMPRA(?:\s+INTERNET\s+EN"
        r"|\s+BIZUM|\s+EN|\s+)?)\b",
        "card_payment",
    ),
    (r"^(?:RECIBO|ADEUDO|RENTING)\b", "direct_debit"),
    (r"^TRANSFERENCIA\b", "transfer"),
    (r"\b(?:RETIRADA|CAJERO)\b", "cash"),
]

# ── Anchored prefix patterns ─────────────────────────────────────────────────
# Removed from the START of the normalized string.  Ordered longest-first so
# the most-specific match wins (e.g. "PAGO MOVIL EN" before "PAGO").

_PREFIX_PATTERNS: list[str] = [
    r"^ANULACION\s+PAGO\s+MOVIL\s+EN\s+",
    r"^PAGO\s+MOVIL\s+EN\s+",
    r"^COMPRA\s+INTERNET\s+EN\s+",
    r"^COMPRA\s+BIZUM\s+",
    r"^COMPRA\s+EN\s+",
    # Legacy format: "COMPRA TARJ 4921*****1234 MERCHANT" or "COMPRA CON TARJETA XXXX MERCHANT"
    r"^COMPRA\s+(?:CON\s+)?TARJ(?:ETA)?\.?\s*",
    r"^COMPRA\s+",
    r"^BIZUM\s+A\s+FAVOR\s+DE\s+",
    r"^BIZUM\s+DE\s+",
    r"^BIZUM\s+",
    r"^TRANSFERENCIA\s+INMEDIATA\s+DE\s+",
    r"^TRANSFERENCIA\s+(?:DE|A|EMITIDA|RECIBIDA)\s+",
    r"^TRANSFERENCIA\s+",
    r"^RECIBO\s+(?:DOMICILIADO\s+)?",
    r"^ADEUDO\s+(?:DIRECTO\s+)?(?:SEPA\s+)?",
    r"^RETIRADA\s+DE\s+EFECTIVO\s+(?:EN\s+)?(?:CAJERO\s+(?:AUTOMATICO\s+)?)?",
    r"^LIQUIDACION\s+(?:POR\s+)?(?:BONIFICACION\s+)?",
    r"^PAGO\s+(?:EN\s+)?COMERCIO\s+",
    r"^PAGO\s+(?:CON\s+)?TARJ(?:ETA)?\s+",
]

# ── Trailing-cut patterns ────────────────────────────────────────────────────
# Applied left-to-right AFTER prefix removal.  Each pattern removes everything
# from the match position to the end of the string.

_TRAILING_CUT_PATTERNS: list[str] = [
    # TARJ. :*428024  /  TARJETA 5489010532428024  (comma-preceded — comma required
    # to prevent matching "COMPRA TARJ XXXX MERCHANT" at position 0)
    r",\s*TARJ(?:ETA)?[\s.,:*].*$",
    # Trailing bare "TARJ" or "TARJ." after a comma (e.g. "..., TARJ.")
    r",\s*TARJ\.?\s*$",
    # ", TOMARES ES," or ", SEVILLA ES," — city + Spanish country code
    # Also handles truncated forms like "MAIRENA DEL AES" (space-less ES suffix)
    r",\s*[\w\s]{2,30}(?:\s+ES|ES)\s*,.*$",
    # Same pattern at end of string
    r",\s*[\w\s]{2,30}(?:\s+ES|ES)\s*$",
    # COMISION 0.00  (may follow a comma)
    r",?\s*COMISION\s+[\d.,]+.*$",
    # "Nº RECIBO 000123" / "N RECIBO 000123" (º→ASCII drops the ordinal)
    r",?\s*N[O\s]?\s*RECIBO\s+\S+.*$",
    # "CONCEPTO: texto" or "CONCEPTO texto" (Bizum / transfer concept field)
    r",?\s*CONCEPTO[:\s].*$",
    # Trailing location after comma: ", MADRID" / ", SAN FRANCISCO"
    r",\s+[A-Z][A-Z\s]{2,}\s*$",
    # Enable Banking credit-note suffixes: "NAME-CRDT-3.21-r2py1"
    r"\s*-?CRDT-?[\d.].*$",
]

# ── Inline noise patterns ────────────────────────────────────────────────────
# Applied AFTER trailing cuts.  Remove fragments anywhere in the string.

_NOISE_PATTERNS: list[str] = [
    r"\b\d{4}\s*\*{4,}\s*\d{4}\b",             # Card numbers: 4921 **** 1234
    r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b",           # Dates: 10/04/2025
    r"\b\d{2}\.\d{2}\.\d{2,4}\b",               # Dates: 10.04.2025
    r"\bREF[\s.:]*\w+\b",                        # REF123456
    r"\bN[OÃ]?\s*\d+\b",                         # Nº 123456
    r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",  # IBAN
    r"\bES\d{18,22}\b",                          # Spanish IBAN shorthand
    r"\bCOM\.\s*\d+[.,]\d+\b",                  # Embedded commissions
    r"\b\d{6,}\b",                               # Long digit sequences (≥6)
    r"\bOFICINA\s+\d+\b",
    r"\bSUCURSAL\s+\d+\b",
    # French/international corporate identifiers (remnants after S.a.r.l. etc.)
    r"\bS\.?A\.?R\.?L\.?\b",                    # S.A.R.L. (French LLC)
    r"\bET\s+CIE\b",                             # "et Cie" (French & Co.)
    # Spanish corporate identifiers (inline — may appear mid-string)
    r"\bS\.A\.U?\.?",
    r"\bS\.L\.U?\.?",
    r"\bS\.C\.?A?\.?\b",                  # S.C., S.C.A. (Société en Commandite)
    r"\bCOOP\.?",
]

# ── Corporate suffixes at end of string ─────────────────────────────────────

_CORPORATE_SUFFIXES: list[str] = [
    r"\s+S\.?A\.?R\.?L\.?$",
    r"\s+S\.?A\.?U?\.?$",
    r"\s+S\.?L\.?U?\.?$",
    r"\s+S\.?C\.?$",
    r"\s+SOCIEDAD\s+\w+$",
    r"\s+COOP\.?$",
    r"\s+ET\s+CIE\.?$",
]

# Words that should be skipped when building the merchant key (leading
# prepositions or articles that survive prefix removal).
_SKIP_WORDS: frozenset[str] = frozenset(
    {"EN", "DE", "LA", "EL", "LOS", "LAS", "DEL", "AL", "UN", "UNA", "A", "Y", "O"}
)


# ── Public API ────────────────────────────────────────────────────────────────


def normalize_text(text: str) -> str:
    """Remove accents and convert to uppercase ASCII."""
    nfkd = unicodedata.normalize("NFKD", text)
    return nfkd.encode("ASCII", "ignore").decode("ASCII").upper().strip()


def detect_transaction_type(raw_description: str) -> TransactionType:
    """Classify the transaction type from the raw bank description.

    Returns one of:
        bizum_sent     – outgoing Bizum (BIZUM A FAVOR DE…)
        bizum_received – incoming Bizum (BIZUM DE…)
        card_payment   – POS / mobile / online card payment
        direct_debit   – recurring debit / SEPA direct debit
        transfer       – bank transfer (TRANSFERENCIA)
        cash           – ATM withdrawal
        other          – anything else (salary, interest, fees…)
    """
    normalized = normalize_text(raw_description)
    for pattern, tx_type in _TYPE_RULES:
        if re.search(pattern, normalized):
            return tx_type
    return "other"


def clean_bank_description(raw_description: str) -> str:
    """Clean a raw bank transaction description into a short merchant name.

    Pipeline:
    1. Normalize (uppercase, strip accents → pure ASCII)
    2. Remove the first matching anchored operation prefix (with preposition)
    3. Apply trailing-cut patterns (location, TARJ, CONCEPTO, Nº RECIBO…)
    4. Remove inline noise (card numbers, dates, corporate identifiers…)
    5. Remove corporate suffixes at end of string
    6. Normalise remaining punctuation and collapse whitespace

    Examples:
        "PAGO MOVIL EN MERCADONA CASIN, TOMARES ES, TARJ. :*428024"
            → "MERCADONA CASIN"
        "COMPRA INTERNET EN AREAFIT MAIRENA, VILLAVERDE DEES, TARJ."
            → "AREAFIT MAIRENA"
        "RECIBO PayPal Europe S.a.r.l. et Cie S.C.A Nº RECIBO 000123"
            → "PAYPAL EUROPE"
        "BIZUM A FAVOR DE LUCIA AMIAN LOPEZ CONCEPTO: Sin concepto"
            → "LUCIA AMIAN LOPEZ"
    """
    text = normalize_text(raw_description)

    # Step 2 — remove the first matching anchored prefix
    for pattern in _PREFIX_PATTERNS:
        new_text = re.sub(pattern, "", text, count=1)
        if new_text != text:
            text = new_text.strip()
            break  # only strip one prefix per description

    # Step 3 — cut trailing location / card / concept data
    for pattern in _TRAILING_CUT_PATTERNS:
        text = re.sub(pattern, "", text).strip()

    # Step 4 — remove inline noise fragments
    for pattern in _NOISE_PATTERNS:
        text = re.sub(pattern, "", text)

    # Step 5 — remove corporate suffixes
    for pattern in _CORPORATE_SUFFIXES:
        text = re.sub(pattern, "", text)

    # Step 6 — normalise punctuation and whitespace
    text = re.sub(r"[*/#\-_.,;:()\[\]]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_merchant_key(cleaned_description: str) -> str:
    """Generate a normalised lookup key for merchant-mapping.

    Takes the first 2 significant words, skipping:
    - Words of 1–2 characters
    - Leading prepositions / articles that may survive prefix removal
      (EN, DE, LA, EL, LOS, LAS, DEL, AL…)

    Examples:
        "MERCADONA MAIRENA DEL ALJARAFE" → "MERCADONA MAIRENA"
        "EN CARREF AZNALFAR"             → "CARREF AZNALFAR"   (skips EN)
        "NETFLIX"                        → "NETFLIX"
    """
    words = cleaned_description.split()
    significant = [w for w in words if len(w) > 2 and w.upper() not in _SKIP_WORDS]
    key_words = significant[:2] if len(significant) >= 2 else significant[:1]
    return " ".join(key_words).upper()
