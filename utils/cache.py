"""
In-memory cache implementation for high-performance data access.

Provides TTL-based caching with automatic expiration and
memory-efficient storage patterns.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Generic, TypeVar
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """Represents a cached item with metadata."""
    
    __slots__ = ('value', 'expires_at', 'created_at', 'access_count')
    
    def __init__(self, value: T, ttl_seconds: int):
        self.value = value
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """Record an access to this entry."""
        self.access_count += 1


class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL support.
    
    Features:
    - Automatic expiration
    - LRU eviction when memory limit reached
    - Thread-safe operations
    - Statistics tracking
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of entries before eviction
            default_ttl: Default time-to-live in seconds
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                await self._delete_key(key)
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1
            
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        async with self._lock:
            ttl = ttl if ttl is not None else self._default_ttl
            
            # If key exists, update it
            if key in self._cache:
                del self._cache[key]
            
            # Evict if necessary
            while len(self._cache) >= self._max_size:
                await self._evict_oldest()
            
            self._cache[key] = CacheEntry(value, ttl)
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            return await self._delete_key(key)
    
    async def _delete_key(self, key: str) -> bool:
        """Internal delete without lock."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def _evict_oldest(self) -> None:
        """Evict the oldest (least recently used) entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._evictions += 1
            logger.debug(f"Evicted cache entry: {oldest_key}")
    
    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    async def contains(self, key: str) -> bool:
        """Check if a key exists in the cache (without updating access)."""
        async with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.is_expired():
                await self._delete_key(key)
                return False
            
            return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate_percent": round(hit_rate, 2),
                "default_ttl": self._default_ttl,
            }
    
    async def keys(self) -> list:
        """Get all non-expired keys."""
        async with self._lock:
            return [
                key for key, entry in self._cache.items()
                if not entry.is_expired()
            ]
    
    async def size(self) -> int:
        """Get current cache size (non-expired entries only)."""
        async with self._lock:
            return sum(
                1 for entry in self._cache.values()
                if not entry.is_expired()
            )


# Global cache instance
_cache: Optional[InMemoryCache] = None


def get_cache(max_size: int = 10000, default_ttl: int = 300) -> InMemoryCache:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        _cache = InMemoryCache(max_size=max_size, default_ttl=default_ttl)
    return _cache


__all__ = ['InMemoryCache', 'CacheEntry', 'get_cache']
