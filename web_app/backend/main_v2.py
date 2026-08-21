"""
Compatibility entrypoint.

The canonical backend is ``web_app.backend.main:app``. This module remains as a
temporary import shim for old commands and should not be used by new tooling.
"""
from .main import app
