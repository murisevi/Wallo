"""Redis cache helpers for Wallo.

Provides a thin wrapper around redis.asyncio so that:
- Cache misses fall back to executing the real fetch function.
- If Redis is unavailable the whole app keeps working (graceful degradation).
- Callers just need to call `cached_response()` — no Redis awareness required.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def cached_response(
    redis: Any | None,
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Coroutine[Any, Any, T]],
) -> T:
    """Return a cached value from Redis, or fetch + cache it on miss.

    Args:
        redis: An active ``redis.asyncio.Redis`` client, or ``None`` when Redis
               is unavailable (the function degrades gracefully to a direct call).
        key:   Cache key string.
        ttl:   Time-to-live in seconds.
        fetch_fn: Async callable that returns the value to cache on miss.

    Returns:
        The cached or freshly fetched value, deserialized from JSON.
    """
    if redis is not None:
        try:
            raw = await redis.get(key)
            if raw is not None:
                logger.debug("Cache HIT  key=%s", key)
                return json.loads(raw)  # type: ignore[return-value]
        except Exception as exc:
            logger.warning(
                "Redis GET failed (key=%s): %s — falling back to DB", key, exc
            )

    result = await fetch_fn()

    if redis is not None:
        try:
            await redis.setex(key, ttl, json.dumps(result, default=str))
            logger.debug("Cache SET  key=%s  ttl=%ds", key, ttl)
        except Exception as exc:
            logger.warning("Redis SET failed (key=%s): %s", key, exc)

    return result


async def invalidate_cache(redis: Any | None, pattern: str) -> None:
    """Delete all Redis keys matching *pattern* (uses SCAN to avoid blocking).

    No-op when Redis is unavailable.
    """
    if redis is None:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
        logger.debug("Cache invalidated pattern=%s", pattern)
    except Exception as exc:
        logger.warning("Redis invalidate failed (pattern=%s): %s", pattern, exc)
