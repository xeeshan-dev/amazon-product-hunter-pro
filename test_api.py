"""
Quick test script to verify the Amazon Hunter Pro API is working
"""
import requests
import json

API_URL = "http://127.0.0.1:8001"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_search():
    """Test search endpoint with filters"""
    print("Testing search endpoint with advanced filters...")
    payload = {
        "keyword": "water bottle",
        "marketplace": "US",
        "pages": 1,
        "min_rating": 4.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": True,
        "skip_brand_seller": True,
        "min_margin": 20.0,
        "min_sales": 50,
        "max_sales": 500,
        "fetch_seller_info": True
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...")
    
    try:
        response = requests.post(f"{API_URL}/api/search", json=payload, timeout=60)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"\nSummary:")
            print(f"  - Total products found: {data['summary']['total_products']}")
            print(f"  - Total market revenue: ${data['summary']['total_revenue']:,.0f}")
            print(f"  - Average revenue: ${data['summary']['avg_revenue']:,.0f}")
            print(f"  - Average sales: {data['summary']['avg_sales']:.0f}/month")
            
            if data['results']:
                print(f"\nTop 3 Products:")
                for i, product in enumerate(data['results'][:3], 1):
                    print(f"\n  {i}. {product['title'][:60]}...")
                    print(f"     Price: ${product['price']:.2f}")
                    print(f"     Revenue: ${product['est_revenue']:,.0f}")
                    print(f"     Margin: {product['margin']:.1f}%")
                    print(f"     Score: {product['enhanced_score']}/100")
                    if product.get('seller_info'):
                        print(f"     Amazon Seller: {product['seller_info'].get('amazon_seller', 'Unknown')}")
                        print(f"     Seller Name: {product['seller_info'].get('seller_name', 'Unknown')}")
            
            print(f"\nFilters Applied:")
            for key, value in data['metadata']['filters_applied'].items():
                print(f"  - {key}: {value}")
        else:
            print(f"❌ ERROR: {response.text}")
    
    except requests.exceptions.Timeout:
        print("❌ Request timed out (this is normal for first request as it scrapes Amazon)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Amazon Hunter Pro API Test")
    print("=" * 60)
    print()
    
    test_health()
    
    print("=" * 60)
    print()
    
    test_search()
    
    print()
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)
