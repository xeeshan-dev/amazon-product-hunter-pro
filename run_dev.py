"""
Development server runner for the canonical FastAPI backend.
"""
import os
import sys

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

print("Starting Amazon Hunter Pro API (Development Mode)")
print("Backend: web_app.backend.main:app")
print("=" * 60)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "web_app.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
