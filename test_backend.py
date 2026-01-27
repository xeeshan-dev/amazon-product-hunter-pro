
import requests
import json

try:
    print("Sending request...")
    response = requests.post(
        "http://localhost:8000/api/search",
        json={"keyword": "test product", "pages": 1, "marketplace": "US"},
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
