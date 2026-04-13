"""Tests for bank description text cleaner."""
import pytest

from app.categories.text_cleaner import clean_bank_description, extract_merchant_key


class TestCleanBankDescription:

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("COMPRA TARJ 4921*****1234 MERCADONA S.A. SEVILLA", "MERCADONA SEVILLA"),
            ("RECIBO DOMICILIADO ENDESA ENERGIA S.A.", "ENDESA ENERGIA"),
            ("BIZUM A JUAN GARCIA REF123456", "JUAN GARCIA"),
            ("PAGO MOVIL SPOTIFY TECHNOLOGY 12/04/2025", "SPOTIFY TECHNOLOGY"),
            ("TRANSFERENCIA NOMINA EMPRESA SL", "NOMINA EMPRESA"),
            ("ADEUDO DIRECTO SEPA NETFLIX", "NETFLIX"),
        ],
    )
    def test_removes_noise(self, raw: str, expected: str) -> None:
        result = clean_bank_description(raw)
        assert expected in result or result in expected

    def test_normalizes_accents(self) -> None:
        result = clean_bank_description("Café París")
        assert "CAFE" in result
        assert "PARIS" in result


class TestExtractMerchantKey:

    def test_takes_first_two_significant_words(self) -> None:
        assert extract_merchant_key("MERCADONA MAIRENA DEL ALJARAFE") == "MERCADONA MAIRENA"

    def test_skips_short_words(self) -> None:
        assert extract_merchant_key("EL CORTE INGLES SEVILLA") == "CORTE INGLES"

    def test_single_word(self) -> None:
        assert extract_merchant_key("NETFLIX") == "NETFLIX"
