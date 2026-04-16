"""Unit tests for the recurring charge detection algorithm.

No database required — detector is a pure function.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.recurring_charges.detector import DetectedCharge, detect_recurring


def _txns(
    merchant_key: str,
    dates: list[date],
    amount: str = "9.99",
    currency: str = "EUR",
    is_subscription: bool = False,
) -> list[tuple]:
    """Build transaction tuples for the detector."""
    display = merchant_key.title()
    return [
        (merchant_key, display, Decimal(amount), currency, d, is_subscription)
        for d in dates
    ]


BASE = date(2024, 1, 15)


class TestMonthlyDetection:
    def test_three_monthly_charges_detected(self):
        txns = _txns("NETFLIX", [BASE, BASE + timedelta(days=31), BASE + timedelta(days=62)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].periodicity == "MONTHLY"
        assert result[0].occurrence_count == 3
        assert result[0].merchant_key == "NETFLIX"

    def test_two_monthly_charges_detected(self):
        """Two occurrences are enough to trigger detection."""
        txns = _txns("SPOTIFY", [BASE, BASE + timedelta(days=30)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].occurrence_count == 2

    def test_next_predicted_date_is_last_plus_30(self):
        last = BASE + timedelta(days=60)
        txns = _txns("AMAZON", [BASE, BASE + timedelta(days=30), last])
        result = detect_recurring(txns)
        assert result[0].next_predicted_date == last + timedelta(days=30)

    def test_last_seen_date_is_most_recent(self):
        last = BASE + timedelta(days=60)
        txns = _txns("AMAZON", [BASE, BASE + timedelta(days=30), last])
        result = detect_recurring(txns)
        assert result[0].last_seen_date == last


class TestWeeklyDetection:
    def test_three_weekly_charges_detected(self):
        txns = _txns("GYM", [BASE, BASE + timedelta(days=7), BASE + timedelta(days=14)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].periodicity == "WEEKLY"

    def test_next_predicted_date_is_last_plus_7(self):
        last = BASE + timedelta(days=14)
        txns = _txns("GYM", [BASE, BASE + timedelta(days=7), last])
        result = detect_recurring(txns)
        assert result[0].next_predicted_date == last + timedelta(days=7)


class TestAnnualDetection:
    def test_annual_pattern_detected(self):
        txns = _txns("INSURANCE", [BASE, BASE + timedelta(days=365)])
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0].periodicity == "ANNUAL"


class TestIrregularPatterns:
    def test_single_occurrence_not_detected(self):
        txns = _txns("ONEOFF", [BASE])
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_irregular_intervals_not_detected(self):
        """Very different intervals don't form a pattern."""
        dates = [BASE, BASE + timedelta(days=5), BASE + timedelta(days=45)]
        txns = _txns("RANDOM", dates)
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_mixed_intervals_not_detected(self):
        """Mix of weekly and monthly intervals → no pattern."""
        dates = [BASE, BASE + timedelta(days=7), BASE + timedelta(days=37)]
        txns = _txns("MIXED", dates)
        result = detect_recurring(txns)
        assert len(result) == 0


class TestSubscriptionFlag:
    def test_subscription_flag_propagated(self):
        txns = [
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE, True),
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE + timedelta(days=30), True),
        ]
        result = detect_recurring(txns)
        assert result[0].is_subscription is True

    def test_any_subscription_occurrence_sets_flag(self):
        """Even one occurrence with is_subscription=True sets the flag."""
        txns = [
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE, False),
            ("NETFLIX", "Netflix", Decimal("9.99"), "EUR", BASE + timedelta(days=30), True),
        ]
        result = detect_recurring(txns)
        assert result[0].is_subscription is True

    def test_no_subscription_flag_when_not_categorised(self):
        txns = _txns("AMZN", [BASE, BASE + timedelta(days=30)], is_subscription=False)
        result = detect_recurring(txns)
        assert result[0].is_subscription is False


class TestMultipleMerchants:
    def test_two_merchants_detected_independently(self):
        txns = (
            _txns("NETFLIX", [BASE, BASE + timedelta(days=30)])
            + _txns("SPOTIFY", [BASE, BASE + timedelta(days=30)])
        )
        result = detect_recurring(txns)
        assert len(result) == 2
        keys = {r.merchant_key for r in result}
        assert keys == {"NETFLIX", "SPOTIFY"}
