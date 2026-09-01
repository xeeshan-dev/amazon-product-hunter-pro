"""Request pacing and block detection for Amazon HTML collection.

This module intentionally avoids public proxy lists, Tor automation, or CAPTCHA
workarounds. Those approaches are unreliable for this app and can fail in ways
that are hard to diagnose. The fetcher focuses on conservative browser-like
headers, session rotation, jittered pacing, and clear block diagnostics.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, Dict, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


CHROME_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]


MARKETPLACE_PREFS = {
    "amazon.co.uk": {"language": "en-GB,en;q=0.9", "currency": "GBP", "locale": "en_GB"},
    "amazon.de": {"language": "de-DE,de;q=0.9", "currency": "EUR", "locale": "de_DE"},
}
DEFAULT_PREFS = {"language": "en-US,en;q=0.9", "currency": "USD", "locale": "en_US"}


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
)


class AntiBlockFetcher:
    """Small wrapper around requests.Session for Amazon HTML fetching."""

    def __init__(
        self,
        base_url: str,
        min_delay: float,
        max_delay: float,
        max_retries: int,
        request_timeout: int,
        *,
        user_agent_rotation: bool = True,
        use_proxy: bool = False,
        proxy_url: Optional[str] = None,
        min_response_bytes: int = 25_000,
        session_factory: Callable[[], requests.Session] = requests.Session,
    ):
        self.base_url = base_url
        self.min_delay = max(0.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        self.max_retries = max(1, max_retries)
        self.request_timeout = min(max(1, request_timeout), 30)
        self.user_agent_rotation = user_agent_rotation
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.min_response_bytes = max(0, min_response_bytes)
        self._session_factory = session_factory
        self._last_request_time = 0.0
        self._consecutive_blocks = 0
        self._ua_string: Optional[str] = None
        self.session = self._new_session()

    def get(
        self,
        url: str,
        *,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        allow_small_response: bool = False,
        timeout: Optional[int] = None,
    ) -> Optional[requests.Response]:
        """Fetch a URL with paced retries and session rotation."""
        last_response: Optional[requests.Response] = None

        for attempt in range(1, self.max_retries + 1):
            self._pace()
            try:
                response = self.session.get(
                    url,
                    headers=self.build_headers(url, referer=referer, extra_headers=extra_headers),
                    timeout=timeout or self.request_timeout,
                )
                last_response = response
                reason = self.block_reason(response, allow_small_response=allow_small_response)
                if response.ok and reason is None:
                    self._consecutive_blocks = 0
                    return response

                logger.warning(
                    "Amazon block/challenge suspected (%s, status=%s, bytes=%s, reason=%s) "
                    "for %s - attempt %s/%s",
                    self.base_url,
                    response.status_code,
                    len(response.content or b""),
                    reason or "http_error",
                    url,
                    attempt,
                    self.max_retries,
                )
                self._consecutive_blocks += 1
            except Exception as exc:
                logger.warning("Request failed for %s (attempt %s/%s): %s", url, attempt, self.max_retries, exc)

            self.reset_session()
            if attempt < self.max_retries:
                self._backoff(attempt)

        return last_response

    def build_headers(
        self,
        url: Optional[str] = None,
        *,
        referer: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        prefs = self._marketplace_prefs(url or self.base_url)
        ua = self._ua_string or self.rotate_user_agent()
        headers = {
            "User-Agent": ua,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": prefs["language"],
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin" if referer else "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Cookie": f"i18n-prefs={prefs['currency']}; lc-main={prefs['locale']}",
        }
        if referer:
            headers["Referer"] = referer
        if "Chrome" in ua:
            headers.update(
                {
                    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                }
            )
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def reset_session(self) -> None:
        self.session = self._new_session()
        if self.user_agent_rotation:
            self.rotate_user_agent()

    def rotate_user_agent(self) -> str:
        self._ua_string = random.choice(CHROME_UAS)
        return self._ua_string

    def block_reason(self, response, *, allow_small_response: bool = False) -> Optional[str]:
        return self.response_block_reason(
            response,
            allow_small_response=allow_small_response,
            min_response_bytes=self.min_response_bytes,
        )

    @classmethod
    def response_block_reason(
        cls,
        response,
        *,
        allow_small_response: bool = False,
        min_response_bytes: int = 25_000,
    ) -> Optional[str]:
        if response.status_code in (202, 403, 429, 503):
            return f"status_{response.status_code}"
        if not getattr(response, "ok", response.status_code < 400):
            return f"status_{response.status_code}"
        try:
            text = response.text[:20_000]
        except Exception:
            text = ""
        lowered = text.lower()
        for marker in BLOCK_MARKERS:
            if marker.lower() in lowered:
                return "block_marker"
        if not allow_small_response and len(response.content or b"") < min_response_bytes:
            return "small_response"
        return None

    def is_blocked(self, response, *, allow_small_response: bool = False) -> bool:
        return self.block_reason(response, allow_small_response=allow_small_response) is not None

    def _new_session(self) -> requests.Session:
        session = self._session_factory()
        if self.use_proxy and self.proxy_url:
            session.proxies = {"http": self.proxy_url, "https": self.proxy_url}
        return session

    def _pace(self) -> None:
        if not self._last_request_time:
            self._last_request_time = time.time()
            return
        elapsed = time.time() - self._last_request_time
        target = random.uniform(self.min_delay, self.max_delay)
        if self._consecutive_blocks:
            target += min(self._consecutive_blocks * random.uniform(2.0, 5.0), 20.0)
        remaining = target - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_time = time.time()

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(min(2 ** attempt, 12) + random.uniform(0.5, 2.0))

    @staticmethod
    def _marketplace_prefs(url: str) -> Dict[str, str]:
        host = urlparse(url).netloc
        for marker, prefs in MARKETPLACE_PREFS.items():
            if marker in host:
                return prefs
        return DEFAULT_PREFS
