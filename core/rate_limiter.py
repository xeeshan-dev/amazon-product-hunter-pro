"""
Production-grade rate limiting
Supports per-user, per-IP, and global rate limits with Redis backend
"""
import time
import asyncio
from typing import Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
import redis
from fastapi import HTTPException, Request
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with Redis backend
    Supports distributed rate limiting across multiple instances
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        requests_per_minute: int = 20,
        requests_per_hour: int = 500,
        burst_size: Optional[int] = None
    ):
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size or requests_per_minute * 2
    
    def _get_key(self, identifier: str, window: str) -> str:
        """Generate Redis key for rate limit tracking"""
        return f"rate_limit:{identifier}:{window}"
    
    def check_rate_limit(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if request is within rate limits
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            
        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        now = time.time()
        minute_key = self._get_key(identifier, f"minute:{int(now // 60)}")
        hour_key = self._get_key(identifier, f"hour:{int(now // 3600)}")
        
        # Check minute limit
        minute_count = self.redis.incr(minute_key)
        if minute_count == 1:
            self.redis.expire(minute_key, 60)
        
        # Check hour limit
        hour_count = self.redis.incr(hour_key)
        if hour_count == 1:
            self.redis.expire(hour_key, 3600)
        
        # Determine if allowed
        minute_allowed = minute_count <= self.requests_per_minute
        hour_allowed = hour_count <= self.requests_per_hour
        allowed = minute_allowed and hour_allowed
        
        info = {
            "allowed": allowed,
            "minute_count": minute_count,
            "minute_limit": self.requests_per_minute,
            "hour_count": hour_count,
            "hour_limit": self.requests_per_hour,
            "retry_after": 60 if not minute_allowed else 3600 if not hour_allowed else 0
        }
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier}: {info}")
        
        return allowed, info
    
    async def wait_if_needed(self, identifier: str, max_wait: int = 60) -> None:
        """
        Wait if rate limit is exceeded (for background tasks)
        
        Args:
            identifier: Unique identifier
            max_wait: Maximum seconds to wait
        """
        allowed, info = self.check_rate_limit(identifier)
        
        if not allowed:
            wait_time = min(info["retry_after"], max_wait)
            logger.info(f"Rate limit hit for {identifier}, waiting {wait_time}s")
            await asyncio.sleep(wait_time)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter for more accurate rate limiting
    """
    
    def __init__(self, redis_client: redis.Redis, window_seconds: int = 60, max_requests: int = 20):
        self.redis = redis_client
        self.window_seconds = window_seconds
        self.max_requests = max_requests
    
    def check_rate_limit(self, identifier: str) -> tuple[bool, dict]:
        """Check rate limit using sliding window"""
        now = time.time()
        window_start = now - self.window_seconds
        key = f"rate_limit:sliding:{identifier}"
        
        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, self.window_seconds + 1)
        
        results = pipe.execute()
        count = results[1]
        
        allowed = count < self.max_requests
        
        info = {
            "allowed": allowed,
            "count": count,
            "limit": self.max_requests,
            "window_seconds": self.window_seconds,
            "retry_after": self.window_seconds if not allowed else 0
        }
        
        return allowed, info


def rate_limit(
    requests_per_minute: int = 20,
    requests_per_hour: int = 500,
    identifier_func: Optional[Callable] = None
):
    """
    Decorator for rate limiting endpoints
    
    Usage:
        @rate_limit(requests_per_minute=10)
        async def my_endpoint(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get("request")
            
            if not request:
                # No request object, skip rate limiting
                return await func(*args, **kwargs)
            
            # Get identifier (IP or user)
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = request.client.host
            
            # Check rate limit (requires Redis client in app state)
            if hasattr(request.app.state, "rate_limiter"):
                limiter = request.app.state.rate_limiter
                allowed, info = limiter.check_rate_limit(identifier)
                
                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "retry_after": info["retry_after"],
                            "limit": {
                                "minute": f"{info['minute_count']}/{info['minute_limit']}",
                                "hour": f"{info['hour_count']}/{info['hour_limit']}"
                            }
                        },
                        headers={"Retry-After": str(info["retry_after"])}
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class ScraperRateLimiter:
    """
    Rate limiter specifically for web scraping
    Implements delays and backoff strategies
    """
    
    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        backoff_factor: float = 1.5,
        max_backoff: float = 60.0
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.current_delay = min_delay
        self.last_request_time = 0
    
    async def wait(self) -> None:
        """Wait before next request"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.current_delay:
            wait_time = self.current_delay - elapsed
            logger.debug(f"Scraper rate limit: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def success(self) -> None:
        """Called after successful request - reduce delay"""
        self.current_delay = max(self.min_delay, self.current_delay / self.backoff_factor)
    
    def failure(self) -> None:
        """Called after failed request - increase delay"""
        self.current_delay = min(self.max_backoff, self.current_delay * self.backoff_factor)
        logger.warning(f"Scraper backoff: delay increased to {self.current_delay:.2f}s")
    
    def reset(self) -> None:
        """Reset to initial delay"""
        self.current_delay = self.min_delay
