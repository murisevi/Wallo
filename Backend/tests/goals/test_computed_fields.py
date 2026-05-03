# Backend/tests/goals/test_computed_fields.py
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.goals.service import (
    _compute_days_remaining,
    _compute_estimated_completion,
    _compute_motivational_message,
    _compute_pace_status,
    _compute_percentage,
)


def test_percentage_normal():
    assert _compute_percentage(Decimal("250"), Decimal("1000")) == 25.0


def test_percentage_complete():
    assert _compute_percentage(Decimal("1000"), Decimal("1000")) == 100.0


def test_percentage_over():
    assert _compute_percentage(Decimal("1200"), Decimal("1000")) == 120.0


def test_percentage_zero_current():
    assert _compute_percentage(Decimal("0"), Decimal("1000")) == 0.0


def test_days_remaining_future():
    future = date.today() + timedelta(days=30)
    assert _compute_days_remaining(future) == 30


def test_days_remaining_past():
    past = date.today() - timedelta(days=5)
    assert _compute_days_remaining(past) == -5


def test_days_remaining_none():
    assert _compute_days_remaining(None) is None


def test_estimated_completion_basic():
    result = _compute_estimated_completion(
        Decimal("0"), Decimal("1200"), Decimal("100")
    )
    assert result is not None
    assert result > date.today()


def test_estimated_completion_no_monthly():
    assert _compute_estimated_completion(Decimal("0"), Decimal("1000"), None) is None


def test_estimated_completion_already_done():
    assert (
        _compute_estimated_completion(Decimal("1000"), Decimal("1000"), Decimal("100"))
        is None
    )


def test_pace_status_ahead():
    deadline = date.today() + timedelta(days=300)
    result = _compute_pace_status(
        Decimal("0"), Decimal("1000"), Decimal("200"), deadline
    )
    assert result == "ahead"


def test_pace_status_on_track():
    deadline = date.today() + timedelta(days=300)
    result = _compute_pace_status(
        Decimal("0"), Decimal("1000"), Decimal("100"), deadline
    )
    assert result == "on_track"


def test_pace_status_at_risk():
    deadline = date.today() + timedelta(days=60)
    result = _compute_pace_status(
        Decimal("0"), Decimal("1000"), Decimal("50"), deadline
    )
    assert result == "at_risk"


def test_pace_status_no_deadline():
    assert _compute_pace_status(Decimal("0"), Decimal("1000"), Decimal("100"), None) is None


def test_pace_status_no_monthly():
    deadline = date.today() + timedelta(days=60)
    assert _compute_pace_status(Decimal("0"), Decimal("1000"), None, deadline) is None


@pytest.mark.parametrize(
    "percentage,expected",
    [
        (100.0, "¡Objetivo cumplido! 🎉"),
        (120.0, "¡Objetivo cumplido! 🎉"),
        (75.0, "¡Ya casi lo tienes!"),
        (80.0, "¡Ya casi lo tienes!"),
        (50.0, "¡Más de la mitad! Sigue así"),
        (60.0, "¡Más de la mitad! Sigue así"),
        (25.0, "Vas por buen camino"),
        (40.0, "Vas por buen camino"),
        (1.0, "¡Buen comienzo!"),
        (24.9, "¡Buen comienzo!"),
        (0.0, "¡Empieza a ahorrar hoy!"),
    ],
)
def test_motivational_message(percentage, expected):
    assert _compute_motivational_message(percentage) == expected
