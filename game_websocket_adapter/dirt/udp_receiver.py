"""UDP receiver for Dirt Rally 2.0 telemetry packets."""

from __future__ import annotations

import asyncio
import os
import struct
import time
from typing import Any, Dict, Tuple

from shared.contracts import SessionStatus, TelemetryReceiver
from dirt.state_manager import DirtStateManager


class DirtUDPReceiver(TelemetryReceiver):
    """Receives and parses Dirt Rally 2.0 UDP telemetry packets."""

    PACKET_MIN_SIZE = 256

    def __init__(self, state_manager: DirtStateManager):
        self.state_manager = state_manager
        self.port = int(os.getenv("DIRT_UDP_PORT", "10001"))
        self.session_timeout_sec = float(os.getenv("DIRT_SESSION_TIMEOUT_SEC", "3.0"))
        self._last_packet_monotonic = 0.0
        self._monitor_task: asyncio.Task | None = None

    def _read_float(self, data: bytes, offset: int) -> float:
        return struct.unpack_from("<f", data, offset)[0]

    def parse_packet(self, data: bytes) -> Dict[str, Any]:
        if len(data) < self.PACKET_MIN_SIZE:
            raise ValueError(f"Dirt packet too small: expected >= {self.PACKET_MIN_SIZE}, got {len(data)}")

        return {
            "total_time": self._read_float(data, 0),
            "current_lap_stage_time": self._read_float(data, 4),
            "current_lap_stage_distance": self._read_float(data, 8),
            "total_distance": self._read_float(data, 12),
            "position_x": self._read_float(data, 16),
            "position_y": self._read_float(data, 20),
            "speed": self._read_float(data, 28),
            "throttle_input": self._read_float(data, 116),
            "steer_position": self._read_float(data, 120),
            "brake_input": self._read_float(data, 124),
            "clutch_input": self._read_float(data, 128),
            "gear": self._read_float(data, 132),
            "engine_speed": self._read_float(data, 148),
            "maximum_rpm": self._read_float(data, 252),
        }

    def process_packet(self, data: bytes) -> None:
        parsed = self.parse_packet(data)
        if self.state_manager.session_status == SessionStatus.IDLE:
            self.state_manager.update_from_session_start(parsed)
            self.state_manager.set_session_status(SessionStatus.ACTIVE)
        else:
            self.state_manager.update_from_session_update(parsed)
        self._last_packet_monotonic = time.monotonic()

    async def _monitor_session_timeout(self) -> None:
        while True:
            await asyncio.sleep(0.5)
            if self.state_manager.session_status != SessionStatus.ACTIVE:
                continue
            elapsed = time.monotonic() - self._last_packet_monotonic
            if elapsed > self.session_timeout_sec:
                self.state_manager.set_session_status(SessionStatus.IDLE)
                print("Dirt session ended due to telemetry timeout")

    async def start_servers(self) -> list[asyncio.DatagramTransport]:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _DirtUDPServerProtocol(self),
            local_addr=("0.0.0.0", self.port),
        )
        print(f"Dirt UDP server listening on port {self.port}")

        self._monitor_task = asyncio.create_task(self._monitor_session_timeout())
        return [transport]


class _DirtUDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, receiver: DirtUDPReceiver):
        self.receiver = receiver

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            self.receiver.process_packet(data)
        except (ValueError, struct.error, TypeError) as exc:
            print(f"Error processing Dirt packet: {exc}")

    def error_received(self, exc: Exception) -> None:
        print(f"Dirt UDP error: {exc}")
