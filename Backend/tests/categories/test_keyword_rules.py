"""Tests for the generic keyword-rule categorization lookup."""

from app.categories.keyword_rules import match_keyword_rule


class TestMatchKeywordRule:

    # ── Positive matches ──────────────────────────────────────────────────────

    def test_cafeteria_restaurantes(self) -> None:
        result = match_keyword_rule("CAFETERIA MAS SEVILLA")
        assert result is not None
        category, confidence = result
        assert category == "Restaurantes y Bares"
        assert confidence == 0.82

    def test_restaurante_restaurantes(self) -> None:
        result = match_keyword_rule("RESTAURANTE CASA PEDRO")
        assert result is not None
        assert result[0] == "Restaurantes y Bares"

    def test_farmacia_salud(self) -> None:
        result = match_keyword_rule("FARMACIA LA PAZ")
        assert result is not None
        assert result[0] == "Salud"

    def test_gimnasio_ocio(self) -> None:
        result = match_keyword_rule("GIMNASIO OLYMPUS SEVILLA")
        assert result is not None
        assert result[0] == "Ocio"

    def test_hotel_ocio(self) -> None:
        """'GRAN HOTEL' contains no keyword rule — should return None."""
        result = match_keyword_rule("GRAN HOTEL MONA SEVILLA")
        # "HOTEL" is not in keyword rules; confirm it does not falsely match
        assert result is None

    def test_clinica_salud(self) -> None:
        result = match_keyword_rule("CLINICA DENTAL GARCIA")
        assert result is not None
        assert result[0] == "Salud"

    def test_autoescuela_educacion(self) -> None:
        result = match_keyword_rule("AUTOESCUELA CENTRO SUR")
        assert result is not None
        assert result[0] == "Educación"

    def test_veterinario_mascotas(self) -> None:
        result = match_keyword_rule("VETERINARIO CIUDAD JARDIN")
        assert result is not None
        assert result[0] == "Mascotas"

    def test_parking_transporte(self) -> None:
        result = match_keyword_rule("PARKING EL CENTRO")
        assert result is not None
        assert result[0] == "Transporte"

    def test_cine_ocio(self) -> None:
        result = match_keyword_rule("CINE NORTE SEVILLA")
        assert result is not None
        assert result[0] == "Ocio"

    def test_kebab_restaurantes(self) -> None:
        result = match_keyword_rule("KEBAB CORIA DEL RIO")
        assert result is not None
        assert result[0] == "Restaurantes y Bares"
        assert result[1] == 0.82

    def test_bocao_bar_restaurantes_by_strong_keyword(self) -> None:
        result = match_keyword_rule("BOCAO BAR")
        assert result is not None
        assert result[0] == "Restaurantes y Bares"
        assert result[1] == 0.82

    def test_sanafarmacia_salud(self) -> None:
        result = match_keyword_rule("SANAFARMACIA")
        assert result is not None
        assert result[0] == "Salud"

    def test_supermercados_alimentacion(self) -> None:
        result = match_keyword_rule("SUPERMERCADOS C")
        assert result is not None
        assert result[0] == "Alimentación"

    def test_primaprix_alimentacion(self) -> None:
        result = match_keyword_rule("PRIMAPRIX T88")
        assert result is not None
        assert result[0] == "Alimentación"

    def test_estanco_otros_gastos(self) -> None:
        result = match_keyword_rule("ESTANCO ODONNE")
        assert result is not None
        assert result[0] == "Otros gastos"

    def test_bar_is_suggestion_strength(self) -> None:
        result = match_keyword_rule("OLIVARES BAR")
        assert result is not None
        assert result == ("Restaurantes y Bares", 0.62)

    # ── No match ──────────────────────────────────────────────────────────────

    def test_loteria_ocio(self) -> None:
        """Loteria is now treated as a deterministic leisure/ocio keyword."""
        result = match_keyword_rule("LOTERIA CIUDAD ANTIGUA")
        assert result is not None
        assert result[0] == "Ocio"

    def test_unknown_returns_none(self) -> None:
        result = match_keyword_rule("TRANSFERENCIA NOMINA EMPRESA")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = match_keyword_rule("")
        assert result is None

    # ── Word boundary ─────────────────────────────────────────────────────────

    def test_keyword_not_matched_inside_word(self) -> None:
        """'CINE' inside 'PARACINE' or similar must not match."""
        # Construct a description that contains CINE as a substring only
        # (unlikely in practice, but validates boundary logic)
        result = match_keyword_rule("PARACINE MADRID")
        assert result is None or result[0] != "Ocio"

    def test_barcelona_does_not_match_bar(self) -> None:
        result = match_keyword_rule("BARCELONA PARKING")
        assert result is not None
        assert result[0] == "Transporte"

    def test_cafe_inside_word_does_not_match(self) -> None:
        result = match_keyword_rule("CAFETERIASINESPACIO")
        assert result is None
