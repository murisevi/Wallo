"""Tests for bank description text cleaner.

Covers real bank transaction description formats as seen in production data
from Enable Banking (BBVA sandbox / Mock ASPSP).
"""

import pytest

from app.categories.text_cleaner import (
    clean_bank_description,
    detect_transaction_type,
    extract_merchant_key,
)


# ── clean_bank_description ────────────────────────────────────────────────────


class TestCleanBankDescription:
    """Real-world bank description formats."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            # ── PAGO MOVIL EN ──────────────────────────────────────────────
            (
                "PAGO MOVIL EN MERCADONA CASIN, TOMARES ES, TARJ. :*428024",
                "MERCADONA CASIN",
            ),
            (
                "PAGO MOVIL EN COFFE GALOS, SEVILLA ES, TARJ. :*428024",
                "COFFE GALOS",
            ),
            (
                "PAGO MOVIL EN METRO SEVILLA, SEVILLA ES, TARJ. :*428024",
                "METRO SEVILLA",
            ),
            (
                "PAGO MOVIL EN LIDL JUAN DE AZ, SAN JUAN DE AES, TARJ. :*428024",
                "LIDL JUAN DE AZ",
            ),
            # ── COMPRA INTERNET EN ────────────────────────────────────────
            (
                "COMPRA INTERNET EN AREAFIT MAIRENA, VILLAVERDE DEES, TARJ.",
                "AREAFIT MAIRENA",
            ),
            # ── COMPRA (generic) ──────────────────────────────────────────
            (
                "COMPRA FERMENTO, Sevilla, TARJETA 5489010532428024, COMISION 0.00",
                "FERMENTO",
            ),
            (
                "COMPRA CLAUDE.AI SUBSCRIPTION, SAN FRANCISCO, TARJETA 5489010532428024",
                "CLAUDE AI SUBSCRIPTION",
            ),
            # ── BIZUM A FAVOR DE ─────────────────────────────────────────
            (
                "BIZUM A FAVOR DE LUCIA AMIAN LOPEZ CONCEPTO: Sin concepto",
                "LUCIA AMIAN LOPEZ",
            ),
            (
                "BIZUM A FAVOR DE Martin Vergara Castro CONCEPTO: sierra nevada",
                "MARTIN VERGARA CASTRO",
            ),
            # ── BIZUM DE ─────────────────────────────────────────────────
            (
                "BIZUM DE Alvaro Ruiz Moreno CONCEPTO b",
                "ALVARO RUIZ MORENO",
            ),
            (
                "BIZUM DE CLARA DEL ESTAD HUMBERT CONCEPTO Pizzi",
                "CLARA DEL ESTAD HUMBERT",
            ),
            # ── RECIBO ───────────────────────────────────────────────────
            (
                "RECIBO PayPal Europe S.a.r.l. et Cie S.C.A",
                "PAYPAL EUROPE",
            ),
            (
                "RECIBO DOMICILIADO ENDESA ENERGIA S.A.",
                "ENDESA ENERGIA",
            ),
            # ── TRANSFERENCIA ─────────────────────────────────────────────
            (
                "TRANSFERENCIA INMEDIATA DE PAYPAL, CONCEPTO INSTANT TRANSFER",
                "PAYPAL",
            ),
            (
                "TRANSFERENCIA DE SEVILLANO MOREJON MARIA AFRICA, CONCEPTO test",
                "SEVILLANO MOREJON MARIA AFRICA",
            ),
            # ── Legacy / other formats (kept working) ──────────────────
            (
                "COMPRA TARJ 4921*****1234 MERCADONA S.A. SEVILLA",
                "MERCADONA SEVILLA",
            ),
            (
                "ADEUDO DIRECTO SEPA NETFLIX",
                "NETFLIX",
            ),
        ],
    )
    def test_real_bank_formats(self, raw: str, expected: str) -> None:
        result = clean_bank_description(raw)
        assert result == expected, (
            f"\n  raw      = {raw!r}\n"
            f"  expected = {expected!r}\n"
            f"  got      = {result!r}"
        )

    def test_normalizes_accents(self) -> None:
        result = clean_bank_description("Café París")
        assert "CAFE" in result
        assert "PARIS" in result

    def test_pago_movil_no_leading_en(self) -> None:
        """The word 'EN' must not survive as the first word after cleaning."""
        result = clean_bank_description(
            "PAGO MOVIL EN MERCADONA CASIN, TOMARES ES, TARJ. :*428024"
        )
        assert not result.startswith("EN "), f"Leading 'EN' not removed: {result!r}"

    def test_no_city_code_es(self) -> None:
        """City + 'ES' country codes must be stripped."""
        result = clean_bank_description(
            "PAGO MOVIL EN LIDL MAIRENA AL, MAIRENA DEL AES, TARJ. :*428024"
        )
        assert "ES" not in result.split(), f"Country code 'ES' survived: {result!r}"

    def test_no_tarj_fragment(self) -> None:
        """TARJ / TARJETA fragments must be stripped."""
        result = clean_bank_description(
            "COMPRA eDreams, Madrid, TARJETA 5489010532428024, COMISION 0.00"
        )
        assert "TARJ" not in result, f"TARJ fragment survived: {result!r}"

    def test_no_concepto(self) -> None:
        """CONCEPTO field must not appear in the cleaned output."""
        result = clean_bank_description(
            "BIZUM DE Alvaro Ruiz Moreno CONCEPTO comida"
        )
        assert "CONCEPTO" not in result, f"CONCEPTO survived: {result!r}"

    def test_no_commission(self) -> None:
        """COMISION amounts must be stripped."""
        result = clean_bank_description(
            "COMPRA eDreams, Madrid, TARJETA 5489010532428024, COMISION 0.00"
        )
        assert "COMISION" not in result, f"COMISION survived: {result!r}"


# ── detect_transaction_type ───────────────────────────────────────────────────


class TestDetectTransactionType:

    @pytest.mark.parametrize(
        "raw, expected_type",
        [
            # Bizum sent (outgoing)
            (
                "BIZUM A FAVOR DE LUCIA AMIAN LOPEZ CONCEPTO: Sin concepto",
                "bizum_sent",
            ),
            (
                "BIZUM A FAVOR DE Martin Vergara Castro CONCEPTO: sierra nevada",
                "bizum_sent",
            ),
            # Bizum received (incoming)
            (
                "BIZUM DE Alvaro Ruiz Moreno CONCEPTO b",
                "bizum_received",
            ),
            (
                "BIZUM DE CLARA DEL ESTAD HUMBERT CONCEPTO Pizzi",
                "bizum_received",
            ),
            # Card payments
            (
                "PAGO MOVIL EN MERCADONA CASIN, TOMARES ES, TARJ. :*428024",
                "card_payment",
            ),
            (
                "COMPRA INTERNET EN AREAFIT MAIRENA, VILLAVERDE DEES, TARJ.",
                "card_payment",
            ),
            (
                "COMPRA eDreams, Madrid, TARJETA 5489010532428024, COMISION 0.00",
                "card_payment",
            ),
            (
                "ANULACION PAGO MOVIL EN LA CAMARA, SEVILLA ES, TARJ.",
                "card_payment",
            ),
            # Direct debit / recurring
            (
                "RECIBO PayPal Europe S.a.r.l. et Cie S.C.A",
                "direct_debit",
            ),
            (
                "ADEUDO DIRECTO SEPA NETFLIX",
                "direct_debit",
            ),
            # Transfers
            (
                "TRANSFERENCIA INMEDIATA DE PAYPAL, CONCEPTO INSTANT TRANSFER",
                "transfer",
            ),
            (
                "TRANSFERENCIA DE SEVILLANO MOREJON MARIA AFRICA, CONCEPTO test",
                "transfer",
            ),
            # Cash
            (
                "RETIRADA DE EFECTIVO EN CAJERO AUTOMATICO 0049737",
                "cash",
            ),
        ],
    )
    def test_type_detection(self, raw: str, expected_type: str) -> None:
        result = detect_transaction_type(raw)
        assert result == expected_type, (
            f"\n  raw      = {raw!r}\n"
            f"  expected = {expected_type!r}\n"
            f"  got      = {result!r}"
        )


# ── extract_merchant_key ──────────────────────────────────────────────────────


class TestExtractMerchantKey:

    def test_takes_first_two_significant_words(self) -> None:
        assert extract_merchant_key("MERCADONA MAIRENA DEL ALJARAFE") == "MERCADONA MAIRENA"

    def test_skips_short_words(self) -> None:
        # "EL" and "CORTE" → "CORTE" is >2 chars, skip "EL"
        assert extract_merchant_key("EL CORTE INGLES SEVILLA") == "CORTE INGLES"

    def test_skips_leading_prepositions(self) -> None:
        """Residual 'EN' or 'DE' after prefix removal must be skipped."""
        assert extract_merchant_key("EN CARREF AZNALFAR") == "CARREF AZNALFAR"
        assert extract_merchant_key("DE PAYPAL EUROPE") == "PAYPAL EUROPE"

    def test_single_word(self) -> None:
        assert extract_merchant_key("NETFLIX") == "NETFLIX"

    def test_pago_movil_result(self) -> None:
        """Full pipeline: PAGO MOVIL EN → clean → merchant key."""
        cleaned = clean_bank_description(
            "PAGO MOVIL EN MERCADONA CASIN, TOMARES ES, TARJ. :*428024"
        )
        assert extract_merchant_key(cleaned) == "MERCADONA CASIN"

    def test_compra_result(self) -> None:
        """Full pipeline: COMPRA → clean → merchant key."""
        cleaned = clean_bank_description(
            "COMPRA INTERNET EN AREAFIT MAIRENA, VILLAVERDE DEES, TARJ."
        )
        assert extract_merchant_key(cleaned) == "AREAFIT MAIRENA"
