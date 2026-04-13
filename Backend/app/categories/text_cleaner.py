"""Bank description text cleaner for categorization.

Removes noise from raw bank descriptions (card numbers, dates,
operation codes) and extracts the merchant name.
"""

import re
import unicodedata

# Prefijos habituales de operaciones bancarias españolas
BANK_PREFIXES = [
    r"COMPRA\s+(?:CON\s+)?TARJ(?:ETA)?\.?\s*",
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

# Patrones de ruido: números de tarjeta, fechas, referencias, IBANs, etc.
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
    # Abreviaturas corporativas inline (pueden aparecer en mitad del texto)
    r"\bS\.A\.U?\.?",  # S.A., S.A.U.
    r"\bS\.L\.U?\.?",  # S.L., S.L.U.
    r"\bS\.C\.?",  # S.C.
    r"\bCOOP\.?",  # COOP
]

# Sufijos corporativos al final de la cadena
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

    # Step 2 — remove bank prefixes
    for pattern in BANK_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Step 3 — remove noise patterns
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Step 4 — remove corporate suffixes
    for pattern in CORPORATE_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Step 5 — normalise remaining special chars and whitespace
    text = re.sub(r"[*/#\-_.,;:()]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_merchant_key(cleaned_description: str) -> str:
    """Generate a normalised key for merchant-mapping lookups.

    Takes the first 2 significant words (ignoring 1-2 char words).
    E.g. "MERCADONA MAIRENA DEL ALJARAFE" → "MERCADONA MAIRENA"
    """
    words = cleaned_description.split()
    significant = [w for w in words if len(w) > 2]
    key_words = significant[:2] if len(significant) >= 2 else significant[:1]
    return " ".join(key_words).upper()
