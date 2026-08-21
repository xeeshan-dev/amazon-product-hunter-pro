"""Manual API search diagnostic with relaxed and strict filters.

This script intentionally calls a live local API. It is not part of pytest.
"""
import argparse
import json

import requests


def run_search(api_url: str, payload: dict) -> None:
    response = requests.post(f"{api_url}/api/search", json=payload, timeout=120)
    print(f"POST /api/search -> {response.status_code}")
    if response.status_code != 200:
        print(response.text)
        return

    data = response.json()
    print(json.dumps(data.get("summary", {}), indent=2))
    for index, product in enumerate(data.get("results", [])[:5], start=1):
        print(
            f"{index}. {product.get('asin')} | "
            f"sales={product.get('estimated_sales')} | "
            f"margin={product.get('margin')} | "
            f"{product.get('title', '')[:80]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--keyword", default="yoga mat")
    args = parser.parse_args()

    base_payload = {
        "keyword": args.keyword,
        "marketplace": "US",
        "pages": 1,
    }

    print("Relaxed filters")
    run_search(
        args.api_url,
        {
            **base_payload,
            "min_rating": 3.0,
            "skip_risky_brands": False,
            "skip_hazmat": False,
            "skip_amazon_seller": False,
            "skip_brand_seller": False,
            "min_margin": 0,
            "min_sales": 0,
            "max_sales": 5000,
            "fetch_seller_info": False,
        },
    )

    print("\nStrict filters")
    run_search(
        args.api_url,
        {
            **base_payload,
            "min_rating": 4.0,
            "skip_risky_brands": True,
            "skip_hazmat": True,
            "skip_amazon_seller": True,
            "skip_brand_seller": True,
            "min_margin": 20,
            "min_sales": 50,
            "max_sales": 300,
            "fetch_seller_info": True,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
