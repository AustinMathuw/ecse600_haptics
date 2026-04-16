"""UDP receiver for Dirt Rally 2.0 telemetry packets."""

from __future__ import annotations

import asyncio
import csv
import os
import struct
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, IO, Optional, Tuple

from src.shared.contracts import SessionStatus, TelemetryReceiver
from src.dirt.state_manager import DirtStateManager

DUMP_PACKETS = os.getenv("DUMP_PACKETS", "false").strip().lower() == "true"

# RPM values that map to dirt
CAR_IDLE_RPM = 95
CAR_IDLE_RPM = 200
CAR_DOWNSHIFT_RPM = 400
CAR_UPSHIFT_RPM = 550
CAR_REDLINE_RPM = 600
CAR_MAX_RPM = 800

# Known field names keyed by byte offset, sourced from confirmed Dirt Rally 2.0
# UDP telemetry layout (66 fields). Brakes_temp is expanded to per-corner suffixes:
# bl=back-left, br=back-right, fl=front-left, fr=front-right.
_KNOWN_FIELDS: Dict[int, str] = {
    0: "total_time",
    4: "lap_time",
    8: "distance",
    12: "percent_complete",
    16: "x",
    20: "y",
    24: "z",
    28: "speed",
    32: "xv",
    36: "yv",
    40: "zv",
    44: "xr",
    48: "yr",
    52: "zr",
    56: "xd",
    60: "yd",
    64: "zd",
    68: "susp_pos_bl",
    72: "susp_pos_br",
    76: "susp_pos_fl",
    80: "susp_pos_fr",
    84: "susp_vel_bl",
    88: "susp_vel_br",
    92: "susp_vel_fl",
    96: "susp_vel_fr",
    100: "wheel_speed_bl",
    104: "wheel_speed_br",
    108: "wheel_speed_fl",
    112: "wheel_speed_fr",
    116: "throttle",
    120: "steer",
    124: "brake",
    128: "clutch",
    132: "gear",
    136: "gforce_lat",
    140: "gforce_lon",
    144: "lap_rx",
    148: "engine_rate",
    152: "sli_pro_native_support",
    156: "car_position_rx",
    160: "kers_level",
    164: "kers_max_level",
    168: "drs",
    172: "traction_control",
    176: "anti_lock_brakes",
    180: "fuel_in_tank",
    184: "fuel_capacity",
    188: "in_pits",
    192: "sector",
    196: "sector1_time",
    200: "sector2_time",
    204: "brakes_temp_bl",
    208: "brakes_temp_br",
    212: "brakes_temp_fl",
    216: "brakes_temp_fr",
    220: "track_size",
    224: "last_lap_time",
    228: "max_rpm",  # always 0
    232: "idle_rpm",  # always 0
    236: "current_lap_rx",  # always 0
    240: "total_laps_rx",  # always 0
    244: "track_id",
    248: "last_lap_time_rx",
    252: "vehicle_id",
    256: "car_id",
    260: "max_gear_number",
}


class DirtUDPReceiver(TelemetryReceiver):
    """Receives and parses Dirt Rally 2.0 UDP telemetry packets."""

    PACKET_MIN_SIZE = 264  # max_gear_number at offset 260 + 4 bytes

    def __init__(self, state_manager: DirtStateManager):
        self.state_manager = state_manager
        self.port = int(os.getenv("DIRT_UDP_PORT", "10001"))
        self.session_timeout_sec = float(os.getenv("DIRT_SESSION_TIMEOUT_SEC", "3.0"))
        self._last_packet_monotonic = 0.0
        self._monitor_task: asyncio.Task | None = None
        self._dump_file: Optional[IO[str]] = None
        self._dump_writer: Optional[csv.DictWriter] = None
        self._dump_packet_size: int = 0

    def _read_float(self, data: bytes, offset: int) -> float:
        return struct.unpack_from("<f", data, offset)[0]

    def _col_name(self, offset: int) -> str:
        known = _KNOWN_FIELDS.get(offset)
        return f"f{offset:03d}_{known}" if known else f"f{offset:03d}"

    def _init_dump(self, packet_size: int) -> None:
        dump_dir = Path(__file__).parents[2] / "sessions"
        dump_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = dump_dir / f"dirt_dump_{timestamp}.csv"
        offsets = range(0, packet_size - 3, 4)
        fieldnames = ["wall_time"] + [self._col_name(o) for o in offsets]
        self._dump_file = path.open("w", newline="", encoding="utf-8")
        self._dump_writer = csv.DictWriter(self._dump_file, fieldnames=fieldnames)
        self._dump_writer.writeheader()
        self._dump_packet_size = packet_size
        print(f"Dirt packet dump path: {path}")

    def _dump_packet(self, data: bytes) -> None:
        if self._dump_writer is None:
            self._init_dump(len(data))
        row: Dict[str, Any] = {"wall_time": datetime.now().isoformat()}
        size = (
            min(len(data), self._dump_packet_size)
            if self._dump_packet_size
            else len(data)
        )
        for offset in range(0, size - 3, 4):
            try:
                row[self._col_name(offset)] = self._read_float(data, offset)
            except struct.error:
                row[self._col_name(offset)] = ""
        self._dump_writer.writerow(row)
        self._dump_file.flush()  # type: ignore[union-attr]

    def parse_packet(self, data: bytes) -> Dict[str, Any]:
        if len(data) < self.PACKET_MIN_SIZE:
            raise ValueError(
                f"Dirt packet too small: expected >= {self.PACKET_MIN_SIZE}, got {len(data)}"
            )

        return {
            "total_time": self._read_float(data, 0),
            "lap_time": self._read_float(data, 4),
            "distance": self._read_float(data, 8),
            "percent_complete": self._read_float(data, 12),
            "x": self._read_float(data, 16),
            "y": self._read_float(data, 20),
            "z": self._read_float(data, 24),
            "speed": self._read_float(data, 28),
            "xv": self._read_float(data, 32),
            "yv": self._read_float(data, 36),
            "zv": self._read_float(data, 40),
            "xr": self._read_float(data, 44),
            "yr": self._read_float(data, 48),
            "zr": self._read_float(data, 52),
            "xd": self._read_float(data, 56),
            "yd": self._read_float(data, 60),
            "zd": self._read_float(data, 64),
            "susp_pos_bl": self._read_float(data, 68),
            "susp_pos_br": self._read_float(data, 72),
            "susp_pos_fl": self._read_float(data, 76),
            "susp_pos_fr": self._read_float(data, 80),
            "susp_vel_bl": self._read_float(data, 84),
            "susp_vel_br": self._read_float(data, 88),
            "susp_vel_fl": self._read_float(data, 92),
            "susp_vel_fr": self._read_float(data, 96),
            "wheel_speed_bl": self._read_float(data, 100),
            "wheel_speed_br": self._read_float(data, 104),
            "wheel_speed_fl": self._read_float(data, 108),
            "wheel_speed_fr": self._read_float(data, 112),
            "throttle": self._read_float(data, 116),
            "steer": self._read_float(data, 120),
            "brake": self._read_float(data, 124),
            "clutch": self._read_float(data, 128),
            "gear": self._read_float(data, 132),
            "gforce_lat": self._read_float(data, 136),
            "gforce_lon": self._read_float(data, 140),
            "lap_rx": self._read_float(data, 144),
            "engine_rate": self._read_float(data, 148),
            "sli_pro_native_support": self._read_float(data, 152),
            "car_position_rx": self._read_float(data, 156),
            "kers_level": self._read_float(data, 160),
            "kers_max_level": self._read_float(data, 164),
            "drs": self._read_float(data, 168),
            "traction_control": self._read_float(data, 172),
            "anti_lock_brakes": self._read_float(data, 176),
            "fuel_in_tank": self._read_float(data, 180),
            "fuel_capacity": self._read_float(data, 184),
            "in_pits": self._read_float(data, 188),
            "sector": self._read_float(data, 192),
            "sector1_time": self._read_float(data, 196),
            "sector2_time": self._read_float(data, 200),
            "brakes_temp_bl": self._read_float(data, 204),
            "brakes_temp_br": self._read_float(data, 208),
            "brakes_temp_fl": self._read_float(data, 212),
            "brakes_temp_fr": self._read_float(data, 216),
            "track_size": self._read_float(data, 220),
            "last_lap_time": self._read_float(data, 224),
            "max_rpm": CAR_MAX_RPM,  # self._read_float(data, 228),
            "idle_rpm": CAR_IDLE_RPM,  # self._read_float(data, 232),
            "red_rpm": CAR_REDLINE_RPM,
            "downshift_rpm": CAR_DOWNSHIFT_RPM,
            "upshift_rpm": CAR_UPSHIFT_RPM,
            "current_lap_rx": self._read_float(data, 236),
            "total_laps_rx": self._read_float(data, 240),
            "track_id": self._read_float(data, 244),
            "last_lap_time_rx": self._read_float(data, 248),
            "vehicle_id": self._read_float(data, 252),
            "car_id": self._read_float(data, 256),
            "max_gear_number": self._read_float(data, 260),
        }

    def process_packet(self, data: bytes) -> None:
        if DUMP_PACKETS:
            self._dump_packet(data)
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
