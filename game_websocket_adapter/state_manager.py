"""Compatibility wrapper for the moved WRC state manager."""

from __future__ import annotations

from functools import lru_cache

from src.wrc.id_resolver import WRCIDResolver
from src.wrc.state_manager import WRCStateManager


StateManager = WRCStateManager


@lru_cache(maxsize=1)
def get_state_manager() -> WRCStateManager:
    """Get or create the global WRC state manager instance."""
    return WRCStateManager(WRCIDResolver())
