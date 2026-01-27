"""
Test search with relaxed filters to see results
"""
import requests
import json

API_URL = "http://127.0.0.1:8001"

def test_with_relaxed_filters():
    """Test with very relaxed filters to ensure we get results"""
    print("=" * 70)
    print("Testing with RELAXED filters to get results")
    print("=" * 70)
    
    payload = {
        "keyword": "yoga mat",  # Non-hazmat product
        "marketplace": "US",
        "pages": 1,
        "min_rating": 3.0,  # Lower rating requirement
        "skip_risky_brands": False,  # Allow risky brands
        "skip_hazmat": False,  # Allow hazmat
        "skip_amazon_seller": False,  # Allow Amazon sellers
        "skip_brand_seller": False,  # Allow brand sellers
        "min_margin": 10.0,  # Lower margin requirement
        "min_sales": 10,  # Very low minimum
        "max_sales": 5000,  # Very high maximum
        "fetch_seller_info": False  # Faster without seller info
    }
    
    print(f"\nSearching for: {payload['keyword']}")
    print(f"Filters: RELAXED (should get many results)")
    print("\nSending request...")
    
    try:
        response = requests.post(f"{API_URL}/api/search", json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"\n📊 Results:")
            print(f"  - Products found: {data['summary']['total_products']}")
            print(f"  - Total revenue: ${data['summary']['total_revenue']:,.0f}")
            print(f"  - Avg revenue: ${data['summary']['avg_revenue']:,.0f}")
            
            if data['results']:
                print(f"\n🏆 Top 5 Products:")
                for i, p in enumerate(data['results'][:5], 1):
                    print(f"\n  {i}. {p['title'][:60]}...")
                    print(f"     💰 Price: ${p['price']:.2f}")
                    print(f"     📈 Revenue: ${p['est_revenue']:,.0f}")
                    print(f"     📊 Sales: {p['estimated_sales']:.0f}/mo")
                    print(f"     💵 Margin: {p['margin']:.1f}%")
                    print(f"     ⭐ Score: {p['enhanced_score']}/100")
                    if p.get('is_vetoed'):
                        print(f"     ⚠️  VETOED: {p.get('veto_reasons')}")
            else:
                print("\n❌ No products returned even with relaxed filters!")
                print("This might indicate an issue with the scraper.")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out (this can happen on first search)")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_with_strict_filters():
    """Test with strict filters (like in the UI)"""
    print("\n" + "=" * 70)
    print("Testing with STRICT filters (like in UI)")
    print("=" * 70)
    
    payload = {
        "keyword": "yoga mat",
        "marketplace": "US",
        "pages": 1,
        "min_rating": 4.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": True,
        "skip_brand_seller": True,
        "min_margin": 20.0,
        "min_sales": 50,
        "max_sales": 300,
        "fetch_seller_info": True
    }
    
    print(f"\nSearching for: {payload['keyword']}")
    print(f"Filters: STRICT (may filter out many products)")
    print("\nSending request...")
    
    try:
        response = requests.post(f"{API_URL}/api/search", json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"\n📊 Results:")
            print(f"  - Products found: {data['summary']['total_products']}")
            
            if data['summary']['total_products'] == 0:
                print("\n⚠️  NO PRODUCTS PASSED FILTERS!")
                print("\n💡 Suggestions:")
                print("  1. Try unchecking 'Skip Amazon as Seller'")
                print("  2. Try unchecking 'Skip Brand as Seller'")
                print("  3. Lower the Min Margin to 15%")
                print("  4. Increase Sales Range to 50-1000")
                print("  5. Try a different product category")
            else:
                print(f"  - Total revenue: ${data['summary']['total_revenue']:,.0f}")
                print(f"\n🏆 Products that passed strict filters:")
                for i, p in enumerate(data['results'][:3], 1):
                    print(f"\n  {i}. {p['title'][:60]}...")
                    print(f"     💰 Price: ${p['price']:.2f}")
                    print(f"     📊 Sales: {p['estimated_sales']:.0f}/mo")
                    print(f"     💵 Margin: {p['margin']:.1f}%")
        else:
            print(f"❌ Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n🔍 Amazon Hunter Pro - Filter Diagnostic Tool\n")
    
    # Test 1: Relaxed filters (should get results)
    test_with_relaxed_filters()
    
    print("\n" + "=" * 70)
    input("\nPress Enter to test with strict filters...")
    
    # Test 2: Strict filters (might get 0 results)
    test_with_strict_filters()
    
    print("\n" + "=" * 70)
    print("✅ Diagnostic complete!")
    print("=" * 70)
