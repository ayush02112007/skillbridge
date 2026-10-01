"""Caching with a Redis backend and an in-process fallback.

The application never hard-depends on Redis: if it is unreachable (local dev,
tests) the cache degrades to a bounded in-memory dictionary so behaviour stays
identical, only unshared.
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("cache")

_memory: dict[str, tuple[float, str]] = {}
_MEMORY_MAX_KEYS = 5000
_redis: Any = None
_redis_checked = False


async def _get_redis() -> Any:
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True
    if not settings.CACHE_ENABLED:
        return None
    try:
        import redis.asyncio as aioredis  # type: ignore[import-not-found]

        client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True,
            socket_connect_timeout=1.5, socket_timeout=1.5,
        )
        await client.ping()
        _redis = client
        log.info("cache.redis_connected")
    except Exception as exc:  # pragma: no cover - depends on infra
        log.warning("cache.redis_unavailable", detail=str(exc)[:200])
        _redis = None
    return _redis


def _prune_memory() -> None:
    now = time.time()
    for key in [k for k, (exp, _) in _memory.items() if exp < now]:
        _memory.pop(key, None)
    if len(_memory) > _MEMORY_MAX_KEYS:
        for key in list(_memory)[: len(_memory) - _MEMORY_MAX_KEYS]:
            _memory.pop(key, None)


async def cache_get(key: str) -> Any | None:
    if not settings.CACHE_ENABLED:
        return None
    client = await _get_redis()
    if client is not None:
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        except Exception:  # pragma: no cover
            return None
    _prune_memory()
    entry = _memory.get(key)
    if entry and entry[0] > time.time():
        return json.loads(entry[1])
    return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    if not settings.CACHE_ENABLED:
        return
    ttl = ttl or settings.CACHE_DEFAULT_TTL
    try:
        raw = json.dumps(value, default=str)
    except (TypeError, ValueError):  # pragma: no cover - non serialisable
        return
    client = await _get_redis()
    if client is not None:
        try:
            await client.setex(key, ttl, raw)
            return
        except Exception as exc:  # pragma: no cover - Redis is optional
            # Never fail a request because the cache is unavailable; fall back
            # to the in-process tier, but leave a trace for diagnosis.
            log.debug("cache.set_failed", key=key, error=str(exc)[:160])
    _prune_memory()
    _memory[key] = (time.time() + ttl, raw)


async def cache_delete(*keys: str) -> None:
    client = await _get_redis()
    if client is not None:
        try:
            await client.delete(*keys)
        except Exception as exc:  # pragma: no cover - Redis is optional
            log.debug("cache.delete_failed", keys=len(keys), error=str(exc)[:160])
    for key in keys:
        _memory.pop(key, None)


async def cache_delete_prefix(prefix: str) -> None:
    client = await _get_redis()
    if client is not None:
        try:
            async for key in client.scan_iter(match=f"{prefix}*", count=200):
                await client.delete(key)
        except Exception as exc:  # pragma: no cover - Redis is optional
            log.debug("cache.delete_prefix_failed", prefix=prefix, error=str(exc)[:160])
    for key in [k for k in _memory if k.startswith(prefix)]:
        _memory.pop(key, None)


async def cache_ping() -> bool:
    client = await _get_redis()
    if client is None:
        return False
    try:
        await client.ping()
        return True
    except Exception:  # pragma: no cover
        return False


def cache_key(*parts: Any) -> str:
    return "sb:" + ":".join(str(p) for p in parts)
