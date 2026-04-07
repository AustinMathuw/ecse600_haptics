"""Placeholder ID resolver for Dirt Rally 2.0 (IDs are not exposed like WRC)."""

from __future__ import annotations

from src.shared.contracts import IdentityResolver


class DirtIDResolver(IdentityResolver):
    """Dirt Rally 2.0 does not expose WRC-style car/track IDs over this feed."""

    def get_vehicle_name(self, vehicle_id: int) -> str:
        return "Unknown Dirt Vehicle"

    def get_track_name(self, location_id: int, route_id: int) -> str:
        return "Unknown Dirt Track"
