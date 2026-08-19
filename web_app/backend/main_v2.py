"""
Legacy compatibility entrypoint that re-exports the canonical backend app.
"""
from web_app.backend.main_simple import app
__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app.backend.main_simple:app", host="0.0.0.0", port=8000)