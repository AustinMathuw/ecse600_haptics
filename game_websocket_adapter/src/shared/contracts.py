"""Shared interfaces and enums for game telemetry adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
import asyncio


class SessionStatus(Enum):
    """Session lifecycle states used by all game adapters."""

    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"


class GameStateManager(ABC):
    """Interface for game-specific state managers."""

    @abstractmethod
    def update_from_session_start(self, packet_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def update_from_session_update(self, packet_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def set_session_status(self, status: SessionStatus) -> None:
        pass

    @abstractmethod
    def get_haptic_command(self) -> Optional[dict]:
        pass

    @abstractmethod
    def get_session_command(self) -> Optional[dict]:
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_full_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_driver_name(self, name: str) -> None:
        pass


class IdentityResolver(ABC):
    """Interface for resolving game-specific vehicle/track identifiers."""

    @abstractmethod
    def get_vehicle_name(self, vehicle_id: int) -> str:
        pass

    @abstractmethod
    def get_track_name(self, location_id: int, route_id: int) -> str:
        pass


class TelemetryReceiver(ABC):
    """Interface for game-specific UDP telemetry receivers."""

    @abstractmethod
    async def start_servers(self) -> list[asyncio.DatagramTransport]:
        pass
