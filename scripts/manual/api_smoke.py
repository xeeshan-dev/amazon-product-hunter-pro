"""Manual smoke test for a running Amazon Hunter API.

This script intentionally calls a live local API. It is not part of pytest.
"""
import argparse
import json

import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--keyword", default="water bottle")
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args()

    health = requests.get(f"{args.api_url}/health", timeout=10)
    print(f"GET /health -> {health.status_code}")
    print(json.dumps(health.json(), indent=2))

    payload = {
        "keyword": args.keyword,
        "marketplace": "US",
        "pages": args.pages,
        "min_rating": 3.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": False,
        "skip_brand_seller": False,
        "min_margin": 0,
        "min_sales": 0,
        "max_sales": 5000,
        "fetch_seller_info": False,
    }
    response = requests.post(f"{args.api_url}/api/search", json=payload, timeout=90)
    print(f"POST /api/search -> {response.status_code}")
    if response.status_code != 200:
        print(response.text)
        return 1

    data = response.json()
    print(json.dumps(data.get("summary", {}), indent=2))
    for index, product in enumerate(data.get("results", [])[:3], start=1):
        print(
            f"{index}. {product.get('asin')} | "
            f"${product.get('price')} | "
            f"score={product.get('enhanced_score')} | "
            f"{product.get('title', '')[:80]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
