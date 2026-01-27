"""
Production-grade caching layer
Redis-backed cache with TTL and invalidation strategies
"""
import json
import hashlib
import pickle
from typing import Any, Optional, Callable
from functools import wraps
import redis
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-backed cache manager with automatic serialization
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_ttl: int = 3600,
        prefix: str = "cache"
    ):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.prefix = prefix
    
    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.prefix}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            cache_key = self._make_key(key)
            data = self.redis.get(cache_key)
            
            if data is None:
                return None
            
            # Try to deserialize
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                # Fallback to pickle for complex objects
                return pickle.loads(data)
        
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = default)
            nx: Only set if key doesn't exist
        """
        try:
            cache_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Try JSON serialization first
            try:
                data = json.dumps(value)
            except (TypeError, ValueError):
                # Fallback to pickle for complex objects
                data = pickle.dumps(value)
            
            if nx:
                return self.redis.set(cache_key, data, ex=ttl, nx=True)
            else:
                return self.redis.set(cache_key, data, ex=ttl)
        
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            cache_key = self._make_key(key)
            return bool(self.redis.delete(cache_key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            cache_pattern = self._make_key(pattern)
            keys = self.redis.keys(cache_pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            cache_key = self._make_key(key)
            return bool(self.redis.exists(cache_key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        try:
            cache_key = self._make_key(key)
            return self.redis.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            cache_key = self._make_key(key)
            return self.redis.incrby(cache_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    def clear_all(self) -> int:
        """Clear all cache entries with prefix"""
        return self.delete_pattern("*")


def cache_key_builder(*args, **kwargs) -> str:
    """
    Build cache key from function arguments
    """
    # Create a string representation of args and kwargs
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # For complex objects, use their string representation
            key_parts.append(str(type(arg).__name__))
    
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
    
    key_string = ":".join(key_parts)
    
    # Hash if too long
    if len(key_string) > 200:
        return hashlib.md5(key_string.encode()).hexdigest()
    
    return key_string


def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching function results
    
    Usage:
        @cached(ttl=3600, key_prefix="product")
        def get_product(asin: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get cache manager from first arg (usually self or request)
            cache_manager = None
            
            if args and hasattr(args[0], "cache"):
                cache_manager = args[0].cache
            elif "cache" in kwargs:
                cache_manager = kwargs["cache"]
            
            if not cache_manager:
                # No cache available, execute function
                return await func(*args, **kwargs)
            
            # Build cache key
            prefix = key_prefix or func.__name__
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                key_suffix = cache_key_builder(*args[1:], **kwargs)  # Skip self
            
            cache_key = f"{prefix}:{key_suffix}"
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get cache manager
            cache_manager = None
            
            if args and hasattr(args[0], "cache"):
                cache_manager = args[0].cache
            elif "cache" in kwargs:
                cache_manager = kwargs["cache"]
            
            if not cache_manager:
                return func(*args, **kwargs)
            
            # Build cache key
            prefix = key_prefix or func.__name__
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                key_suffix = cache_key_builder(*args[1:], **kwargs)
            
            cache_key = f"{prefix}:{key_suffix}"
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ProductCache:
    """
    Specialized cache for product data with smart invalidation
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    def get_product(self, asin: str) -> Optional[dict]:
        """Get product from cache"""
        return self.cache.get(f"product:{asin}")
    
    def set_product(self, asin: str, data: dict, ttl: int = 3600) -> bool:
        """Cache product data"""
        return self.cache.set(f"product:{asin}", data, ttl=ttl)
    
    def invalidate_product(self, asin: str) -> bool:
        """Invalidate product cache"""
        return self.cache.delete(f"product:{asin}")
    
    def get_search_results(self, keyword: str, page: int = 1) -> Optional[list]:
        """Get search results from cache"""
        key = f"search:{keyword}:page:{page}"
        return self.cache.get(key)
    
    def set_search_results(self, keyword: str, page: int, results: list, ttl: int = 1800) -> bool:
        """Cache search results (shorter TTL as they change frequently)"""
        key = f"search:{keyword}:page:{page}"
        return self.cache.set(key, results, ttl=ttl)
    
    def invalidate_search(self, keyword: str) -> int:
        """Invalidate all search results for keyword"""
        return self.cache.delete_pattern(f"search:{keyword}:*")
