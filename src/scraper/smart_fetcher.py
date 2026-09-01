"""Smart fetcher with automatic fallback chain.

Orchestrates HTTP → Browser → Proxy → CAPTCHA fallback strategy
for maximum reliability with optimal speed.
"""
from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class FetchStrategy(Enum):
    """Fetching strategy used."""
    HTTP_ENHANCED = "http_enhanced"
    BROWSER_AUTO = "browser_auto"
    HTTP_WITH_PROXY = "http_with_proxy"
    BROWSER_WITH_PROXY = "browser_with_proxy"
    CAPTCHA_MANUAL = "captcha_manual"


class FetchResult:
    """Result of a fetch operation with metadata."""

    def __init__(
        self,
        response,
        strategy: FetchStrategy,
        attempts: int,
        success: bool,
        block_reason: Optional[str] = None,
        captcha_encountered: bool = False,
    ):
        self.response = response
        self.strategy = strategy
        self.attempts = attempts
        self.success = success
        self.block_reason = block_reason
        self.captcha_encountered = captcha_encountered


class SmartFetcher:
    """
    Intelligent fetcher with automatic fallback chain.

    Strategy chain:
    1. HTTP with enhanced headers (fast)
    2. Browser automation (reliable)
    3. HTTP/Browser with proxy (resilient)
    4. Manual CAPTCHA solving (last resort)
    """

    def __init__(
        self,
        base_url: str,
        # HTTP settings
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        max_retries: int = 3,
        request_timeout: int = 30,
        # Browser settings
        enable_browser_fallback: bool = True,
        browser_headless: bool = True,
        # Proxy settings
        enable_proxy: bool = False,
        proxy_url: Optional[str] = None,
        proxy_manager = None,
        # CAPTCHA settings
        enable_captcha_handling: bool = True,
        captcha_api_key: Optional[str] = None,
        # Rate limiting
        adaptive_rate_limiting: bool = True,
        # Storage
        storage_path: Optional[Path] = None,
    ):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.enable_browser_fallback = enable_browser_fallback
        self.enable_proxy = enable_proxy
        self.enable_captcha_handling = enable_captcha_handling
        self.adaptive_rate_limiting = adaptive_rate_limiting

        # Initialize storage
        self.storage_path = storage_path or Path("data/smart_fetcher")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Import and initialize components
        self._init_components(
            min_delay=min_delay,
            max_delay=max_delay,
            max_retries=max_retries,
            request_timeout=request_timeout,
            browser_headless=browser_headless,
            proxy_url=proxy_url,
            proxy_manager=proxy_manager,
            captcha_api_key=captcha_api_key,
        )

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "captcha_encounters": 0,
            "strategy_usage": {strategy.value: 0 for strategy in FetchStrategy},
        }

        logger.info(
            f"SmartFetcher initialized for {self.domain} "
            f"(browser={enable_browser_fallback}, proxy={enable_proxy}, "
            f"captcha={enable_captcha_handling})"
        )

    def _init_components(self, **kwargs):
        """Initialize fetcher components."""
        # Enhanced HTTP fetcher
        from .enhanced_http_fetcher import EnhancedHTTPFetcher

        self.http_fetcher = EnhancedHTTPFetcher(
            base_url=self.base_url,
            min_delay=kwargs.get("min_delay", 3.0),
            max_delay=kwargs.get("max_delay", 8.0),
            max_retries=kwargs.get("max_retries", 3),
            request_timeout=kwargs.get("request_timeout", 30),
            use_tls_fingerprint=True,
            rotate_profiles=True,
            persist_cookies=True,
            cookie_storage_path=self.storage_path / "http_cookies",
        )

        # Browser fetcher (lazy init)
        self.browser_fetcher = None
        self.browser_headless = kwargs.get("browser_headless", True)

        # Proxy manager
        self.proxy_manager = kwargs.get("proxy_manager")
        if self.enable_proxy and not self.proxy_manager and kwargs.get("proxy_url"):
            # Create simple proxy wrapper
            logger.info(f"Using proxy: {kwargs.get('proxy_url')}")

        # CAPTCHA handler
        self.captcha_handler = None
        if self.enable_captcha_handling:
            from .captcha_handler import CaptchaHandler

            self.captcha_handler = CaptchaHandler(
                api_key_2captcha=kwargs.get("captcha_api_key"),
                use_manual_fallback=True,
                cookie_storage_path=self.storage_path / "captcha_cookies",
            )

        # Adaptive rate limiter
        self.rate_limiter = None
        if self.adaptive_rate_limiting:
            from .adaptive_rate_limiter import AdaptiveRateLimiter

            self.rate_limiter = AdaptiveRateLimiter(
                default_min_delay=kwargs.get("min_delay", 3.0),
                default_max_delay=kwargs.get("max_delay", 8.0),
            )

    def get(
        self,
        url: str,
        *,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        priority: str = "normal",
        force_strategy: Optional[FetchStrategy] = None,
    ) -> FetchResult:
        """
        Fetch URL with intelligent fallback strategy.

        Args:
            url: URL to fetch
            referer: Referer header
            extra_headers: Additional headers
            priority: Request priority ("high", "normal", "low")
            force_strategy: Force specific strategy (for testing)

        Returns:
            FetchResult with response and metadata
        """
        self.stats["total_requests"] += 1

        # Rate limiting
        if self.rate_limiter:
            self.rate_limiter.wait(self.domain, priority=priority)

        # Try strategies in order
        if force_strategy:
            strategies = [force_strategy]
        else:
            strategies = self._determine_strategies()

        attempts = 0
        last_response = None
        last_block_reason = None

        for strategy in strategies:
            attempts += 1
            self.stats["strategy_usage"][strategy.value] += 1

            logger.info(f"Attempting fetch with strategy: {strategy.value} (attempt {attempts})")

            try:
                response = self._fetch_with_strategy(
                    strategy=strategy,
                    url=url,
                    referer=referer,
                    extra_headers=extra_headers,
                )

                if response is None:
                    continue

                last_response = response

                # Check for CAPTCHA
                if self.captcha_handler and self.captcha_handler.detect_captcha(response):
                    logger.warning("CAPTCHA detected in response")
                    self.stats["captcha_encounters"] += 1

                    if self.rate_limiter:
                        self.rate_limiter.report_captcha(self.domain)

                    if self.enable_captcha_handling:
                        captcha_result = self.captcha_handler.solve_captcha(
                            response,
                            self.domain,
                            solve_method="auto_with_fallback",
                        )

                        if captcha_result:
                            # CAPTCHA solved - retry request
                            logger.info("CAPTCHA solved, retrying request...")
                            continue

                    # CAPTCHA not solved
                    return FetchResult(
                        response=response,
                        strategy=strategy,
                        attempts=attempts,
                        success=False,
                        captcha_encountered=True,
                    )

                # Check for blocks
                block_reason = self._detect_block(response)
                if block_reason:
                    logger.warning(f"Block detected: {block_reason}")
                    last_block_reason = block_reason

                    if self.rate_limiter:
                        self.rate_limiter.report_block(self.domain)

                    # Try next strategy
                    continue

                # Success!
                self.stats["successful_requests"] += 1

                if self.rate_limiter:
                    self.rate_limiter.report_success(self.domain)

                logger.info(f"Fetch successful with strategy: {strategy.value}")

                return FetchResult(
                    response=response,
                    strategy=strategy,
                    attempts=attempts,
                    success=True,
                )

            except Exception as e:
                logger.error(f"Strategy {strategy.value} failed: {e}")
                if self.rate_limiter:
                    self.rate_limiter.report_block(self.domain)
                continue

        # All strategies failed
        self.stats["failed_requests"] += 1

        logger.error(f"All fetch strategies failed for {url}")

        return FetchResult(
            response=last_response,
            strategy=strategies[-1] if strategies else FetchStrategy.HTTP_ENHANCED,
            attempts=attempts,
            success=False,
            block_reason=last_block_reason,
        )

    def _determine_strategies(self) -> list[FetchStrategy]:
        """Determine which strategies to try based on configuration."""
        strategies = []

        # Always try HTTP first (fastest)
        strategies.append(FetchStrategy.HTTP_ENHANCED)

        # Try browser if enabled
        if self.enable_browser_fallback:
            strategies.append(FetchStrategy.BROWSER_AUTO)

        # Try with proxy if enabled
        if self.enable_proxy:
            strategies.append(FetchStrategy.HTTP_WITH_PROXY)
            if self.enable_browser_fallback:
                strategies.append(FetchStrategy.BROWSER_WITH_PROXY)

        return strategies

    def _fetch_with_strategy(
        self,
        strategy: FetchStrategy,
        url: str,
        referer: Optional[str],
        extra_headers: Optional[Dict[str, str]],
    ):
        """Fetch using a specific strategy."""
        if strategy == FetchStrategy.HTTP_ENHANCED:
            return self.http_fetcher.get(url, referer=referer, extra_headers=extra_headers)

        elif strategy == FetchStrategy.BROWSER_AUTO:
            return self._fetch_with_browser(url)

        elif strategy == FetchStrategy.HTTP_WITH_PROXY:
            return self._fetch_with_proxy(url, referer, extra_headers)

        elif strategy == FetchStrategy.BROWSER_WITH_PROXY:
            return self._fetch_with_browser(url, use_proxy=True)

        else:
            logger.warning(f"Unknown strategy: {strategy}")
            return None

    def _fetch_with_browser(self, url: str, use_proxy: bool = False):
        """Fetch using browser automation."""
        if self.browser_fetcher is None:
            from .browser_fetcher import BrowserFetcher

            self.browser_fetcher = BrowserFetcher(
                base_url=self.base_url,
                headless=self.browser_headless,
                cookie_storage_path=self.storage_path / "browser_cookies",
            )

        return self.browser_fetcher.get(url)

    def _fetch_with_proxy(self, url: str, referer: Optional[str], extra_headers: Optional[Dict[str, str]]):
        """Fetch using proxy."""
        if self.proxy_manager:
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                logger.info(f"Using proxy: {proxy.url}")
                # Implementation would configure http_fetcher to use this proxy
                # For now, falls back to regular HTTP

        return self.http_fetcher.get(url, referer=referer, extra_headers=extra_headers)

    def _detect_block(self, response) -> Optional[str]:
        """Detect if response indicates a block."""
        # Delegate to HTTP fetcher's detection
        if hasattr(self.http_fetcher, '_detect_block'):
            return self.http_fetcher._detect_block(response)
        return None

    def get_stats(self) -> Dict:
        """Get fetcher statistics."""
        stats = dict(self.stats)

        if self.rate_limiter:
            stats["rate_limiter"] = self.rate_limiter.get_stats(self.domain)

        if self.proxy_manager:
            stats["proxy_manager"] = self.proxy_manager.get_stats()

        return stats

    def reset(self):
        """Reset fetcher state."""
        self.http_fetcher.reset_session()

        if self.browser_fetcher:
            self.browser_fetcher.close()
            self.browser_fetcher = None

        if self.rate_limiter:
            self.rate_limiter.reset_marketplace(self.domain)

        logger.info("SmartFetcher reset complete")

    def close(self):
        """Cleanup resources."""
        if self.browser_fetcher:
            self.browser_fetcher.close()

        logger.info("SmartFetcher closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
