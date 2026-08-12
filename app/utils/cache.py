"""
Lightweight in-memory TTL cache.

Deliberately NOT a database or external cache — this is a single-process,
best-effort cache to avoid hammering upstream sites with duplicate requests
in a short window (per Phase 11: no unnecessarily complicated persistence
layer). If the process restarts, the cache is simply empty again.
"""
import time
from typing import Any, Callable, Optional, Awaitable

from app.config import settings

_store: dict[str, tuple[float, Any]] = {}


def _evict_if_full() -> None:
    if len(_store) <= settings.CACHE_MAX_ENTRIES:
        return
    # Drop the oldest ~10% of entries (cheap approximate LRU-ish eviction).
    n_to_drop = max(1, len(_store) // 10)
    oldest = sorted(_store.items(), key=lambda kv: kv[1][0])[:n_to_drop]
    for k, _ in oldest:
        _store.pop(k, None)


def cache_get(key: str) -> Optional[Any]:
    if not settings.CACHE_ENABLED:
        return None
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        _store.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    if not settings.CACHE_ENABLED or ttl_seconds <= 0:
        return
    _evict_if_full()
    _store[key] = (time.monotonic() + ttl_seconds, value)


def cache_clear() -> None:
    _store.clear()


async def get_or_set(key: str, ttl_seconds: int, producer: Callable[[], Awaitable[Any]]) -> Any:
    """Return the cached value for `key`, or await `producer()` and cache the result."""
    cached = cache_get(key)
    if cached is not None:
        return cached
    value = await producer()
    cache_set(key, value, ttl_seconds)
    return value
