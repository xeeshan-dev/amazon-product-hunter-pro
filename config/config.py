"""Compatibility module for older imports.

New code should import from `config.settings`.
"""
from config.settings import Config, Settings, config, get_settings

__all__ = ["Config", "Settings", "config", "get_settings"]
