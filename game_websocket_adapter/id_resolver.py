"""Compatibility wrapper for the moved WRC ID resolver."""

from __future__ import annotations

from functools import lru_cache

from src.wrc.id_resolver import WRCIDResolver


IDResolver = WRCIDResolver


@lru_cache(maxsize=1)
def get_resolver() -> WRCIDResolver:
    """Get or create the global WRC ID resolver instance."""
    return WRCIDResolver()
