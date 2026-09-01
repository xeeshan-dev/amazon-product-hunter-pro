#!/usr/bin/env python
"""
Test script for seller information extraction.
Tests:
  1. Direct SellerAnalyzer via AOD endpoint (real Amazon request)
  2. Brand-as-seller detection logic (no network)
"""
import sys
import time
import logging
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s')
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)

print("=" * 70)
print("SELLER EXTRACTION TEST SUITE")
print("=" * 70)
print("\n⚠  This script makes REAL requests to Amazon.")
print("   Delays are built-in to stay respectful.\n")

# ── test data ─────────────────────────────────────────────────────────────────
TEST_ASIN = "B08N5WRWNW"   # popular yoga mat – many FBA sellers


# ── TEST 1: SellerAnalyzer via AOD endpoint ───────────────────────────────────
def test_seller_analyzer():
    print("\n" + "=" * 70)
    print("TEST 1: Direct SellerAnalyzer  (AOD endpoint)")
    print("=" * 70)

    try:
        from analysis.seller_analysis import SellerAnalyzer
        import requests

        analyzer = SellerAnalyzer()
        session  = requests.Session()
        headers  = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        print(f"\nASIN : {TEST_ASIN}")
        print("Fetching seller data from AOD endpoint …")

        seller_info = analyzer.analyze_sellers(
            soup=None,
            asin=TEST_ASIN,
            headers=headers,
            session=session,
            referer=f"https://www.amazon.com/dp/{TEST_ASIN}",
        )

        print("\n📊 Results:")
        print(f"  FBA sellers    : {seller_info.fba_count}")
        print(f"  FBM sellers    : {seller_info.fbm_count}")
        print(f"  Total sellers  : {seller_info.total_sellers}")
        print(f"  Amazon selling : {seller_info.amazon_seller}")
        print(f"  Buy Box winner : {seller_info.seller_name or 'Unknown'}")

        if seller_info.total_sellers > 0:
            print("\n✅ PASS – seller data extracted successfully")
            return True
        else:
            print("\n⚠  No sellers found – Amazon may have blocked the request")
            print("   → Enable SmartFetcher: USE_SMART_FETCHER=true")
            print("   → Enable browser fallback: ENABLE_BROWSER_FALLBACK=true")
            return False

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Make sure you are running from the project root.")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()
        return False


# ── TEST 2: Brand-as-seller detection ─────────────────────────────────────────
def test_brand_detection():
    print("\n" + "=" * 70)
    print("TEST 2: Brand-as-Seller Detection  (no network)")
    print("=" * 70)

    try:
        from analytics.winning_product_filter import WinningProductFilter
        f = WinningProductFilter()

        cases = [
            ("Adidas",          "Adidas Official Store",    True,  "exact brand match"),
            ("Nature's Bounty", "Nature's Bounty Official", True,  "multi-word brand match"),
            ("Generic",         "Amazon Seller LLC",        False, "different seller"),
            ("Art",             "Earth Products",           False, "partial word – no false positive"),
            ("Apple",           "Apple Inc",                True,  "brand with suffix"),
        ]

        passed = 0
        for brand, seller, expected, description in cases:
            result = f._brand_seller_match(brand, seller)
            ok = result == expected
            icon = "✅" if ok else "❌"
            print(f"\n{icon} {description}")
            print(f"   brand='{brand}'  seller='{seller}'")
            print(f"   got={result}  expected={expected}")
            if ok:
                passed += 1

        print(f"\n📊 {passed}/{len(cases)} cases passed")
        return passed == len(cases)

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    except AttributeError:
        print("\n❌ _brand_seller_match() not found on WinningProductFilter")
        print("   Check the method name in winning_product_filter.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()
        return False


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    r1 = test_seller_analyzer()
    time.sleep(3)
    r2 = test_brand_detection()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Test 1 – Seller extraction  : {'✅ PASS' if r1 else '❌ FAIL'}")
    print(f"  Test 2 – Brand detection    : {'✅ PASS' if r2 else '❌ FAIL'}")

    if r1 and r2:
        print("\n🎉 Everything working – seller data pipeline is healthy!")
    elif r1 and not r2:
        print("\n⚠  Seller extraction works but brand detection needs review.")
        print("   Check _brand_seller_match() in winning_product_filter.py")
    elif not r1 and r2:
        print("\n⚠  Brand detection works but seller extraction is blocked.")
        print("   Enable the anti-blocking system and retry:")
        print("   USE_SMART_FETCHER=true  ENABLE_BROWSER_FALLBACK=true")
    else:
        print("\n❌ Both tests failed – check imports and .env configuration.")

    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
