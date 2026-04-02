"""Compatibility wrapper for the moved WRC state manager."""

from __future__ import annotations

from functools import lru_cache

from wrc.id_resolver import WRCIDResolver
from wrc.state_manager import WRCStateManager


StateManager = WRCStateManager


@lru_cache(maxsize=1)
def get_state_manager() -> WRCStateManager:
    """Get or create the global WRC state manager instance."""
    return WRCStateManager(WRCIDResolver())
