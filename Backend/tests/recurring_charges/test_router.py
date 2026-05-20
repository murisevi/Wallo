"""API tests for recurring charge review endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.main import app
from app.recurring_charges.models import RecurringCharge
from tests.conftest import TestSessionLocal


class FakeRedis:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        self.matches: list[str] = []
        self.deleted: list[str] = []

    async def scan(
        self, cursor: int, match: str, count: int
    ) -> tuple[int, list[str]]:
        self.matches.append(match)
        return 0, [key for key in self.keys if key == match]

    async def delete(self, *keys: str) -> None:
        self.deleted.extend(keys)


async def _register_and_login(client: AsyncClient) -> tuple[str, uuid.UUID]:
    email = f"recurring-router-{uuid.uuid4()}@example.com"
    password = "CachePass1!"  # noqa: S105
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Recurring Router", "password": password},
    )
    user_id = uuid.UUID(register_resp.json()["id"])

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return login_resp.json()["access_token"], user_id


@pytest.mark.asyncio
async def test_dismiss_invalidates_dashboard_cache(client: AsyncClient) -> None:
    token, user_id = await _register_and_login(client)
    charge_id = uuid.uuid4()

    async with TestSessionLocal() as db:
        db.add(
            RecurringCharge(
                id=charge_id,
                user_id=user_id,
                merchant_key="NETFLIX",
                display_name="Netflix",
                amount=Decimal("9.99"),
                currency="EUR",
                periodicity="MONTHLY",
                status="possible",
                occurrence_count=3,
                next_predicted_date=date(2024, 4, 15),
                last_seen_date=date(2024, 3, 15),
            )
        )
        await db.commit()

    fake_redis = FakeRedis(keys=[f"dashboard:{user_id}"])
    previous_redis = getattr(app.state, "redis", None)
    app.state.redis = fake_redis
    try:
        resp = await client.patch(
            f"/api/v1/recurring-charges/{charge_id}/dismiss",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.state.redis = previous_redis

    assert resp.status_code == 204
    assert fake_redis.matches == [f"dashboard:{user_id}"]
    assert fake_redis.deleted == [f"dashboard:{user_id}"]

    async with TestSessionLocal() as db:
        dismissed = await db.get(RecurringCharge, charge_id)
        assert dismissed is not None
        assert dismissed.status == "dismissed"
