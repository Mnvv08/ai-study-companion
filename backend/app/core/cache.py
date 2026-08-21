"""
app/core/cache.py
─────────────────
Simple in-memory cache with TTL (Time To Live) for static generated study contents.
"""

import time
from typing import Any, Dict, Optional, Tuple


class InMemoryCache:
    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = default_ttl_seconds
        # Stores mapping of (document_id, endpoint_key) -> (cached_value, expiry_timestamp)
        self._cache: Dict[Tuple[str, str], Tuple[Any, float]] = {}

    def get(self, document_id: str, endpoint: str) -> Optional[Any]:
        key = (document_id, endpoint)
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                # Evict expired entry
                del self._cache[key]
        return None

    def set(self, document_id: str, endpoint: str, value: Any, ttl: Optional[int] = None) -> None:
        key = (document_id, endpoint)
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._cache[key] = (value, expiry)

    def invalidate(self, document_id: str, endpoint: str) -> None:
        key = (document_id, endpoint)
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all entries in the cache."""
        self._cache.clear()


# Shared singleton cache instance
study_cache = InMemoryCache()
