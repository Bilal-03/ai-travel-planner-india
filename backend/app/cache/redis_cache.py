"""
Caching layer — Upstash Redis when available, in-memory dict fallback.
Decorator-based caching with configurable TTL for each external API.
"""

import json
import hashlib
import logging
import time
from functools import wraps
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── In-memory fallback cache ──────────────────────────────────────────

_memory_cache: dict[str, tuple[Any, float]] = {}  # key → (value, expire_timestamp)


class CacheClient:
    """Unified cache interface — Redis or in-memory."""

    def __init__(self):
        self._redis = None
        self._try_connect_redis()

    def _try_connect_redis(self):
        """Attempt to connect to Upstash Redis. Fall back silently."""
        try:
            from app.config import settings

            if settings.upstash_redis_url and settings.upstash_redis_token:
                import redis as redis_lib

                self._redis = redis_lib.from_url(
                    settings.upstash_redis_url,
                    password=settings.upstash_redis_token,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                self._redis.ping()
                logger.info("✅ Connected to Upstash Redis")
            else:
                logger.info("ℹ️  No Redis config — using in-memory cache")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed, using in-memory cache: {e}")
            self._redis = None

    def get(self, key: str) -> Optional[str]:
        if self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass

        # In-memory fallback
        if key in _memory_cache:
            value, expires = _memory_cache[key]
            if time.time() < expires:
                return value
            del _memory_cache[key]
        return None

    def set(self, key: str, value: str, ttl_seconds: int = 3600):
        if self._redis:
            try:
                self._redis.setex(key, ttl_seconds, value)
                return
            except Exception:
                pass

        # In-memory fallback
        _memory_cache[key] = (value, time.time() + ttl_seconds)

    def delete(self, key: str):
        if self._redis:
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        _memory_cache.pop(key, None)


# ── Singleton ─────────────────────────────────────────────────────────

_cache_client: Optional[CacheClient] = None


def get_cache() -> CacheClient:
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
    return _cache_client


# ── Decorator ─────────────────────────────────────────────────────────

def cached(prefix: str, ttl_seconds: int = 3600):
    """
    Decorator that caches function results.

    Usage:
        @cached("geocode", ttl_seconds=86400 * 30)
        async def geocode_city(city: str) -> dict:
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function args
            key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
            cache_key = f"travel:{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

            cache = get_cache()
            hit = cache.get(cache_key)
            if hit:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(hit)

            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            if result is not None:
                try:
                    cache.set(cache_key, json.dumps(result, default=str), ttl_seconds)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to cache result for {cache_key}: {e}")

            return result

        return wrapper

    return decorator
