"""Browser automation fetcher using Playwright for realistic scraping.

Falls back to browser automation when HTTP requests are blocked.
Uses stealth mode to bypass bot detection.
"""
from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Playwright not installed. Browser automation disabled. Install with: pip install playwright")


# Try to import playwright-stealth
try:
    from playwright_stealth import stealth_sync
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    logger.info("playwright-stealth not installed. Stealth mode disabled. Install with: pip install playwright-stealth")


MARKETPLACE_PREFS = {
    "amazon.co.uk": {"language": "en-GB", "timezone": "Europe/London"},
    "amazon.de": {"language": "de-DE", "timezone": "Europe/Berlin"},
    "amazon.fr": {"language": "fr-FR", "timezone": "Europe/Paris"},
    "amazon.it": {"language": "it-IT", "timezone": "Europe/Rome"},
    "amazon.es": {"language": "es-ES", "timezone": "Europe/Madrid"},
}
DEFAULT_PREFS = {"language": "en-US", "timezone": "America/New_York"}


class MockResponse:
    """Mock response object compatible with requests.Response."""

    def __init__(self, content: bytes, status_code: int, url: str, headers: dict):
        self.content = content
        self.status_code = status_code
        self.url = url
        self.headers = headers
        self.ok = 200 <= status_code < 400
        self._text = None

    @property
    def text(self) -> str:
        if self._text is None:
            try:
                self._text = self.content.decode('utf-8')
            except UnicodeDecodeError:
                self._text = self.content.decode('latin-1')
        return self._text


class BrowserFetcher:
    """Browser automation fetcher using Playwright with stealth mode."""

    def __init__(
        self,
        base_url: str,
        headless: bool = True,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        page_timeout: int = 30000,
        save_cookies: bool = True,
        cookie_storage_path: Optional[Path] = None,
    ):
        if not HAS_PLAYWRIGHT:
            raise ImportError(
                "Playwright is required for browser automation. "
                "Install with: pip install playwright && playwright install chromium"
            )

        self.base_url = base_url
        self.headless = headless
        self.min_delay = max(1.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        self.page_timeout = max(5000, page_timeout)
        self.save_cookies = save_cookies

        self.domain = urlparse(base_url).netloc
        self.cookie_storage_path = cookie_storage_path or Path("data/browser_cookies")
        self.cookie_storage_path.mkdir(parents=True, exist_ok=True)

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._last_request_time = 0.0

        logger.info(f"BrowserFetcher initialized for {self.domain} (headless={headless})")

    def _init_browser(self):
        """Initialize Playwright browser."""
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            logger.debug("Playwright started")

        if self.browser is None:
            prefs = self._get_marketplace_prefs(self.base_url)

            # Launch browser with stealth settings
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ],
            )
            logger.debug("Browser launched")

            # Load cookies if available
            cookie_file = self.cookie_storage_path / f"{self.domain.replace('.', '_')}.json"
            storage_state = None
            if cookie_file.exists() and self.save_cookies:
                try:
                    storage_state = str(cookie_file)
                    logger.debug(f"Loading cookies from {cookie_file}")
                except Exception as e:
                    logger.warning(f"Failed to load cookies: {e}")

            # Create context with realistic settings
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale=prefs["language"],
                timezone_id=prefs["timezone"],
                geolocation=None,
                permissions=[],
                storage_state=storage_state,
                extra_http_headers={
                    "Accept-Language": f"{prefs['language']},en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )

            # Create page
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.page_timeout)

            # Apply stealth if available
            if HAS_STEALTH:
                stealth_sync(self.page)
                logger.debug("Stealth mode applied")

            logger.info("Browser context and page created")

    def get(
        self,
        url: str,
        *,
        wait_for_selector: Optional[str] = None,
        wait_time: Optional[float] = None,
        extract_cookies: bool = True,
    ) -> MockResponse:
        """Fetch URL using browser automation."""
        self._init_browser()
        self._pace()

        try:
            logger.info(f"Browser fetching: {url}")

            # Navigate to page
            response = self.page.goto(url, wait_until="domcontentloaded", timeout=self.page_timeout)

            # Optional: wait for specific selector
            if wait_for_selector:
                try:
                    self.page.wait_for_selector(wait_for_selector, timeout=self.page_timeout)
                    logger.debug(f"Found selector: {wait_for_selector}")
                except PlaywrightTimeout:
                    logger.warning(f"Selector not found: {wait_for_selector}")

            # Optional: additional wait time (simulate human reading)
            if wait_time:
                time.sleep(wait_time)
            else:
                # Random human-like delay
                time.sleep(random.uniform(1.0, 3.0))

            # Scroll page randomly (human behavior)
            self._random_scroll()

            # Get page content
            content = self.page.content()
            status = response.status if response else 200
            headers = dict(response.headers) if response else {}

            # Save cookies
            if extract_cookies and self.save_cookies:
                self._save_cookies()

            logger.info(f"Browser fetch successful: {len(content)} bytes")

            return MockResponse(
                content=content.encode('utf-8'),
                status_code=status,
                url=url,
                headers=headers,
            )

        except Exception as e:
            logger.error(f"Browser fetch failed for {url}: {e}")
            raise

    def get_cookies(self) -> Dict:
        """Extract cookies from current browser context."""
        if not self.context:
            return {}

        cookies = self.context.cookies()
        return {cookie['name']: cookie['value'] for cookie in cookies}

    def _save_cookies(self):
        """Save browser cookies to file."""
        if not self.context or not self.save_cookies:
            return

        cookie_file = self.cookie_storage_path / f"{self.domain.replace('.', '_')}.json"
        try:
            self.context.storage_state(path=str(cookie_file))
            logger.debug(f"Saved browser cookies to {cookie_file}")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")

    def _random_scroll(self):
        """Simulate human-like scrolling behavior."""
        try:
            # Scroll down in random steps
            scroll_height = self.page.evaluate("document.body.scrollHeight")
            current_position = 0
            target_position = random.randint(int(scroll_height * 0.2), int(scroll_height * 0.6))

            while current_position < target_position:
                step = random.randint(100, 300)
                current_position += step
                self.page.evaluate(f"window.scrollTo(0, {current_position})")
                time.sleep(random.uniform(0.1, 0.3))

            # Scroll back up a bit
            self.page.evaluate(f"window.scrollTo(0, {current_position - random.randint(100, 200)})")
            time.sleep(random.uniform(0.2, 0.5))

        except Exception as e:
            logger.debug(f"Scroll simulation failed: {e}")

    def _pace(self):
        """Pacing between browser requests."""
        if not self._last_request_time:
            self._last_request_time = time.time()
            return

        elapsed = time.time() - self._last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        remaining = delay - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_time = time.time()

    def _get_marketplace_prefs(self, url: str) -> Dict[str, str]:
        """Get marketplace-specific preferences."""
        host = urlparse(url).netloc
        for marker, prefs in MARKETPLACE_PREFS.items():
            if marker in host:
                return prefs
        return DEFAULT_PREFS

    def reset_session(self):
        """Reset browser session (close and reopen)."""
        self.close()
        self._init_browser()
        logger.info("Browser session reset")

    def close(self):
        """Close browser and cleanup."""
        if self.page:
            self.page.close()
            self.page = None

        if self.context:
            self.context.close()
            self.context = None

        if self.browser:
            self.browser.close()
            self.browser = None

        if self.playwright:
            self.playwright.stop()
            self.playwright = None

        logger.info("Browser closed")

    def __enter__(self):
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
