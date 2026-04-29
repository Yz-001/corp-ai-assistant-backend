"""Redis connection and utilities."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    """Create Redis client."""
    return redis.from_url(
        settings.redis_dsn_str,
        password=settings.redis_password,
        encoding="utf-8",
        decode_responses=True,
    )


redis_client = create_redis_client()


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency for getting Redis client."""
    yield redis_client


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    redis_client = create_redis_client()


async def close_redis() -> None:
    """Close Redis connection."""
    await redis_client.close()


# ============ Redis Key Utilities ============


class RedisKeys:
    """Redis key patterns."""

    # Online users
    ONLINE_USERS = "online:users"
    ONLINE_USER_TTL = "online:user:{user_id}"

    # Active users
    ACTIVE_USERS = "active:users"
    ACTIVE_USER_TTL = "active:user:{user_id}"

    # Session
    SESSION_PREFIX = "session:"
    SESSION_USER = "session:user:{session_id}"
    USER_SESSIONS = "user:sessions:{user_id}"

    # Rate limiting
    RATE_LIMIT_PREFIX = "rate_limit:"
    RATE_LIMIT_KEY = "rate_limit:{key}:{window}"

    # Cache
    CACHE_PREFIX = "cache:"
    CACHE_TENANT = "cache:tenant:{tenant_id}"
    CACHE_USER = "cache:user:{user_id}"
    CACHE_PROMPTS = "cache:prompts:{tenant_id}:{channel}"
    CACHE_SUGGESTIONS = "cache:suggestions:{tenant_id}:{channel}"

    # Metrics
    METRICS_PREFIX = "metrics:"
    METRICS_REQUESTS = "metrics:requests:{tenant_id}:{date}"
    METRICS_TOKENS = "metrics:tokens:{tenant_id}:{date}"
    METRICS_TOOL_CALLS = "metrics:tool_calls:{tenant_id}:{date}"

    # SSE
    SSE_CHANNEL = "sse:channel:{user_id}"
    SSE_MESSAGE = "sse:message:{message_id}"


# ============ Redis Helper Functions ============


async def set_json(key: str, value: Any, ttl: int | None = None) -> bool:
    """Set JSON value in Redis."""
    data = json.dumps(value, ensure_ascii=False, default=str)
    if ttl:
        await redis_client.setex(key, ttl, data)
    else:
        await redis_client.set(key, data)
    return True


async def get_json(key: str) -> Any | None:
    """Get JSON value from Redis."""
    data = await redis_client.get(key)
    if data is None:
        return None
    return json.loads(data)


async def delete_key(key: str) -> bool:
    """Delete key from Redis."""
    return bool(await redis_client.delete(key))


async def exists(key: str) -> bool:
    """Check if key exists."""
    return bool(await redis_client.exists(key))


async def set_ttl(key: str, ttl: int) -> bool:
    """Set TTL for key."""
    return bool(await redis_client.expire(key, ttl))


async def increment(key: str, amount: int = 1) -> int:
    """Increment counter."""
    return await redis_client.incrby(key, amount)


async def add_to_set(key: str, *values: str) -> int:
    """Add values to set."""
    return await redis_client.sadd(key, *values)


async def remove_from_set(key: str, *values: str) -> int:
    """Remove values from set."""
    return await redis_client.srem(key, *values)


async def get_set_members(key: str) -> set[str]:
    """Get all members of set."""
    return await redis_client.smembers(key)


async def set_count(key: str) -> int:
    """Get set member count."""
    return await redis_client.scard(key)


# ============ Online User Tracking ============


async def track_online_user(user_id: str) -> None:
    """Track user as online."""
    now = int(__import__("time").time())
    await redis_client.zadd(
        RedisKeys.ONLINE_USERS,
        {user_id: now},
    )
    # Cleanup old entries (older than TTL)
    cutoff = now - settings.online_user_ttl_seconds
    await redis_client.zremrangebyscore(RedisKeys.ONLINE_USERS, "-inf", cutoff)


async def get_online_users_count() -> int:
    """Get count of online users."""
    try:
        now = int(__import__("time").time())
        cutoff = now - settings.online_user_ttl_seconds
        # Remove stale entries first
        await redis_client.zremrangebyscore(RedisKeys.ONLINE_USERS, "-inf", cutoff)
        return await redis_client.zcard(RedisKeys.ONLINE_USERS)
    except Exception:
        # Redis not available, return 0
        return 0


async def is_user_online(user_id: str) -> bool:
    """Check if user is online."""
    score = await redis_client.zscore(RedisKeys.ONLINE_USERS, user_id)
    if score is None:
        return False
    now = int(__import__("time").time())
    return now - int(score) <= settings.online_user_ttl_seconds


async def remove_online_user(user_id: str) -> None:
    """Remove user from online tracking."""
    await redis_client.zrem(RedisKeys.ONLINE_USERS, user_id)


# ============ Rate Limiting ============


async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int, int]:
    """
    Check rate limit using sliding window.
    Returns: (is_allowed, current_count, remaining)
    """
    full_key = RedisKeys.RATE_LIMIT_KEY.format(key=key, window=window_seconds)
    current = await redis_client.get(full_key)

    if current is None:
        await redis_client.setex(full_key, window_seconds, 1)
        return True, 1, max_requests - 1

    current_count = int(current)
    if current_count >= max_requests:
        ttl = await redis_client.ttl(full_key)
        return False, current_count, 0

    await redis_client.incr(full_key)
    return True, current_count + 1, max_requests - current_count - 1