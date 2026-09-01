"""Seller detection for Amazon product pages.

The two rules this module enforces:
  1. Amazon must NOT be selling the product (any offer, not just buy box)
  2. The product brand must NOT be selling its own product

How Amazon hides this data:
  Amazon does NOT show the full seller list on the main product page.
  The complete offer list is only available via the AOD (All Offers Display)
  AJAX endpoint: /gp/aod/ajax?asin=XXXX

  The buy box shows ONE seller. If there are 4 sellers and Amazon is #3,
  the buy box may show seller #1 — so you would miss Amazon entirely
  if you only look at the buy box.

  This module:
    1. Fetches the AOD page for every product (required for accuracy)
    2. Scans EVERY offer for Amazon names
    3. Scans EVERY offer seller name against the product brand
    4. Falls back to the offer-listing page if AOD fails
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Amazon entity name matching
# ---------------------------------------------------------------------------

# All known Amazon seller name variants (lowercase, for substring matching)
AMAZON_SELLER_NAMES = {
    "amazon",
    "amazon.com",
    "amazon.com services",
    "amazon.com services llc",
    "amazon services llc",
    "amazon eu sarl",
    "amazon retail",
    "amazon marketplace",
    "amazon fulfillment",
    "amazon logistics",
    "amazon digital services",
    "amazon digital services llc",
    "amazon.ca",
    "amazon.co.uk",
    "amazon.de",
    "amazon.fr",
    "amazon.it",
    "amazon.es",
    "amazon.nl",
    "amazon.com.au",
    "amazon.co.jp",
    "amazon.in",
    "sold by amazon",
    "ships from and sold by amazon",
}

# Phrases that appear in buy-box / merchant-info when Amazon owns the offer
AMAZON_PAGE_PHRASES = (
    "ships from and sold by amazon",
    "sold by amazon.com",
    "sold by amazon",
    "amazon.com services llc",
    "amazon services llc",
    "amazon eu sarl",
    "amazon retail",
)


def _is_amazon_seller(name: str) -> bool:
    """Return True if *name* matches any known Amazon seller entity."""
    if not name:
        return False
    n = name.strip().lower()
    # Exact set membership first (fast)
    if n in AMAZON_SELLER_NAMES:
        return True
    # Substring: "amazon.com services llc" contains "amazon"
    return any(known in n for known in AMAZON_SELLER_NAMES)


def _brand_owns_listing(seller_name: str, brand: str) -> bool:
    """Return True when the seller name matches the product brand.

    Logic: if brand is "Adidas" and seller is "Adidas US" or "Adidas Direct
    Store" — the brand is selling its own product.
    We use bidirectional substring match so short brands (e.g. "Sony") inside
    longer seller names ("Sony Electronics Inc") are caught.
    """
    if not seller_name or not brand:
        return False
    sn = _normalize_entity_name(seller_name)
    br = _normalize_entity_name(brand)
    if len(br) < 3:          # Too short to be meaningful ("ac", "bb"…)
        return False
    if sn == br:
        return True
    if len(br) <= 4 and len(sn) > len(br):
        return bool(re.search(rf"\b{re.escape(br)}\b", sn))
    return br in sn or sn in br


def _normalize_entity_name(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"[^\w\s&.-]+", " ", normalized)
    normalized = re.sub(
        r"\b(official|store|shop|direct|llc|inc|corp|ltd|co|company|usa|us)\b",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SellerOffer:
    seller_name: Optional[str] = None
    price: Optional[float] = None
    fulfillment: str = "FBM"   # "FBA" or "FBM"
    is_amazon: bool = False

    def as_dict(self) -> dict:
        return {
            "seller_name": self.seller_name,
            "price": self.price,
            "fulfillment": self.fulfillment,
            "is_amazon": self.is_amazon,
        }


@dataclass
class SellerInfo:
    # Core decision fields
    amazon_seller: bool = False          # True if Amazon has ANY offer
    brand_is_seller: bool = False        # True if brand has ANY offer
    buy_box_seller_name: Optional[str] = None
    buy_box_is_amazon: bool = False

    # Offer counts
    total_sellers: int = 0
    fba_count: int = 0
    fbm_count: int = 0

    # All parsed offers (for debugging / frontend display)
    offers: List[SellerOffer] = field(default_factory=list)
    data_status: str = SELLER_DATA_STATUS_UNAVAILABLE

    # Legacy compat
    prices: Dict = field(default_factory=lambda: {"fba": [], "fbm": [], "amazon": None})

    @property
    def seller_name(self) -> Optional[str]:
        """Buy-box seller name (legacy compat)."""
        return self.buy_box_seller_name


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class SellerAnalyzer:
    """Fetch and parse all offers for an ASIN.

    Call analyze_sellers() with an active requests.Session.  It will:
      1. Try the AOD AJAX endpoint (fastest, most complete)
      2. Fall back to /gp/offer-listing/{asin}
      3. Fall back to scanning the product page soup passed in
    """

    def analyze_sellers(
        self,
        soup,          # BeautifulSoup of the product page (may be None)
        asin: str = None,
        headers: dict = None,
        session=None,
        referer: str = None,
        brand: str = "",  # Product brand — used for brand-is-seller detection
        base_url: str = "https://www.amazon.com",
        fetch_response=None,
    ) -> SellerInfo:

        info = SellerInfo()
        if not asin:
            return info

        # ---- Step 1: fetch the full offer list --------------------------------
        offers_html, fetch_status = self._fetch_offers_html(
            asin,
            headers,
            session,
            referer,
            base_url=base_url,
            fetch_response=fetch_response,
        )

        if offers_html:
            offers = self._parse_offers(offers_html)
        elif soup:
            # Last resort: scan the main product page
            offers = self._parse_buy_box_from_soup(soup)
        else:
            offers = []

        # ---- Step 2: classify each offer --------------------------------------
        for offer in offers:
            offer.is_amazon = _is_amazon_seller(offer.seller_name or "")

        # ---- Step 3: also check buy-box text directly from product page -------
        buy_box_is_amazon = False
        buy_box_name = None
        if soup:
            buy_box_is_amazon, buy_box_name = self._read_buy_box(soup)

        # ---- Step 4: aggregate ------------------------------------------------
        any_amazon_offer = buy_box_is_amazon or any(o.is_amazon for o in offers)

        # Brand check: does any offer's seller name match the brand?
        any_brand_offer = False
        if brand:
            for offer in offers:
                if _brand_owns_listing(offer.seller_name or "", brand):
                    any_brand_offer = True
                    logger.info(
                        "[%s] Brand-sells-own-product detected: seller='%s' brand='%s'",
                        asin, offer.seller_name, brand,
                    )
                    break
            # Also check buy-box name
            if not any_brand_offer and _brand_owns_listing(buy_box_name or "", brand):
                any_brand_offer = True

        info.amazon_seller = any_amazon_offer
        info.brand_is_seller = any_brand_offer
        info.buy_box_seller_name = buy_box_name
        info.buy_box_is_amazon = buy_box_is_amazon
        info.offers = offers
        info.total_sellers = len(offers) or (1 if buy_box_name else 0)
        info.fba_count = sum(1 for o in offers if o.fulfillment == "FBA")
        info.fbm_count = sum(1 for o in offers if o.fulfillment == "FBM")
        info.prices = {
            "fba": [o.price for o in offers if o.fulfillment == "FBA" and o.price],
            "fbm": [o.price for o in offers if o.fulfillment == "FBM" and o.price],
            "amazon": next((o.price for o in offers if o.is_amazon and o.price), None),
        }
        if info.total_sellers > 0 or info.amazon_seller or info.brand_is_seller:
            info.data_status = SELLER_DATA_STATUS_OBSERVED
        elif offers_html:
            info.data_status = SELLER_DATA_STATUS_PARSE_FAILED
        else:
            info.data_status = fetch_status

        logger.info(
            "[%s] Seller summary: total=%d fba=%d fbm=%d amazon=%s brand_seller=%s buy_box='%s' status=%s",
            asin, info.total_sellers, info.fba_count, info.fbm_count,
            info.amazon_seller, info.brand_is_seller, info.buy_box_seller_name,
            info.data_status,
        )
        return info

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _fetch_offers_html(
        self,
        asin: str,
        headers: Optional[dict],
        session,
        referer: Optional[str],
        *,
        base_url: str,
        fetch_response=None,
    ) -> tuple[Optional[str], str]:
        """Try AOD AJAX → offer-listing page. Returns (raw_html, data_status)."""
        if not session and fetch_response is None:
            return None, SELLER_DATA_STATUS_UNAVAILABLE

        domain = self._resolve_marketplace_domain(base_url)
        root_url = f"https://{domain}"

        req_headers = dict(headers or {})
        req_headers.update({
            "Accept": "text/html,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Referer": referer or f"{root_url}/dp/{asin}",
            "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache",
        })

        # Set locale cookies so offers render correctly
        try:
            session.cookies.set("i18n-prefs", self._marketplace_currency(domain), domain=f".{domain}")
            session.cookies.set("lc-main", self._marketplace_locale(domain), domain=f".{domain}")
        except Exception:
            pass

        # AOD AJAX endpoints — try in order
        aod_urls = [
            f"{root_url}/gp/aod/ajax/ref=dp_aod_NEW_mbc?asin={asin}",
            f"{root_url}/gp/aod/ajax?asin={asin}",
            f"{root_url}/gp/aod/ajax/ref=dp_aod_all?asin={asin}",
        ]
        blocked_detected = False
        for url in aod_urls:
            try:
                resp = self._fetch_response(
                    url=url,
                    req_headers=req_headers,
                    referer=referer or f"{root_url}/dp/{asin}",
                    timeout=12,
                    session=session,
                    fetch_response=fetch_response,
                )
                if not resp:
                    continue
                if resp.status_code in (202, 403, 429, 503) or self._looks_like_block_page(resp.text):
                    blocked_detected = True
                    continue
                if resp.status_code == 200 and resp.text and len(resp.text) > 500:
                    # Confirm it's an offers page, not a bot-check
                    if any(kw in resp.text for kw in (
                        "aod-offer", "olpOffer", "aod-seller", "offer-listing",
                        "sold-by", "soldBy", "seller-name",
                    )):
                        logger.debug("[%s] AOD fetched from %s (%d chars)", asin, url, len(resp.text))
                        return resp.text, SELLER_DATA_STATUS_OBSERVED
            except Exception as exc:
                logger.debug("[%s] AOD fetch failed (%s): %s", asin, url, exc)

        # Fallback: full offer-listing page
        try:
            ol_url = f"{root_url}/gp/offer-listing/{asin}/ref=olp_prime_all"
            resp = self._fetch_response(
                url=ol_url,
                req_headers=req_headers,
                referer=referer or f"{root_url}/dp/{asin}",
                timeout=14,
                session=session,
                fetch_response=fetch_response,
            )
            if resp and (
                resp.status_code in (202, 403, 429, 503)
                or self._looks_like_block_page(resp.text)
            ):
                blocked_detected = True
            if resp and resp.status_code == 200 and resp.text and len(resp.text) > 500:
                logger.debug("[%s] Offer-listing page fetched (%d chars)", asin, len(resp.text))
                return resp.text, SELLER_DATA_STATUS_OBSERVED
        except Exception as exc:
            logger.debug("[%s] Offer-listing fallback failed: %s", asin, exc)

        if blocked_detected:
            return None, SELLER_DATA_STATUS_BLOCKED
        return None, SELLER_DATA_STATUS_UNAVAILABLE

    @staticmethod
    def _resolve_marketplace_domain(base_url: str) -> str:
        domain = urlparse(base_url or "").netloc
        return domain or "www.amazon.com"

    @staticmethod
    def _marketplace_currency(domain: str) -> str:
        if domain.endswith("amazon.co.uk"):
            return "GBP"
        if domain.endswith("amazon.de"):
            return "EUR"
        return "USD"

    @staticmethod
    def _marketplace_locale(domain: str) -> str:
        if domain.endswith("amazon.co.uk"):
            return "en_GB"
        if domain.endswith("amazon.de"):
            return "de_DE"
        return "en_US"

    @staticmethod
    def _fetch_response(
        *,
        url: str,
        req_headers: Dict[str, str],
        referer: str,
        timeout: int,
        session,
        fetch_response=None,
    ):
        if fetch_response is not None:
            return fetch_response(url, req_headers, referer, timeout)
        return session.get(url, headers=req_headers, timeout=timeout)

    @staticmethod
    def _looks_like_block_page(text: str) -> bool:
        lower = (text or "").lower()
        block_markers = (
            "robot check",
            "enter the characters",
            "validatecaptcha",
            "automated access to amazon data",
        )
        return any(marker in lower for marker in block_markers)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_offers(self, html: str) -> List[SellerOffer]:
        """Parse seller offers from AOD or offer-listing HTML."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        offers: List[SellerOffer] = []

        # Locate offer containers — AOD uses div.aod-offer; OLP uses div.olpOffer
        containers = (
            soup.select("div.aod-offer")
            or soup.select("div.olpOffer")
            or soup.select("div[id^='aod-offer']")
            or soup.select("li.olpOfferRow")
        )

        if not containers:
            # Broader fallback: any div that contains a sold-by link/span
            containers = [
                tag for tag in soup.find_all("div")
                if tag.find(class_=re.compile(r"aod-offer|olpOffer|sold-by|soldBy", re.I))
            ]

        logger.debug("Offer containers found: %d", len(containers))

        for container in containers:
            offer = SellerOffer()

            # ---- Seller name ----
            # AOD: div.aod-offer-soldBy  /  a inside it
            # OLP: span.olpSellerName  /  a inside it
            name_elem = (
                container.select_one(".aod-offer-soldBy a")
                or container.select_one(".aod-offer-soldBy")
                or container.select_one(".olpSellerName a")
                or container.select_one(".olpSellerName")
                or container.find("a", id=re.compile(r"soldBy|sellerProfile", re.I))
                or container.find(
                    ["span", "a", "div"],
                    class_=re.compile(r"sold.?by|seller.?name|merchant", re.I),
                )
            )
            if name_elem:
                offer.seller_name = name_elem.get_text(strip=True)

            # If no structured name, scan text for "Sold by XYZ"
            if not offer.seller_name:
                container_text = container.get_text(" ")
                m = re.search(
                    r"(?:sold\s+by|ships\s+from\s+and\s+sold\s+by)\s+([^\n\r$]{3,60})",
                    container_text, re.IGNORECASE,
                )
                if m:
                    candidate = m.group(1).strip().rstrip(".")
                    # Remove trailing fulfilment noise ("and fulfilled by Amazon")
                    candidate = re.sub(
                        r"\s+and\s+(fulfilled|shipped)\s+by.*$", "", candidate, flags=re.IGNORECASE
                    ).strip()
                    if candidate:
                        offer.seller_name = candidate

            # ---- Is Amazon ----
            # Check name AND any tell-tale phrases in the container text
            container_text_low = container.get_text(" ").lower()
            offer.is_amazon = _is_amazon_seller(offer.seller_name or "") or any(
                phrase in container_text_low for phrase in AMAZON_PAGE_PHRASES
            )

            # ---- Price ----
            price_elem = (
                container.select_one("span.a-offscreen")
                or container.select_one("span.a-price-whole")
                or container.select_one("span.olpOfferPrice")
                or container.select_one("span.a-color-price")
            )
            if price_elem:
                offer.price = _parse_price(price_elem.get_text())

            # ---- Fulfillment ----
            is_prime = bool(
                container.find(class_=re.compile(r"a-icon-prime", re.I))
                or container.find("i", {"class": re.compile(r"prime", re.I)})
                or container.find(attrs={"aria-label": re.compile(r"prime", re.I)})
                or "fulfilled by amazon" in container_text_low
                or "prime eligible" in container_text_low
            )
            offer.fulfillment = "FBA" if is_prime else "FBM"

            offers.append(offer)
            logger.debug(
                "  Offer: seller='%s' amazon=%s fulfillment=%s price=%s",
                offer.seller_name, offer.is_amazon, offer.fulfillment, offer.price,
            )

        return offers

    def _parse_buy_box_from_soup(self, soup) -> List[SellerOffer]:
        """Extract at least the buy-box offer from the main product page."""
        offers: List[SellerOffer] = []
        is_amazon, name = self._read_buy_box(soup)
        offer = SellerOffer(
            seller_name=name or ("Amazon.com" if is_amazon else None),
            is_amazon=is_amazon,
            fulfillment="FBA" if is_amazon else "FBM",
        )
        if offer.seller_name or offer.is_amazon:
            offers.append(offer)
        return offers

    def _read_buy_box(self, soup) -> tuple[bool, Optional[str]]:
        """Return (is_amazon, seller_name) from the buy-box / merchant-info section."""
        if not soup:
            return False, None

        # --- Is Amazon selling? ---
        page_text_low = soup.get_text(" ").lower()
        is_amazon = any(phrase in page_text_low for phrase in AMAZON_PAGE_PHRASES)

        # More targeted check in the merchant-info block
        merchant_div = (
            soup.find("div", id="merchant-info")
            or soup.find("div", id="seller-info")
            or soup.find("span", id="merchant-info")
        )
        if merchant_div:
            mtext = merchant_div.get_text(" ").lower()
            if any(phrase in mtext for phrase in AMAZON_PAGE_PHRASES):
                is_amazon = True

        # --- Seller name (non-Amazon only) ---
        seller_name: Optional[str] = None

        # sellerProfileTriggerId is the clearest signal
        link = soup.find("a", id="sellerProfileTriggerId")
        if link:
            seller_name = link.get_text(strip=True)

        # merchant-info div — parse "Sold by XYZ"
        if not seller_name and merchant_div:
            m = re.search(
                r"(?:sold\s+by|ships\s+from\s+and\s+sold\s+by)\s+([^\n\r$]{3,60})",
                merchant_div.get_text(" "), re.IGNORECASE,
            )
            if m:
                candidate = m.group(1).strip().rstrip(".")
                candidate = re.sub(
                    r"\s+and\s+(fulfilled|shipped)\s+by.*$", "", candidate, flags=re.IGNORECASE
                ).strip()
                if candidate and not _is_amazon_seller(candidate):
                    seller_name = candidate

        return is_amazon, seller_name

    # ------------------------------------------------------------------
    # Legacy compat
    # ------------------------------------------------------------------

    def _is_amazon_name(self, name: str) -> bool:
        return _is_amazon_seller(name)

    def meets_criteria(
        self,
        seller_info: SellerInfo,
        min_fba: int = 4,
        max_fba: int = 5,
        min_fbm: int = 2,
        max_fbm: int = 3,
        allow_amazon: bool = False,
    ) -> bool:
        fba_ok = min_fba <= (seller_info.fba_count or 0) <= max_fba
        fbm_ok = min_fbm <= (seller_info.fbm_count or 0) <= max_fbm
        amazon_ok = True if allow_amazon else not seller_info.amazon_seller
        return fba_ok and fbm_ok and amazon_ok


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    if m:
        try:
            v = float(m.group())
            return v if 0.01 <= v <= 10_000 else None
        except ValueError:
            pass
    return None
SELLER_DATA_STATUS_OBSERVED = "observed"
SELLER_DATA_STATUS_UNAVAILABLE = "unavailable"
SELLER_DATA_STATUS_BLOCKED = "blocked"
SELLER_DATA_STATUS_PARSE_FAILED = "parse_failed"
