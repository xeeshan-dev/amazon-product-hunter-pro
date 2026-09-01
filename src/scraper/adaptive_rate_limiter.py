"""Adaptive rate limiter that learns from blocks and adjusts dynamically.

Tracks block rates per marketplace and adjusts delays intelligently.
Implements cool-down periods and priority-based request handling.
"""
from __future__ import annotations

import logging
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketplaceState:
    """Tracks state for a specific marketplace."""
    domain: str
    current_delay: float
    min_delay: float
    max_delay: float
    consecutive_blocks: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    last_request_time: float = 0.0
    last_block_time: Optional[float] = None
    cool_down_until: Optional[float] = None

    # Track recent performance (last 100 requests)
    recent_successes: deque = None
    recent_failures: deque = None

    def __post_init__(self):
        if self.recent_successes is None:
            self.recent_successes = deque(maxlen=100)
        if self.recent_failures is None:
            self.recent_failures = deque(maxlen=100)

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self.total_requests
        if total == 0:
            return 1.0
        return self.successful_requests / total

    @property
    def recent_success_rate(self) -> float:
        """Calculate recent success rate (last 100 requests)."""
        total = len(self.recent_successes) + len(self.recent_failures)
        if total == 0:
            return 1.0
        return len(self.recent_successes) / total

    @property
    def is_in_cooldown(self) -> bool:
        """Check if marketplace is in cool-down period."""
        if self.cool_down_until is None:
            return False
        return time.time() < self.cool_down_until

    @property
    def time_since_last_block(self) -> Optional[float]:
        """Get seconds since last block."""
        if self.last_block_time is None:
            return None
        return time.time() - self.last_block_time


class AdaptiveRateLimiter:
    """Adaptive rate limiter with per-marketplace intelligence."""

    def __init__(
        self,
        default_min_delay: float = 3.0,
        default_max_delay: float = 8.0,
        aggressive_mode: bool = False,
    ):
        """
        Args:
            default_min_delay: Minimum delay between requests (seconds)
            default_max_delay: Maximum delay between requests (seconds)
            aggressive_mode: If True, use more aggressive delays and cool-downs
        """
        self.default_min_delay = default_min_delay
        self.default_max_delay = default_max_delay
        self.aggressive_mode = aggressive_mode

        # Per-marketplace state
        self.marketplaces: Dict[str, MarketplaceState] = {}

        # Adaptive delay multipliers
        self.delay_increase_factor = 1.5
        self.delay_decrease_factor = 0.9
        self.max_delay_multiplier = 4.0  # Max delay = default_max * 4

        # Cool-down settings
        self.cooldown_threshold = 3  # Consecutive blocks before cool-down
        self.cooldown_base_duration = 60  # Base cool-down time in seconds
        self.cooldown_multiplier = 1.5  # Increases with consecutive blocks

        logger.info(
            f"AdaptiveRateLimiter initialized "
            f"(delays={default_min_delay}-{default_max_delay}s, aggressive={aggressive_mode})"
        )

    def _get_marketplace_state(self, domain: str) -> MarketplaceState:
        """Get or create marketplace state."""
        if domain not in self.marketplaces:
            self.marketplaces[domain] = MarketplaceState(
                domain=domain,
                current_delay=self.default_min_delay,
                min_delay=self.default_min_delay,
                max_delay=self.default_max_delay * self.max_delay_multiplier,
                consecutive_blocks=0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
            )
        return self.marketplaces[domain]

    def wait(self, domain: str, priority: str = "normal"):
        """Wait before making next request.

        Args:
            domain: Marketplace domain (e.g., "amazon.com")
            priority: Request priority ("high", "normal", "low")
        """
        state = self._get_marketplace_state(domain)

        # Check if in cool-down period
        if state.is_in_cooldown:
            remaining = state.cool_down_until - time.time()
            logger.warning(
                f"[{domain}] In cool-down period: waiting {remaining:.1f}s more "
                f"(blocks={state.consecutive_blocks})"
            )
            time.sleep(max(0, remaining))
            state.cool_down_until = None

        # Calculate pacing delay
        if not state.last_request_time:
            state.last_request_time = time.time()
            return

        elapsed = time.time() - state.last_request_time

        # Determine base delay with jitter
        base_delay = state.current_delay
        jitter = random.uniform(-0.5, 1.5)
        target_delay = base_delay + jitter

        # Adjust for priority
        if priority == "high":
            target_delay *= 0.7
        elif priority == "low":
            target_delay *= 1.3

        # Add penalty for recent blocks
        if state.consecutive_blocks > 0:
            block_penalty = min(state.consecutive_blocks * 2, 20)
            target_delay += block_penalty
            logger.debug(
                f"[{domain}] Added {block_penalty:.1f}s penalty "
                f"({state.consecutive_blocks} consecutive blocks)"
            )

        # Wait if needed
        remaining = target_delay - elapsed
        if remaining > 0:
            logger.debug(f"[{domain}] Pacing: waiting {remaining:.1f}s (delay={base_delay:.1f}s)")
            time.sleep(remaining)

        state.last_request_time = time.time()

    def report_success(self, domain: str, response_time: Optional[float] = None):
        """Report successful request."""
        state = self._get_marketplace_state(domain)

        state.total_requests += 1
        state.successful_requests += 1
        state.recent_successes.append(time.time())
        state.consecutive_blocks = 0  # Reset consecutive blocks

        # Gradually decrease delay on sustained success
        if state.recent_success_rate > 0.90 and state.current_delay > state.min_delay:
            old_delay = state.current_delay
            state.current_delay = max(
                state.min_delay,
                state.current_delay * self.delay_decrease_factor
            )
            logger.debug(
                f"[{domain}] Success - decreased delay: {old_delay:.1f}s → {state.current_delay:.1f}s "
                f"(success_rate={state.recent_success_rate:.1%})"
            )

    def report_block(self, domain: str):
        """Report blocked/failed request."""
        state = self._get_marketplace_state(domain)

        state.total_requests += 1
        state.failed_requests += 1
        state.recent_failures.append(time.time())
        state.consecutive_blocks += 1
        state.last_block_time = time.time()

        # Increase delay
        old_delay = state.current_delay
        state.current_delay = min(
            state.max_delay,
            state.current_delay * self.delay_increase_factor
        )

        logger.warning(
            f"[{domain}] Block detected - increased delay: {old_delay:.1f}s → {state.current_delay:.1f}s "
            f"(consecutive_blocks={state.consecutive_blocks}, "
            f"success_rate={state.recent_success_rate:.1%})"
        )

        # Trigger cool-down if too many consecutive blocks
        if state.consecutive_blocks >= self.cooldown_threshold:
            cooldown_duration = self.cooldown_base_duration * (
                self.cooldown_multiplier ** (state.consecutive_blocks - self.cooldown_threshold)
            )
            cooldown_duration = min(cooldown_duration, 300)  # Max 5 minutes
            state.cool_down_until = time.time() + cooldown_duration

            logger.error(
                f"[{domain}] Cool-down triggered: {cooldown_duration:.0f}s "
                f"({state.consecutive_blocks} consecutive blocks)"
            )

    def report_captcha(self, domain: str):
        """Report CAPTCHA encounter (treated as severe block)."""
        state = self._get_marketplace_state(domain)

        logger.warning(f"[{domain}] CAPTCHA detected - applying severe penalties")

        # CAPTCHA is treated as multiple blocks
        for _ in range(3):
            self.report_block(domain)

    def get_stats(self, domain: Optional[str] = None) -> Dict:
        """Get statistics for marketplace(s)."""
        if domain:
            state = self._get_marketplace_state(domain)
            return {
                "domain": state.domain,
                "current_delay": state.current_delay,
                "consecutive_blocks": state.consecutive_blocks,
                "total_requests": state.total_requests,
                "success_rate": state.success_rate,
                "recent_success_rate": state.recent_success_rate,
                "in_cooldown": state.is_in_cooldown,
                "time_since_last_block": state.time_since_last_block,
            }

        # Return stats for all marketplaces
        return {
            domain: self.get_stats(domain)
            for domain in self.marketplaces.keys()
        }

    def reset_marketplace(self, domain: str):
        """Reset state for a specific marketplace."""
        if domain in self.marketplaces:
            del self.marketplaces[domain]
            logger.info(f"[{domain}] State reset")

    def reset_all(self):
        """Reset all marketplace states."""
        self.marketplaces.clear()
        logger.info("All marketplace states reset")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.DEBUG)

    limiter = AdaptiveRateLimiter(default_min_delay=2.0, default_max_delay=5.0)

    # Simulate requests
    print("\nSimulating successful requests...")
    for i in range(5):
        limiter.wait("amazon.com")
        print(f"Request {i+1}")
        limiter.report_success("amazon.com")

    print("\nSimulating blocks...")
    for i in range(4):
        limiter.wait("amazon.com")
        print(f"Request {i+1} - BLOCKED")
        limiter.report_block("amazon.com")

    print("\nStats:")
    stats = limiter.get_stats("amazon.com")
    for key, value in stats.items():
        print(f"  {key}: {value}")
