"""Enhanced HTTP fetcher with realistic browser fingerprinting.

Uses curl_cffi to mimic Chrome's TLS fingerprint and adds realistic headers,
cookie persistence, and browser-like behavior for better anti-blocking.
"""
from __future__ import annotations

import json
import logging
import pickle
import random
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import curl_cffi for TLS fingerprinting
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    curl_requests = requests
    HAS_CURL_CFFI = False
    logger.warning("curl_cffi not installed. TLS fingerprinting disabled. Install with: pip install curl-cffi")


CHROME_VERSIONS = [
    "120.0.6099.109",
    "121.0.6167.85",
    "122.0.6261.94",
    "123.0.6312.58",
    "124.0.6367.60",
]

FIREFOX_VERSIONS = [
    "122.0",
    "123.0",
    "124.0",
    "125.0",
]

PLATFORM_PROFILES = {
    "windows": {
        "platforms": ["Win32"],
        "platform_versions": ["10.0", "11.0"],
        "oscpu": "Windows NT 10.0; Win64; x64",
    },
    "macos": {
        "platforms": ["MacIntel"],
        "platform_versions": ["10.15.7", "11.0", "12.0"],
        "oscpu": "Intel Mac OS X 10_15_7",
    },
    "linux": {
        "platforms": ["Linux x86_64"],
        "platform_versions": [""],
        "oscpu": "Linux x86_64",
    },
}

MARKETPLACE_PREFS = {
    "amazon.co.uk": {
        "language": "en-GB,en;q=0.9",
        "currency": "GBP",
        "locale": "en_GB",
        "country": "GB",
    },
    "amazon.de": {
        "language": "de-DE,de;q=0.9,en;q=0.8",
        "currency": "EUR",
        "locale": "de_DE",
        "country": "DE",
    },
    "amazon.fr": {
        "language": "fr-FR,fr;q=0.9,en;q=0.8",
        "currency": "EUR",
        "locale": "fr_FR",
        "country": "FR",
    },
    "amazon.it": {
        "language": "it-IT,it;q=0.9,en;q=0.8",
        "currency": "EUR",
        "locale": "it_IT",
        "country": "IT",
    },
    "amazon.es": {
        "language": "es-ES,es;q=0.9,en;q=0.8",
        "currency": "EUR",
        "locale": "es_ES",
        "country": "ES",
    },
}
DEFAULT_PREFS = {
    "language": "en-US,en;q=0.9",
    "currency": "USD",
    "locale": "en_US",
    "country": "US",
}

BLOCK_MARKERS = (
    "Enter the characters",
    "api-services-support@amazon",
    "Robot Check",
    "Sorry! Something went wrong",
    "To discuss automated access",
    "automated access to Amazon data",
    "continue shopping",
    "validateCaptcha",
    "CAPTCHA",
    "Type the characters you see",
)


class BrowserProfile:
    """Represents a realistic browser fingerprint."""

    def __init__(self, browser: str = "chrome", platform: str = "windows"):
        self.browser = browser.lower()
        self.platform = platform.lower()
        self.version = self._generate_version()
        self.platform_profile = PLATFORM_PROFILES.get(self.platform, PLATFORM_PROFILES["windows"])
        self.user_agent = self._generate_user_agent()
        self.sec_ch_ua = self._generate_sec_ch_ua()
        self.viewport = self._generate_viewport()
        self.screen_resolution = self._generate_screen_resolution()

    def _generate_version(self) -> str:
        if self.browser == "firefox":
            return random.choice(FIREFOX_VERSIONS)
        return random.choice(CHROME_VERSIONS)

    def _generate_user_agent(self) -> str:
        oscpu = self.platform_profile["oscpu"]
        if self.browser == "firefox":
            return f"Mozilla/5.0 ({oscpu}; rv:{self.version}) Gecko/20100101 Firefox/{self.version}"
        elif self.browser == "chrome":
            webkit_version = "537.36"
            return (
                f"Mozilla/5.0 ({oscpu}) AppleWebKit/{webkit_version} "
                f"(KHTML, like Gecko) Chrome/{self.version} Safari/{webkit_version}"
            )
        return f"Mozilla/5.0 ({oscpu}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.version} Safari/537.36"

    def _generate_sec_ch_ua(self) -> str:
        if self.browser != "chrome":
            return ""
        major_version = self.version.split(".")[0]
        return (
            f'"Chromium";v="{major_version}", '
            f'"Google Chrome";v="{major_version}", '
            f'"Not-A.Brand";v="99"'
        )

    def _generate_viewport(self) -> tuple:
        common_viewports = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1280, 720),
        ]
        return random.choice(common_viewports)

    def _generate_screen_resolution(self) -> tuple:
        viewport_w, viewport_h = self.viewport
        return (viewport_w, viewport_h)


class CookieJar:
    """Persistent cookie storage across sessions."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/cookies")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.cookies: Dict[str, Dict] = {}

    def load(self, domain: str) -> Dict:
        """Load cookies for a specific domain."""
        cookie_file = self.storage_path / f"{domain.replace('.', '_')}.pkl"
        if cookie_file.exists():
            try:
                with open(cookie_file, "rb") as f:
                    self.cookies[domain] = pickle.load(f)
                logger.debug(f"Loaded {len(self.cookies[domain])} cookies for {domain}")
                return self.cookies[domain]
            except Exception as e:
                logger.warning(f"Failed to load cookies for {domain}: {e}")
        return {}

    def save(self, domain: str, cookies: Dict):
        """Save cookies for a specific domain."""
        cookie_file = self.storage_path / f"{domain.replace('.', '_')}.pkl"
        try:
            self.cookies[domain] = cookies
            with open(cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            logger.debug(f"Saved {len(cookies)} cookies for {domain}")
        except Exception as e:
            logger.warning(f"Failed to save cookies for {domain}: {e}")

    def get(self, domain: str) -> Dict:
        """Get cookies for a domain (load if not in memory)."""
        if domain not in self.cookies:
            return self.load(domain)
        return self.cookies.get(domain, {})

    def clear(self, domain: str):
        """Clear cookies for a specific domain."""
        cookie_file = self.storage_path / f"{domain.replace('.', '_')}.pkl"
        if cookie_file.exists():
            cookie_file.unlink()
        self.cookies.pop(domain, None)
        logger.info(f"Cleared cookies for {domain}")


class EnhancedHTTPFetcher:
    """Enhanced HTTP fetcher with browser fingerprinting and cookie persistence."""

    def __init__(
        self,
        base_url: str,
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        max_retries: int = 3,
        request_timeout: int = 30,
        use_tls_fingerprint: bool = True,
        rotate_profiles: bool = True,
        persist_cookies: bool = True,
        cookie_storage_path: Optional[Path] = None,
    ):
        self.base_url = base_url
        self.min_delay = max(1.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        self.max_retries = max(1, max_retries)
        self.request_timeout = min(max(5, request_timeout), 60)
        self.use_tls_fingerprint = use_tls_fingerprint and HAS_CURL_CFFI
        self.rotate_profiles = rotate_profiles
        self.persist_cookies = persist_cookies

        self.domain = urlparse(base_url).netloc
        self.profile = BrowserProfile(browser="chrome", platform="windows")
        self.cookie_jar = CookieJar(cookie_storage_path) if persist_cookies else None
        self.session = self._create_session()
        self._last_request_time = 0.0
        self._consecutive_blocks = 0

        if not HAS_CURL_CFFI and use_tls_fingerprint:
            logger.warning(
                "TLS fingerprinting requested but curl_cffi not available. "
                "Install with: pip install curl-cffi"
            )

    def _create_session(self):
        """Create a new session with the appropriate library."""
        if self.use_tls_fingerprint:
            # Use curl_cffi for TLS fingerprinting
            session = curl_requests.Session()
            logger.info("Created session with curl_cffi (TLS fingerprint enabled)")
        else:
            # Fallback to standard requests
            import requests
            session = requests.Session()
            logger.info("Created session with standard requests")

        # Load cookies if available
        if self.cookie_jar:
            cookies = self.cookie_jar.get(self.domain)
            if cookies:
                session.cookies.update(cookies)

        return session

    def get(
        self,
        url: str,
        *,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        allow_small_response: bool = False,
    ):
        """Fetch URL with enhanced fingerprinting and retries."""
        last_response = None

        for attempt in range(1, self.max_retries + 1):
            self._pace()

            try:
                headers = self.build_headers(url, referer=referer, extra_headers=extra_headers)

                # Use impersonate parameter if available (curl_cffi feature)
                if self.use_tls_fingerprint:
                    response = self.session.get(
                        url,
                        headers=headers,
                        timeout=self.request_timeout,
                        impersonate="chrome120",  # Mimic Chrome 120 TLS fingerprint
                        allow_redirects=True,
                    )
                else:
                    response = self.session.get(
                        url,
                        headers=headers,
                        timeout=self.request_timeout,
                        allow_redirects=True,
                    )

                last_response = response

                # Save cookies after successful request
                if self.cookie_jar and response.ok:
                    self.cookie_jar.save(self.domain, dict(self.session.cookies))

                # Check for blocks
                block_reason = self._detect_block(response, allow_small_response)
                if response.ok and block_reason is None:
                    self._consecutive_blocks = 0
                    return response

                logger.warning(
                    f"Block detected ({block_reason}) for {url} "
                    f"(attempt {attempt}/{self.max_retries}, status={response.status_code}, "
                    f"bytes={len(response.content or b'')})"
                )
                self._consecutive_blocks += 1

            except Exception as exc:
                logger.warning(f"Request failed for {url} (attempt {attempt}/{self.max_retries}): {exc}")

            # Rotate profile and reset session before retry
            if attempt < self.max_retries:
                self._rotate_profile()
                self._backoff(attempt)

        return last_response

    def build_headers(
        self,
        url: str,
        *,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Build realistic browser headers with fingerprinting."""
        prefs = self._get_marketplace_prefs(url)
        viewport_w, viewport_h = self.profile.viewport

        headers = {
            "User-Agent": self.profile.user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": prefs["language"],
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin" if referer else "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
        }

        # Add Chrome-specific headers
        if self.profile.browser == "chrome" and self.profile.sec_ch_ua:
            platform = random.choice(self.profile.platform_profile["platforms"])
            headers.update(
                {
                    "sec-ch-ua": self.profile.sec_ch_ua,
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": f'"{platform}"',
                    "sec-ch-ua-platform-version": f'"{random.choice(self.profile.platform_profile["platform_versions"])}"',
                }
            )

        # Add realistic viewport headers
        headers["Viewport-Width"] = str(viewport_w)

        # Add referer if provided
        if referer:
            headers["Referer"] = referer

        # Add marketplace-specific cookies
        cookie_parts = [
            f"i18n-prefs={prefs['currency']}",
            f"lc-main={prefs['locale']}",
            f"sp-cdn={prefs['country']}",
        ]
        headers["Cookie"] = "; ".join(cookie_parts)

        # Merge extra headers
        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _get_marketplace_prefs(self, url: str) -> Dict[str, str]:
        """Get marketplace-specific preferences."""
        host = urlparse(url).netloc
        for marker, prefs in MARKETPLACE_PREFS.items():
            if marker in host:
                return prefs
        return DEFAULT_PREFS

    def _detect_block(self, response, allow_small_response: bool = False) -> Optional[str]:
        """Detect if response indicates a block."""
        # Check status codes
        if response.status_code in (202, 403, 429, 503, 504):
            return f"status_{response.status_code}"

        if not response.ok:
            return f"status_{response.status_code}"

        # Check for block markers in content
        try:
            text = response.text[:20000].lower()
        except Exception:
            return "text_decode_error"

        for marker in BLOCK_MARKERS:
            if marker.lower() in text:
                return "block_marker"

        # Check response size
        if not allow_small_response and len(response.content or b"") < 25000:
            return "small_response"

        return None

    def _pace(self):
        """Intelligent pacing between requests."""
        if not self._last_request_time:
            self._last_request_time = time.time()
            return

        elapsed = time.time() - self._last_request_time

        # Calculate target delay with jitter
        base_delay = random.uniform(self.min_delay, self.max_delay)

        # Increase delay if we're experiencing blocks
        if self._consecutive_blocks > 0:
            penalty = min(self._consecutive_blocks * random.uniform(2.0, 4.0), 30.0)
            base_delay += penalty
            logger.debug(f"Increased delay to {base_delay:.1f}s due to {self._consecutive_blocks} consecutive blocks")

        # Wait if needed
        remaining = base_delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

        self._last_request_time = time.time()

    def _backoff(self, attempt: int):
        """Exponential backoff with jitter."""
        backoff_time = min(2 ** attempt, 20) + random.uniform(1.0, 3.0)
        logger.debug(f"Backing off for {backoff_time:.1f}s before retry")
        time.sleep(backoff_time)

    def _rotate_profile(self):
        """Rotate browser profile for next request."""
        if not self.rotate_profiles:
            return

        # Randomly choose browser and platform
        browser = random.choice(["chrome", "chrome", "chrome", "firefox"])  # 75% Chrome
        platform = random.choice(["windows", "windows", "macos", "linux"])  # 50% Windows

        self.profile = BrowserProfile(browser=browser, platform=platform)
        logger.debug(f"Rotated to {browser} on {platform}: {self.profile.user_agent[:50]}...")

        # Create new session with new profile
        self.session = self._create_session()

    def reset_session(self):
        """Reset session completely."""
        self._rotate_profile()
        self._consecutive_blocks = 0
        logger.info("Session reset complete")

    def clear_cookies(self):
        """Clear all stored cookies."""
        if self.cookie_jar:
            self.cookie_jar.clear(self.domain)
            self.session.cookies.clear()
            logger.info("Cookies cleared")
