"""
Mock Redis client for development without Redis server
"""
import time
from typing import Any, Optional


class MockRedis:
    """In-memory mock Redis for development"""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
    
    def ping(self):
        """Mock ping"""
        return True
    
    def get(self, key: str) -> Optional[bytes]:
        """Mock get"""
        # Check expiry
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return None
        
        return self._data.get(key)
    
    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> bool:
        """Mock set"""
        if nx and key in self._data:
            return False
        
        self._data[key] = value
        
        if ex:
            self._expiry[key] = time.time() + ex
        
        return True
    
    def delete(self, *keys) -> int:
        """Mock delete"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._expiry:
                    del self._expiry[key]
                count += 1
        return count
    
    def exists(self, key: str) -> bool:
        """Mock exists"""
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return False
        return key in self._data
    
    def ttl(self, key: str) -> int:
        """Mock TTL"""
        if key not in self._data:
            return -2
        if key not in self._expiry:
            return -1
        remaining = int(self._expiry[key] - time.time())
        return max(0, remaining)
    
    def incr(self, key: str) -> int:
        """Mock increment"""
        current = int(self._data.get(key, 0))
        current += 1
        self._data[key] = str(current)
        return current
    
    def incrby(self, key: str, amount: int) -> int:
        """Mock increment by amount"""
        current = int(self._data.get(key, 0))
        current += amount
        self._data[key] = str(current)
        return current
    
    def expire(self, key: str, seconds: int) -> bool:
        """Mock expire"""
        if key in self._data:
            self._expiry[key] = time.time() + seconds
            return True
        return False
    
    def keys(self, pattern: str) -> list:
        """Mock keys"""
        # Simple pattern matching
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return [k for k in self._data.keys() if k.startswith(prefix)]
        return [k for k in self._data.keys() if k == pattern]
    
    def info(self) -> dict:
        """Mock info"""
        return {
            'connected_clients': 1,
            'used_memory_human': f'{len(str(self._data))} bytes',
            'total_commands_processed': len(self._data)
        }
    
    def close(self):
        """Mock close"""
        pass
    
    # Sorted set operations for sliding window rate limiter
    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """Mock zremrangebyscore"""
        if key not in self._data:
            self._data[key] = []
        
        original_len = len(self._data[key])
        self._data[key] = [
            item for item in self._data[key]
            if not (min_score <= item[1] <= max_score)
        ]
        return original_len - len(self._data[key])
    
    def zcard(self, key: str) -> int:
        """Mock zcard"""
        if key not in self._data:
            return 0
        return len(self._data[key])
    
    def zadd(self, key: str, mapping: dict) -> int:
        """Mock zadd"""
        if key not in self._data:
            self._data[key] = []
        
        for member, score in mapping.items():
            self._data[key].append((member, score))
        
        return len(mapping)
    
    def pipeline(self):
        """Mock pipeline"""
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.commands = []
    
    def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        self.commands.append(('zremrangebyscore', key, min_score, max_score))
        return self
    
    def zcard(self, key: str):
        self.commands.append(('zcard', key))
        return self
    
    def zadd(self, key: str, mapping: dict):
        self.commands.append(('zadd', key, mapping))
        return self
    
    def expire(self, key: str, seconds: int):
        self.commands.append(('expire', key, seconds))
        return self
    
    def execute(self):
        """Execute all commands"""
        results = []
        for cmd in self.commands:
            if cmd[0] == 'zremrangebyscore':
                results.append(self.redis.zremrangebyscore(cmd[1], cmd[2], cmd[3]))
            elif cmd[0] == 'zcard':
                results.append(self.redis.zcard(cmd[1]))
            elif cmd[0] == 'zadd':
                results.append(self.redis.zadd(cmd[1], cmd[2]))
            elif cmd[0] == 'expire':
                results.append(self.redis.expire(cmd[1], cmd[2]))
        self.commands = []
        return results


def from_url(url: str, **kwargs):
    """Mock redis.from_url"""
    return MockRedis()
