"""CAPTCHA detection and solving using free services and manual fallback.

Supports:
- 2captcha API (free tier: 1000 solves)
- Manual solving via browser UI
- Cookie extraction after solve
"""
from __future__ import annotations

import logging
import re
import time
import webbrowser
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import 2captcha
try:
    from twocaptcha import TwoCaptcha
    HAS_2CAPTCHA = True
except ImportError:
    HAS_2CAPTCHA = False
    logger.info("2captcha not installed. Auto-solving disabled. Install with: pip install 2captcha-python")


CAPTCHA_INDICATORS = [
    "enter the characters",
    "type the characters",
    "validatecaptcha",
    "captcha",
    "robot check",
    "sorry! something went wrong",
    "to discuss automated access",
]


class CaptchaDetector:
    """Detects CAPTCHA challenges in responses."""

    @staticmethod
    def has_captcha(response_text: str) -> bool:
        """Check if response contains CAPTCHA challenge."""
        text_lower = response_text.lower()

        for indicator in CAPTCHA_INDICATORS:
            if indicator in text_lower:
                logger.debug(f"CAPTCHA detected: indicator '{indicator}' found")
                return True

        return False

    @staticmethod
    def extract_captcha_image_url(response_text: str) -> Optional[str]:
        """Extract CAPTCHA image URL from response."""
        # Look for image URL in various formats
        patterns = [
            r'<img[^>]*src="([^"]*captcha[^"]*)"',
            r'<img[^>]*src="([^"]*opfcaptcha[^"]*)"',
            r'src="([^"]*\/captcha\/[^"]*)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                url = match.group(1)
                logger.debug(f"Found CAPTCHA image URL: {url}")
                return url

        return None

    @staticmethod
    def extract_captcha_form_data(response_text: str) -> Dict[str, str]:
        """Extract form data needed for CAPTCHA submission."""
        data = {}

        # Extract hidden form fields
        hidden_fields = re.findall(
            r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"',
            response_text,
            re.IGNORECASE
        )

        for name, value in hidden_fields:
            data[name] = value

        logger.debug(f"Extracted {len(data)} hidden form fields")
        return data


class CaptchaHandler:
    """Handles CAPTCHA solving using multiple strategies."""

    def __init__(
        self,
        api_key_2captcha: Optional[str] = None,
        use_manual_fallback: bool = True,
        cookie_storage_path: Optional[Path] = None,
    ):
        self.api_key_2captcha = api_key_2captcha
        self.use_manual_fallback = use_manual_fallback
        self.cookie_storage_path = cookie_storage_path or Path("data/captcha_cookies")
        self.cookie_storage_path.mkdir(parents=True, exist_ok=True)

        self.twocaptcha_client = None
        if api_key_2captcha and HAS_2CAPTCHA:
            self.twocaptcha_client = TwoCaptcha(api_key_2captcha)
            logger.info("2captcha client initialized")
        elif api_key_2captcha and not HAS_2CAPTCHA:
            logger.warning("2captcha API key provided but library not installed")

        self.detector = CaptchaDetector()

    def detect_captcha(self, response) -> bool:
        """Detect if response contains CAPTCHA."""
        try:
            text = response.text if hasattr(response, 'text') else response.content.decode('utf-8')
            return self.detector.has_captcha(text)
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {e}")
            return False

    def solve_captcha(
        self,
        response,
        domain: str,
        solve_method: str = "auto",
    ) -> Optional[Dict[str, str]]:
        """
        Solve CAPTCHA challenge.

        Args:
            response: Response object containing CAPTCHA
            domain: Domain being accessed
            solve_method: "auto" (try 2captcha), "manual", or "auto_with_fallback"

        Returns:
            Dictionary with solved CAPTCHA data or None if failed
        """
        logger.info(f"Attempting to solve CAPTCHA for {domain} (method={solve_method})")

        try:
            text = response.text if hasattr(response, 'text') else response.content.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to get response text: {e}")
            return None

        # Extract CAPTCHA details
        image_url = self.detector.extract_captcha_image_url(text)
        form_data = self.detector.extract_captcha_form_data(text)

        # Try automated solving first
        if solve_method in ("auto", "auto_with_fallback") and self.twocaptcha_client:
            result = self._solve_with_2captcha(image_url, form_data)
            if result:
                return result
            elif solve_method == "auto":
                logger.error("Auto-solving failed and fallback disabled")
                return None

        # Fall back to manual solving
        if solve_method in ("manual", "auto_with_fallback") and self.use_manual_fallback:
            return self._solve_manually(response.url if hasattr(response, 'url') else "", domain)

        logger.error("No CAPTCHA solving method available")
        return None

    def _solve_with_2captcha(
        self,
        image_url: Optional[str],
        form_data: Dict[str, str],
    ) -> Optional[Dict[str, str]]:
        """Solve CAPTCHA using 2captcha service."""
        if not self.twocaptcha_client:
            return None

        try:
            logger.info("Attempting to solve CAPTCHA with 2captcha...")

            # For image CAPTCHA
            if image_url:
                result = self.twocaptcha_client.normal(image_url)
                logger.info(f"2captcha solved CAPTCHA: {result['code']}")

                # Return solution with form data
                return {
                    "captcha_solution": result["code"],
                    "form_data": form_data,
                }

            logger.warning("No image URL found for 2captcha")
            return None

        except Exception as e:
            logger.error(f"2captcha solving failed: {e}")
            return None

    def _solve_manually(self, captcha_url: str, domain: str) -> Optional[Dict[str, str]]:
        """Manual CAPTCHA solving - opens browser for user to solve."""
        logger.info("Opening browser for manual CAPTCHA solving...")

        try:
            # Open CAPTCHA page in browser
            webbrowser.open(captcha_url)

            print("\n" + "=" * 60)
            print("CAPTCHA DETECTED - MANUAL SOLVING REQUIRED")
            print("=" * 60)
            print(f"Domain: {domain}")
            print(f"URL: {captcha_url}")
            print("\nA browser window has been opened.")
            print("Please solve the CAPTCHA in the browser.")
            print("\nAfter solving:")
            print("1. Wait for the page to load successfully")
            print("2. Return here and press ENTER")
            print("=" * 60)

            # Wait for user to solve
            input("\nPress ENTER after solving CAPTCHA... ")

            logger.info("User confirmed CAPTCHA solved")

            # Return success indicator
            # In a real implementation, you would extract cookies from the browser
            return {
                "manual_solve": True,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.error(f"Manual solving failed: {e}")
            return None

    def extract_cookies_after_solve(self, domain: str) -> Dict:
        """
        Extract cookies after CAPTCHA is solved.

        In a real implementation, this would:
        1. Read cookies from the browser that solved the CAPTCHA
        2. Save them for future use
        3. Return them for immediate use

        This is a placeholder that would need browser automation integration.
        """
        logger.info(f"Extracting cookies after CAPTCHA solve for {domain}")

        # Placeholder - would integrate with BrowserFetcher to extract actual cookies
        return {}

    def has_stored_captcha_cookies(self, domain: str) -> bool:
        """Check if we have stored cookies from a previous CAPTCHA solve."""
        cookie_file = self.cookie_storage_path / f"{domain.replace('.', '_')}_captcha.json"
        return cookie_file.exists()

    def load_captcha_cookies(self, domain: str) -> Dict:
        """Load cookies from a previous CAPTCHA solve."""
        cookie_file = self.cookie_storage_path / f"{domain.replace('.', '_')}_captcha.json"

        if not cookie_file.exists():
            return {}

        try:
            import json
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            logger.info(f"Loaded {len(cookies)} CAPTCHA cookies for {domain}")
            return cookies
        except Exception as e:
            logger.error(f"Failed to load CAPTCHA cookies: {e}")
            return {}

    def save_captcha_cookies(self, domain: str, cookies: Dict):
        """Save cookies after CAPTCHA solve for future use."""
        cookie_file = self.cookie_storage_path / f"{domain.replace('.', '_')}_captcha.json"

        try:
            import json
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} CAPTCHA cookies for {domain}")
        except Exception as e:
            logger.error(f"Failed to save CAPTCHA cookies: {e}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Test without API key (manual fallback only)
    handler = CaptchaHandler(use_manual_fallback=True)

    # Simulate CAPTCHA detection
    class MockResponse:
        def __init__(self):
            self.text = """
            <html>
                <body>
                    <h1>Robot Check</h1>
                    <p>Enter the characters you see below</p>
                    <img src="/captcha/image123.jpg">
                    <input type="hidden" name="csrf" value="abc123">
                </body>
            </html>
            """
            self.url = "https://www.amazon.com/captcha"

    response = MockResponse()

    if handler.detect_captcha(response):
        print("CAPTCHA detected!")
        # result = handler.solve_captcha(response, "amazon.com", solve_method="manual")
        # print(f"Result: {result}")
