
import requests
import json
import time

try:
    print("Sending request with 2 pages...")
    start = time.time()
    response = requests.post(
        "http://localhost:8000/api/search",
        json={"keyword": "yoga mat", "pages": 2, "marketplace": "US"},
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    print(f"Time taken: {time.time() - start:.2f} seconds")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
