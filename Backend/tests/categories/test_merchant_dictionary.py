"""Tests for the static merchant dictionary lookup."""

import re
from collections import Counter
from pathlib import Path

import pytest

from app.categories.merchant_dictionary import KNOWN_MERCHANTS, match_known_merchant


class TestMatchKnownMerchant:

    # ── Positive matches ──────────────────────────────────────────────────────

    def test_mercadona_alimentacion(self) -> None:
        result = match_known_merchant("MERCADONA CASIN")
        assert result is not None
        category, confidence = result
        assert category == "Alimentación"
        assert confidence == pytest.approx(0.90)

    def test_carref_alimentacion(self) -> None:
        result = match_known_merchant("CARREF AZNALFAR")
        assert result is not None
        assert result[0] == "Alimentación"

    def test_lidl_alimentacion(self) -> None:
        result = match_known_merchant("LIDL JUAN DE AZ")
        assert result is not None
        assert result[0] == "Alimentación"

    def test_uber_eats_restaurantes_not_transporte(self) -> None:
        """UBER EATS must resolve to Restaurantes y Bares, never Transporte."""
        result = match_known_merchant("UBER EATS SEVILLA")
        assert result is not None
        category, _ = result
        assert category == "Restaurantes y Bares", (
            f"Expected 'Restaurantes y Bares' but got {category!r}. "
            "UBER EATS key must appear before UBER in sorted list."
        )

    def test_uber_transporte(self) -> None:
        """Plain UBER (no EATS) must resolve to Transporte."""
        result = match_known_merchant("UBER VIAJE MADRID")
        assert result is not None
        assert result[0] == "Transporte"

    def test_spotify_suscripciones(self) -> None:
        result = match_known_merchant("SPOTIFY AB ESTOCOLMO")
        assert result is not None
        assert result[0] == "Suscripciones"

    def test_netflix_suscripciones(self) -> None:
        result = match_known_merchant("NETFLIX AMSTERDAM")
        assert result is not None
        assert result[0] == "Suscripciones"

    def test_repsol_transporte(self) -> None:
        result = match_known_merchant("REPSOL GASOLINERA NORTE")
        assert result is not None
        assert result[0] == "Transporte"

    def test_farmacia_salud(self) -> None:
        result = match_known_merchant("FARMACIA GARCIA SEVILLA")
        assert result is not None
        assert result[0] == "Salud"

    def test_endesa_suministros(self) -> None:
        result = match_known_merchant("ENDESA ENERGIA")
        assert result is not None
        assert result[0] == "Suministros"

    def test_dia_short_key_word_boundary(self) -> None:
        """'DIA' must match as a standalone word."""
        result = match_known_merchant("SUPERMERCADO DIA GETAFE")
        assert result is not None
        assert result[0] == "Alimentación"

    def test_bp_short_key_word_boundary(self) -> None:
        result = match_known_merchant("ESTACION BP NORTE")
        assert result is not None
        assert result[0] == "Transporte"

    def test_digi_short_key_word_boundary(self) -> None:
        result = match_known_merchant("DIGI MOVIL RECIBO")
        assert result is not None
        assert result[0] == "Suministros"

    # ── Word boundary — must NOT match ────────────────────────────────────────

    def test_digital_ocean_not_digi(self) -> None:
        """'DIGI' inside 'DIGITAL' must not trigger the DIGI rule."""
        result = match_known_merchant("DIGITAL OCEAN AMSTERDAM")
        assert result is not None
        # DIGITAL OCEAN is in the dictionary as "Suscripciones"
        assert result[0] == "Suscripciones"

    def test_dia_inside_word_no_false_positive(self) -> None:
        """'DIA' inside 'INDIA' or 'MEDIA' must not match Alimentación."""
        assert match_known_merchant("INDIA PALACE RESTAURANT") is None or (
            match_known_merchant("INDIA PALACE RESTAURANT") is not None
            and match_known_merchant("INDIA PALACE RESTAURANT")[0] != "Alimentación"
        )

    # ── No match ──────────────────────────────────────────────────────────────

    def test_unknown_merchant_returns_none(self) -> None:
        result = match_known_merchant("XYZABC DESCONOCIDO")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = match_known_merchant("")
        assert result is None

    # ── Dictionary integrity ───────────────────────────────────────────────────

    def test_min_200_entries(self) -> None:
        assert len(KNOWN_MERCHANTS) >= 200, (
            f"Expected at least 200 merchant entries, got {len(KNOWN_MERCHANTS)}"
        )

    def test_uber_eats_before_uber_in_sorted_order(self) -> None:
        """Verify runtime sort places 'UBER EATS' ahead of 'UBER'."""
        from app.categories.merchant_dictionary import _SORTED_KEYS

        uber_eats_idx = _SORTED_KEYS.index("UBER EATS")
        uber_idx = _SORTED_KEYS.index("UBER")
        assert uber_eats_idx < uber_idx, (
            "'UBER EATS' must appear before 'UBER' in _SORTED_KEYS"
        )

    def test_no_duplicate_source_keys(self) -> None:
        """Duplicate literal keys would be silently overwritten by Python."""
        source = Path("app/categories/merchant_dictionary.py").read_text(
            encoding="utf-8"
        )
        keys = re.findall(r'^\s+"([^"]+)":\s+"[^"]+",', source, flags=re.MULTILINE)
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        assert duplicates == []
