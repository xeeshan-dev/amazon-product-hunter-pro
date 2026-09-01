"""Free proxy rotation system with validation and health scoring.

Manages a pool of free proxies, validates them against Amazon,
and tracks success rates for intelligent rotation.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    raise ImportError("requests library required for proxy manager")


@dataclass
class ProxyInfo:
    """Information about a proxy."""
    host: str
    port: int
    protocol: str = "http"
    country: str = ""
    anonymity: str = ""
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    last_validation: Optional[datetime] = None
    response_time: float = 999.0
    is_working: bool = False

    @property
    def url(self) -> str:
        """Get proxy URL."""
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    @property
    def health_score(self) -> float:
        """Calculate health score (0-100)."""
        if not self.is_working:
            return 0.0

        # Components of health score
        success_score = min(self.success_rate * 100, 50)  # Max 50 points
        speed_score = max(0, 30 - (self.response_time / 100))  # Max 30 points (faster = better)
        reliability_score = min(self.success_count * 2, 20)  # Max 20 points

        return success_score + speed_score + reliability_score

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "anonymity": self.anonymity,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_validation": self.last_validation.isoformat() if self.last_validation else None,
            "response_time": self.response_time,
            "is_working": self.is_working,
            "success_rate": self.success_rate,
            "health_score": self.health_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProxyInfo:
        """Create from dictionary."""
        last_used = data.get("last_used")
        last_validation = data.get("last_validation")

        return cls(
            host=data["host"],
            port=data["port"],
            protocol=data.get("protocol", "http"),
            country=data.get("country", ""),
            anonymity=data.get("anonymity", ""),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            last_used=datetime.fromisoformat(last_used) if last_used else None,
            last_validation=datetime.fromisoformat(last_validation) if last_validation else None,
            response_time=data.get("response_time", 999.0),
            is_working=data.get("is_working", False),
        )


class ProxyManager:
    """Manages free proxy pool with validation and health monitoring."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        min_health_score: float = 30.0,
        max_proxies: int = 100,
        validation_timeout: int = 10,
        revalidation_hours: int = 6,
    ):
        self.storage_path = storage_path or Path("data/proxies/proxy_pool.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.min_health_score = min_health_score
        self.max_proxies = max_proxies
        self.validation_timeout = validation_timeout
        self.revalidation_hours = revalidation_hours

        self.proxy_pool: List[ProxyInfo] = []
        self._load_proxies()

        logger.info(f"ProxyManager initialized with {len(self.proxy_pool)} proxies")

    def get_proxy(self, prefer_country: Optional[str] = None) -> Optional[ProxyInfo]:
        """Get a working proxy with preference for country."""
        # Filter working proxies with good health scores
        candidates = [
            p for p in self.proxy_pool
            if p.is_working and p.health_score >= self.min_health_score
        ]

        if not candidates:
            logger.warning("No working proxies available")
            return None

        # Prefer proxies from specific country if requested
        if prefer_country:
            country_proxies = [p for p in candidates if p.country.upper() == prefer_country.upper()]
            if country_proxies:
                candidates = country_proxies

        # Sort by health score and pick from top candidates randomly
        candidates.sort(key=lambda p: p.health_score, reverse=True)
        top_candidates = candidates[:max(5, len(candidates) // 4)]  # Top 25% or at least 5

        proxy = random.choice(top_candidates)
        proxy.last_used = datetime.now()
        self._save_proxies()

        logger.debug(f"Selected proxy: {proxy.url} (health={proxy.health_score:.1f})")
        return proxy

    def report_success(self, proxy: ProxyInfo, response_time: float):
        """Report successful use of proxy."""
        proxy.success_count += 1
        proxy.response_time = response_time
        self._save_proxies()
        logger.debug(f"Proxy success: {proxy.url} (health={proxy.health_score:.1f})")

    def report_failure(self, proxy: ProxyInfo):
        """Report failed use of proxy."""
        proxy.failure_count += 1

        # Mark as not working if failure rate is too high
        if proxy.failure_count >= 3 and proxy.success_rate < 0.3:
            proxy.is_working = False
            logger.warning(f"Proxy marked as not working: {proxy.url}")

        self._save_proxies()

    def validate_proxy(self, proxy: ProxyInfo, test_url: str = "https://www.amazon.com") -> bool:
        """Validate proxy by attempting to connect to test URL."""
        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies={"http": proxy.url, "https": proxy.url},
                timeout=self.validation_timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"},
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                proxy.is_working = True
                proxy.response_time = response_time
                proxy.last_validation = datetime.now()
                logger.info(f"Proxy validated: {proxy.url} ({response_time:.2f}s)")
                return True

        except Exception as e:
            logger.debug(f"Proxy validation failed for {proxy.url}: {e}")

        proxy.is_working = False
        proxy.last_validation = datetime.now()
        return False

    def validate_all(self, test_url: str = "https://www.amazon.com"):
        """Validate all proxies in the pool."""
        logger.info(f"Validating {len(self.proxy_pool)} proxies...")

        valid_count = 0
        for proxy in self.proxy_pool:
            # Skip recently validated proxies
            if proxy.last_validation:
                age = datetime.now() - proxy.last_validation
                if age < timedelta(hours=self.revalidation_hours) and proxy.is_working:
                    valid_count += 1
                    continue

            if self.validate_proxy(proxy, test_url):
                valid_count += 1

            time.sleep(random.uniform(0.5, 1.5))  # Don't hammer servers

        logger.info(f"Validation complete: {valid_count}/{len(self.proxy_pool)} working")
        self._save_proxies()

    def add_proxy(self, host: str, port: int, protocol: str = "http", **kwargs):
        """Add a new proxy to the pool."""
        # Check if proxy already exists
        for existing in self.proxy_pool:
            if existing.host == host and existing.port == port:
                logger.debug(f"Proxy already exists: {host}:{port}")
                return

        # Don't exceed max proxies
        if len(self.proxy_pool) >= self.max_proxies:
            # Remove worst performing proxy
            self.proxy_pool.sort(key=lambda p: p.health_score)
            removed = self.proxy_pool.pop(0)
            logger.debug(f"Removed worst proxy to make room: {removed.url}")

        proxy = ProxyInfo(host=host, port=port, protocol=protocol, **kwargs)
        self.proxy_pool.append(proxy)
        logger.info(f"Added proxy: {proxy.url}")
        self._save_proxies()

    def add_proxies_from_list(self, proxies: List[str]):
        """Add multiple proxies from a list of proxy strings (host:port)."""
        for proxy_str in proxies:
            try:
                if ":" in proxy_str:
                    host, port = proxy_str.strip().split(":")
                    self.add_proxy(host, int(port))
            except Exception as e:
                logger.warning(f"Failed to parse proxy '{proxy_str}': {e}")

    def get_stats(self) -> Dict:
        """Get proxy pool statistics."""
        working = [p for p in self.proxy_pool if p.is_working]
        healthy = [p for p in working if p.health_score >= self.min_health_score]

        return {
            "total_proxies": len(self.proxy_pool),
            "working_proxies": len(working),
            "healthy_proxies": len(healthy),
            "average_health": sum(p.health_score for p in working) / len(working) if working else 0,
            "best_proxy": max(working, key=lambda p: p.health_score).to_dict() if working else None,
            "proxies": [p.to_dict() for p in self.proxy_pool],
        }

    def cleanup_dead_proxies(self):
        """Remove proxies that are consistently failing."""
        initial_count = len(self.proxy_pool)

        # Remove proxies that have been validated and are not working
        self.proxy_pool = [
            p for p in self.proxy_pool
            if not p.last_validation or p.is_working or p.failure_count < 5
        ]

        removed = initial_count - len(self.proxy_pool)
        if removed > 0:
            logger.info(f"Cleaned up {removed} dead proxies")
            self._save_proxies()

    def _load_proxies(self):
        """Load proxies from storage."""
        if not self.storage_path.exists():
            logger.info("No saved proxies found")
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            self.proxy_pool = [ProxyInfo.from_dict(p) for p in data]
            logger.info(f"Loaded {len(self.proxy_pool)} proxies from storage")

        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
            self.proxy_pool = []

    def _save_proxies(self):
        """Save proxies to storage."""
        try:
            data = [p.to_dict() for p in self.proxy_pool]
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save proxies: {e}")


# Free proxy sources (educational purposes - quality varies greatly)
FREE_PROXY_SOURCES = [
    # These are example sources - actual implementation would fetch from APIs
    # "https://www.proxy-list.download/api/v1/get?type=http",
    # "https://api.proxyscrape.com/v2/?request=get&protocol=http",
]


def fetch_free_proxies() -> List[str]:
    """Fetch proxies from free public sources.

    Note: Free proxies are unreliable and often blocked. This is provided
    for educational purposes. For production, use paid residential proxies.
    """
    proxies = []

    # Example: manual proxy list (you would fetch these from APIs or scrape lists)
    # These are examples only - do not use in production
    logger.warning("Free proxy fetching is for educational purposes only")

    return proxies


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    manager = ProxyManager()

    # Add some example proxies (these won't actually work - just for demonstration)
    manager.add_proxy("proxy1.example.com", 8080)
    manager.add_proxy("proxy2.example.com", 3128)

    # Validate proxies
    manager.validate_all()

    # Get stats
    stats = manager.get_stats()
    print(f"Proxy stats: {stats['working_proxies']}/{stats['total_proxies']} working")
