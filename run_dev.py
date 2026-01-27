"""
Development server runner (simple version, no Redis needed)
"""
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

print("🚀 Starting Amazon Hunter Pro API (Development Mode)")
print("📝 Simple version - no Redis required")
print("=" * 60)

# Now import and run
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "web_app.backend.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
