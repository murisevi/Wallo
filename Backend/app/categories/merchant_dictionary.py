"""Static merchant-to-category dictionary for Spanish bank transactions.

Keys are uppercase substrings as they appear after clean_bank_description().
Matching uses word-boundary regex so short keys like "DIA", "BP", "HM" are
protected against false positives (e.g. "DIGI" does not match "DIGITAL OCEAN").
Lookup tries the longest key first so "UBER EATS" wins over "UBER".
"""

from __future__ import annotations

import re

# ── Known merchants organised by category ─────────────────────────────────────
# Keys: uppercase, as returned by clean_bank_description().
# Values: exact category name matching seed.py DEFAULT_CATEGORIES.
# Longest key always wins — do NOT move keys without understanding the order.

KNOWN_MERCHANTS: dict[str, str] = {
    # ── Alimentación ──────────────────────────────────────────────────────────
    "EL CORTE INGLES SUPERMERCADO": "Alimentación",
    "CORTE INGLES SUPERMERCADO": "Alimentación",
    "BM SUPERMERCADOS": "Alimentación",
    "BM SUPERMERCADO": "Alimentación",
    "LUPA SUPERMERCADOS": "Alimentación",
    "SUMA SUPERMERCADOS": "Alimentación",
    "MAXI DIA": "Alimentación",
    "SIMPLY MARKET": "Alimentación",
    "FRESH MARKET": "Alimentación",
    "MERCADONA": "Alimentación",
    "CARREFOUR": "Alimentación",
    "CARREF": "Alimentación",
    "ALCAMPO": "Alimentación",
    "HIPERCOR": "Alimentación",
    "SUPERCOR": "Alimentación",
    "CONSUM": "Alimentación",
    "EROSKI": "Alimentación",
    "LIDL": "Alimentación",
    "ALDI": "Alimentación",
    "FROIZ": "Alimentación",
    "AHORRAMAS": "Alimentación",
    "SUPERSOL": "Alimentación",
    "COVIRÁN": "Alimentación",
    "COVIRAN": "Alimentación",
    "BONPREU": "Alimentación",
    "CONDIS": "Alimentación",
    "GADIS": "Alimentación",
    "DIALPRIX": "Alimentación",
    "SUPECO": "Alimentación",
    "MASYMAS": "Alimentación",
    "SIMPLY": "Alimentación",
    "SPAR": "Alimentación",
    "SUPERMERCADOS": "Alimentación",
    "SUPERMERCADO": "Alimentación",
    "PRIMAPRIX": "Alimentación",
    "COSTCO": "Alimentación",
    "MARKET": "Alimentación",
    "CASH": "Alimentación",
    "DIA": "Alimentación",          # short — word boundary essential
    "CARNICERIA": "Alimentación",
    "PANADERIA": "Alimentación",
    "PESCADERIA": "Alimentación",
    "FRUTERIA": "Alimentación",
    "VERDULERIA": "Alimentación",
    "CHARCUTERIA": "Alimentación",
    "HERBOLARIO": "Alimentación",
    "ULTRAMARINOS": "Alimentación",
    "COLMADO": "Alimentación",

    # ── Restaurantes y Bares ──────────────────────────────────────────────────
    "FOSTER HOLLYWOOD": "Restaurantes y Bares",
    "PANS AND CO": "Restaurantes y Bares",
    "BURGER KING": "Restaurantes y Bares",
    "TACO BELL": "Restaurantes y Bares",
    "FIVE GUYS": "Restaurantes y Bares",
    "PAPA JOHNS": "Restaurantes y Bares",
    "UBER EATS": "Restaurantes y Bares",    # MUST come before UBER
    "JUST EAT": "Restaurantes y Bares",
    "MC DONALDS": "Restaurantes y Bares",
    "CAFES MORENO": "Restaurantes y Bares",
    "MCDONALDS": "Restaurantes y Bares",
    "MCDONALD": "Restaurantes y Bares",
    "STARBUCKS": "Restaurantes y Bares",
    "DELIVEROO": "Restaurantes y Bares",
    "TELEPIZZA": "Restaurantes y Bares",
    "DOMINOS": "Restaurantes y Bares",
    "POPEYES": "Restaurantes y Bares",
    "SUBWAY": "Restaurantes y Bares",
    "GLOVO": "Restaurantes y Bares",
    "VIPS": "Restaurantes y Bares",
    "GOIKO": "Restaurantes y Bares",
    "PANS CO": "Restaurantes y Bares",
    "PANS": "Restaurantes y Bares",
    "KFC": "Restaurantes y Bares",
    "CAFETERIA": "Restaurantes y Bares",
    "RESTAURANTE": "Restaurantes y Bares",
    "CERVECERIA": "Restaurantes y Bares",
    "PIZZERIA": "Restaurantes y Bares",
    "HELADERIA": "Restaurantes y Bares",
    "CHURRERIA": "Restaurantes y Bares",
    "HAMBURGUESERIA": "Restaurantes y Bares",
    "VERMUTERIA": "Restaurantes y Bares",
    "TAPERIA": "Restaurantes y Bares",
    "TORTILLERIA": "Restaurantes y Bares",
    "ASADOR": "Restaurantes y Bares",
    "TABERNA": "Restaurantes y Bares",
    "SUSHICLUB": "Restaurantes y Bares",
    "SUSHI": "Restaurantes y Bares",
    "COFFEE": "Restaurantes y Bares",
    "COFFE": "Restaurantes y Bares",    # common Spanish typo in receipts
    "CAFE": "Restaurantes y Bares",
    "BODEGAS": "Restaurantes y Bares",
    "BODEGA": "Restaurantes y Bares",
    "TASCA": "Restaurantes y Bares",

    # ── Transporte ────────────────────────────────────────────────────────────
    "METRO SEVILLA": "Transporte",
    "METRO MADRID": "Transporte",
    "METRO BILBAO": "Transporte",
    "SABA APARCAMIENTO": "Transporte",
    "INDIGO PARK": "Transporte",
    "WIZZ AIR": "Transporte",
    "REPSOL GAS": "Transporte",     # before REPSOL (longer key wins)
    "BLABLACAR": "Transporte",
    "PETRONOR": "Transporte",
    "GASOLINERA": "Transporte",
    "AUTOPISTA": "Transporte",
    "AUTOLAVADO": "Transporte",
    "WIZZAIR": "Transporte",
    "RODALIES": "Transporte",
    "VOLTERRA": "Transporte",
    "RYANAIR": "Transporte",
    "VUELING": "Transporte",
    "EASYJET": "Transporte",
    "VOLOTEA": "Transporte",
    "PLENOIL": "Transporte",
    "CAMPSA": "Transporte",
    "CABIFY": "Transporte",
    "IBERIA": "Transporte",
    "RENFE": "Transporte",
    "REPSOL": "Transporte",
    "CEPSA": "Transporte",
    "AVANZA": "Transporte",
    "OUIGO": "Transporte",
    "PARKIA": "Transporte",
    "GALP": "Transporte",
    "AENA": "Transporte",
    "ALSA": "Transporte",
    "IRYO": "Transporte",
    "SABA": "Transporte",
    "UBER": "Transporte",           # AFTER UBER EATS — longest key wins
    "BOLT": "Transporte",
    "EMT": "Transporte",
    "TMB": "Transporte",
    "BP": "Transporte",             # short — word boundary essential
    "PEAJE": "Transporte",
    "PARKING": "Transporte",

    # ── Vivienda ──────────────────────────────────────────────────────────────
    "LEROY MERLIN": "Vivienda",
    "BRICOMART": "Vivienda",
    "BRICODEPOT": "Vivienda",
    "IDEALISTA": "Vivienda",
    "HABITACLIA": "Vivienda",
    "FOTOCASA": "Vivienda",
    "BAUHAUS": "Vivienda",
    "AIRBNB": "Vivienda",
    "BOOKING": "Vivienda",
    "IKEA": "Vivienda",
    "AKI": "Vivienda",

    # ── Suministros ───────────────────────────────────────────────────────────
    "OCTOPUS ENERGY": "Suministros",
    "ACCIONA ENERGIA": "Suministros",
    "CANAL ISABEL": "Suministros",
    "CANAL COMUNIDAD": "Suministros",
    "REPSOL ELECTRICIDAD": "Suministros",
    "IBERDROLA": "Suministros",
    "NATURGY": "Suministros",
    "ENDESA": "Suministros",
    "HOLALUZ": "Suministros",
    "VIESGO": "Suministros",
    "MOVISTAR": "Suministros",
    "VODAFONE": "Suministros",
    "MASMOVIL": "Suministros",
    "PEPEPHONE": "Suministros",
    "EUSKALTEL": "Suministros",
    "TELECABLE": "Suministros",
    "EMASAGRA": "Suministros",
    "EMASESA": "Suministros",
    "ORANGE": "Suministros",
    "JAZZTEL": "Suministros",
    "R CABLE": "Suministros",
    "SIMYO": "Suministros",
    "YOIGO": "Suministros",
    "AGBAR": "Suministros",
    "AGUAS": "Suministros",
    "LOWI": "Suministros",
    "EDP": "Suministros",
    "DIGI": "Suministros",          # short — word boundary essential

    # ── Salud ─────────────────────────────────────────────────────────────────
    "CLINICA DENTAL": "Salud",
    "OPTICAS VISION": "Salud",
    "GENERAL OPTICA": "Salud",
    "MULTIOFTALMICA": "Salud",
    "LABORATORIO ANALISIS": "Salud",
    "LABORATORIO CLINICO": "Salud",
    "CENTRO MEDICO": "Salud",
    "MAPFRE SALUD": "Salud",
    "QUIRONSALUD": "Salud",
    "FISIOTERAPIA": "Salud",
    "FISIOTERAPEUTA": "Salud",
    "PSICOLOGIA": "Salud",
    "PARAFARMACIA": "Salud",
    "SANAFARMACIA": "Salud",
    "FARMACIA": "Salud",
    "DENTISTA": "Salud",
    "OCULISTA": "Salud",
    "HOSPITAL": "Salud",
    "CLINICA": "Salud",
    "SANITAS": "Salud",
    "ADESLAS": "Salud",
    "OPTICA": "Salud",

    # ── Ocio ──────────────────────────────────────────────────────────────────
    "ANYTIME FITNESS": "Ocio",
    "PARQUE WARNER": "Ocio",
    "PISCINA MUNICIPAL": "Ocio",
    "PALACIO DEPORTES": "Ocio",
    "POLIDEPORTIVO": "Ocio",
    "PORTAVENTURA": "Ocio",
    "EPIC GAMES": "Ocio",
    "TICKETMASTER": "Ocio",
    "ENTRADAS COM": "Ocio",
    "INTERSPORT": "Ocio",
    "SPORT ZONE": "Ocio",
    "BASICFIT": "Ocio",
    "BASIC FIT": "Ocio",
    "PLANETFIT": "Ocio",
    "APOLO GYM": "Ocio",
    "KINEPOLIS": "Ocio",
    "VUE CINE": "Ocio",
    "DECATHLON": "Ocio",
    "ATRAPALO": "Ocio",
    "CIVITATIS": "Ocio",
    "ALTAFIT": "Ocio",
    "AREAFIT": "Ocio",
    "MCFIT": "Ocio",
    "CINESA": "Ocio",
    "YELMO": "Ocio",
    "STEAM": "Ocio",
    "PLAYSTATION": "Ocio",
    "NINTENDO": "Ocio",
    "GIMNASIO": "Ocio",
    "PARADORES": "Ocio",
    "NH HOTELES": "Ocio",
    "BARCELO": "Ocio",
    "MELIA": "Ocio",
    "TRIVAGO": "Ocio",
    "CAMPING": "Ocio",
    "MUSEO": "Ocio",
    "CINES": "Ocio",
    "XBOX": "Ocio",
    "FLYING TIGER": "Ocio",
    "NORMAL": "Ocio",

    # ── Ropa ──────────────────────────────────────────────────────────────────
    "PULL AND BEAR": "Ropa",
    "MASSIMO DUTTI": "Ropa",
    "PEDRO DEL HIERRO": "Ropa",
    "STRADIVARIUS": "Ropa",
    "SPORT SHOES": "Ropa",
    "FOOT LOCKER": "Ropa",
    "CALZEDONIA": "Ropa",
    "INTIMISSIMI": "Ropa",
    "WOMEN SECRET": "Ropa",
    "CORTEFIEL": "Ropa",
    "SPRINGFIELD": "Ropa",
    "FOOTLOCKER": "Ropa",
    "PULL BEAR": "Ropa",
    "BERSHKA": "Ropa",
    "PRIMARK": "Ropa",
    "LEFTIES": "Ropa",
    "DECIMAS": "Ropa",
    "VINTED": "Ropa",
    "WALLAPOP": "Ropa",
    "CAMPER": "Ropa",
    "MANGO": "Ropa",
    "OYSHO": "Ropa",
    "SHEIN": "Ropa",
    "ADIDAS": "Ropa",
    "ASICS": "Ropa",
    "ZARA": "Ropa",
    "PUMA": "Ropa",
    "NIKE": "Ropa",
    "H M": "Ropa",
    "HM": "Ropa",                   # short — word boundary essential
    "C&A": "Ropa",

    # ── Educación ─────────────────────────────────────────────────────────────
    "LINKEDIN LEARNING": "Educación",
    "OPENWEBINARS": "Educación",
    "PLURALSIGHT": "Educación",
    "AUTOESCUELA": "Educación",
    "DOMESTIKA": "Educación",
    "COURSERA": "Educación",
    "PAPELERIA": "Educación",
    "ACADEMIA": "Educación",
    "EDUREKA": "Educación",
    "UDEMY": "Educación",

    # ── Suscripciones ─────────────────────────────────────────────────────────
    "AMAZON PRIME": "Suscripciones",
    "PRIME VIDEO": "Suscripciones",
    "DISNEY PLUS": "Suscripciones",
    "DISNEYPLUS": "Suscripciones",
    "APPLE MUSIC": "Suscripciones",
    "APPLE TV": "Suscripciones",
    "YOUTUBE PREMIUM": "Suscripciones",
    "MICROSOFT 365": "Suscripciones",
    "MICROSOFT OFFICE": "Suscripciones",
    "OFFICE 365": "Suscripciones",
    "GOOGLE ONE": "Suscripciones",
    "GOOGLE STORAGE": "Suscripciones",
    "AMAZON WEB SERVICES": "Suscripciones",
    "DIGITAL OCEAN": "Suscripciones",
    "DIGITALOCEAN": "Suscripciones",
    "MOVISTAR PLUS": "Suscripciones",
    "ORANGE TV": "Suscripciones",
    "CLAUDE AI": "Suscripciones",
    "OPENAI": "Suscripciones",
    "CHATGPT": "Suscripciones",
    "CLOUDFLARE": "Suscripciones",
    "NAMECHEAP": "Suscripciones",
    "GODADDY": "Suscripciones",
    "PLANETSCALE": "Suscripciones",
    "RTVE PLAY": "Suscripciones",
    "YOUTUBE": "Suscripciones",
    "NETFLIX": "Suscripciones",
    "SPOTIFY": "Suscripciones",
    "DROPBOX": "Suscripciones",
    "FILMIN": "Suscripciones",
    "HETZNER": "Suscripciones",
    "VERCEL": "Suscripciones",
    "HEROKU": "Suscripciones",
    "ICLOUD": "Suscripciones",
    "TWITCH": "Suscripciones",
    "GITHUB": "Suscripciones",
    "ADOBE": "Suscripciones",
    "CANVA": "Suscripciones",
    "DAZN": "Suscripciones",
    "HBO": "Suscripciones",
    "AWS": "Suscripciones",

    # ── Seguros ───────────────────────────────────────────────────────────────
    "MUTUA MADRILENA": "Seguros",
    "LINEA DIRECTA": "Seguros",
    "CATALANA OCCIDENTE": "Seguros",
    "DKV SEGUROS": "Seguros",
    "SEGURCAIXA": "Seguros",
    "GENERALI": "Seguros",
    "HELVETIA": "Seguros",
    "ALLIANZ": "Seguros",
    "MAPFRE": "Seguros",
    "OCASO": "Seguros",
    "CASER": "Seguros",
    "ZURICH": "Seguros",
    "ASISA": "Seguros",
    "VHI": "Seguros",
    "AXA": "Seguros",

    # ── Mascotas ──────────────────────────────────────────────────────────────
    "CLINICA VETERINARIA": "Mascotas",
    "HOSPITAL VETERINARIO": "Mascotas",
    "PELUQUERIA CANINA": "Mascotas",
    "TIENDANIMAL": "Mascotas",
    "VETERINARIO": "Mascotas",
    "VETERINARIA": "Mascotas",
    "PETCOACH": "Mascotas",
    "PETSTOP": "Mascotas",
    "ZOOPLUS": "Mascotas",
    "KIWOKO": "Mascotas",
    "GUDOG": "Mascotas",

    # ── Otros gastos ──────────────────────────────────────────────────────────
    "AGENCIA TRIBUTARIA": "Otros gastos",
    "APPLE COM BILL": "Otros gastos",
    "APPLE STORE": "Otros gastos",
    "EL CORTE INGLES": "Otros gastos",
    "CORTE INGLES": "Otros gastos",
    "PCCOMPONENTES": "Otros gastos",
    "MEDIAMARKT": "Otros gastos",
    "ALIEXPRESS": "Otros gastos",
    "AMAZON": "Otros gastos",
    "PAYPAL": "Otros gastos",
    "HACIENDA": "Otros gastos",
    "NOTARIA": "Otros gastos",
    "NOTARIO": "Otros gastos",
    "WORTEN": "Otros gastos",
    "FNAC": "Otros gastos",
    "CORREOS": "Otros gastos",
    "MULTA": "Otros gastos",
    "SEUR": "Otros gastos",
    "DHL": "Otros gastos",
    "MRW": "Otros gastos",
    "GLS": "Otros gastos",
    "UPS": "Otros gastos",
    "FEDEX": "Otros gastos",
    "DGT": "Otros gastos",
}

# Pre-sort keys by descending length once at module load — longest wins.
_SORTED_KEYS: list[str] = sorted(KNOWN_MERCHANTS, key=len, reverse=True)

# Compiled regex cache to avoid recompiling on every call.
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _word_match(text: str, key: str) -> bool:
    """Return True if *key* appears in *text* as a whole-word token.

    Uses negative lookbehind/lookahead for [A-Z0-9] so that short keys like
    "DIA" match "SUPERMERCADO DIA GETAFE" but not "INDIA" or "MEDIA".
    """
    if key not in _PATTERN_CACHE:
        _PATTERN_CACHE[key] = re.compile(
            r"(?<![A-Z0-9])" + re.escape(key) + r"(?![A-Z0-9])"
        )
    return bool(_PATTERN_CACHE[key].search(text))


def match_known_merchant(
    cleaned_description: str,
) -> tuple[str, float] | None:
    """Return (category_name, confidence) for the best matching known merchant.

    Checks keys longest-first so multi-word keys ("UBER EATS") win over their
    substrings ("UBER").  Uses word-boundary matching to avoid false positives.

    Args:
        cleaned_description: Output of clean_bank_description() — uppercase ASCII.

    Returns:
        ``(category_name, 0.90)`` on a match, ``None`` otherwise.
    """
    for key in _SORTED_KEYS:
        if _word_match(cleaned_description, key):
            return KNOWN_MERCHANTS[key], 0.90
    return None
