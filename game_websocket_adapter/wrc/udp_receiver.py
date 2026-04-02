"""UDP receiver for EA SPORTS WRC telemetry packets."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import struct
from typing import Any, Dict, List, Optional, Tuple

from shared.contracts import SessionStatus, TelemetryReceiver
from wrc.state_manager import WRCStateManager


class PacketStructure:
    """Represents a parsed WRC packet structure with channel info."""

    def __init__(self, packet_id: str, channels: List[str], channel_types: Dict[str, str]):
        self.packet_id = packet_id
        self.channels = channels
        self.channel_types = channel_types
        self.format_string = self._build_format_string()
        self.struct_size = struct.calcsize(self.format_string)

    def _build_format_string(self) -> str:
        format_parts = ["<"]
        type_mapping = {
            "uint8": "B",
            "uint16": "H",
            "uint32": "I",
            "uint64": "Q",
            "int8": "b",
            "int16": "h",
            "int32": "i",
            "int64": "q",
            "float32": "f",
            "float64": "d",
            "boolean": "?",
            "fourcc": "4s",
        }
        for channel_id in self.channels:
            channel_type = self.channel_types.get(channel_id, "float32")
            format_parts.append(type_mapping.get(channel_type, "f"))
        return "".join(format_parts)

    def parse(self, data: bytes) -> Dict[str, Any]:
        if len(data) < self.struct_size:
            raise ValueError(f"Packet too small: expected {self.struct_size}, got {len(data)}")

        values = struct.unpack(self.format_string, data[: self.struct_size])
        result: Dict[str, Any] = {}
        for i, channel_id in enumerate(self.channels):
            value = values[i]
            if self.channel_types.get(channel_id) == "fourcc":
                value = value.decode("ascii", errors="ignore")
            result[channel_id] = value
        return result


class WRCUDPReceiver(TelemetryReceiver):
    """Receives and parses WRC UDP telemetry packets."""

    def __init__(self, state_manager: WRCStateManager):
        self.state_manager = state_manager
        self.packet_structures: Dict[str, PacketStructure] = {}
        self.fourcc_map: Dict[str, str] = {}
        self._load_packet_definitions()

    def _load_packet_definitions(self) -> None:
        base_path = Path(__file__).resolve().parent.parent

        channels_path = base_path / "wrc_deps" / "readme" / "channels.json"
        channel_types: Dict[str, str] = {}
        try:
            with open(channels_path, "r", encoding="utf-8-sig") as f:
                channels_data = json.load(f)
            for channel in channels_data.get("channels", []):
                channel_types[channel["id"]] = channel["type"]
            print(f"Loaded {len(channel_types)} WRC channel type definitions")
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            print(f"Error loading channels.json: {exc}")

        haptic_watch_path = base_path / "wrc_deps" / "udp" / "wrc_haptic_watch.json"
        try:
            with open(haptic_watch_path, "r", encoding="utf-8-sig") as f:
                haptic_watch_data = json.load(f)

            header_channels = haptic_watch_data.get("header", {}).get("channels", [])
            for packet in haptic_watch_data.get("packets", []):
                packet_id = packet["id"]
                packet_channels = header_channels + packet["channels"]
                structure = PacketStructure(packet_id, packet_channels, channel_types)
                self.packet_structures[packet_id] = structure
                print(
                    f"Loaded WRC packet structure: {packet_id} "
                    f"({len(packet_channels)} channels, {structure.struct_size} bytes)"
                )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            print(f"Error loading wrc_haptic_watch.json: {exc}")

        packets_path = base_path / "wrc_deps" / "readme" / "packets.json"
        try:
            with open(packets_path, "r", encoding="utf-8-sig") as f:
                packets_data = json.load(f)
            for packet in packets_data.get("packets", []):
                fourcc = packet.get("fourCC", "")
                packet_id = packet["id"]
                self.fourcc_map[fourcc] = packet_id
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            print(f"Error loading packets.json: {exc}")

    def _identify_packet(self, data: bytes) -> Optional[str]:
        if len(data) < 4:
            return None

        try:
            fourcc = data[:4].decode("ascii", errors="ignore").upper()
            return self.fourcc_map.get(fourcc)
        except (UnicodeDecodeError, AttributeError):
            return None

    def process_packet(self, data: bytes, from_port: int) -> None:
        try:
            packet_id = self._identify_packet(data)
            if packet_id is None:
                print(f"Warning: Could not identify WRC packet for port {from_port}")
                return

            structure = self.packet_structures.get(packet_id)
            if structure is None:
                print(f"Warning: No WRC structure defined for packet {packet_id}")
                return

            packet_data = structure.parse(data)
            if packet_id == "session_start":
                self.state_manager.update_from_session_start(packet_data)
                self.state_manager.set_session_status(SessionStatus.ACTIVE)
            elif packet_id == "session_update":
                self.state_manager.update_from_session_update(packet_data)
            elif packet_id == "session_end":
                self.state_manager.set_session_status(SessionStatus.IDLE)
                print("WRC session ended")
            elif packet_id == "session_pause":
                self.state_manager.set_session_status(SessionStatus.PAUSED)
                print("WRC session paused")
            elif packet_id == "session_resume":
                self.state_manager.set_session_status(SessionStatus.ACTIVE)
                print("WRC session resumed")
        except (ValueError, TypeError, KeyError, struct.error) as exc:
            print(f"Error processing WRC packet: {exc}")

    async def start_servers(self) -> list[asyncio.DatagramTransport]:
        loop = asyncio.get_running_loop()
        transports: list[asyncio.DatagramTransport] = []

        transport1, _ = await loop.create_datagram_endpoint(
            lambda: _WRCUDPServerProtocol(self, 29888),
            local_addr=("0.0.0.0", 29888),
        )
        transports.append(transport1)

        transport2, _ = await loop.create_datagram_endpoint(
            lambda: _WRCUDPServerProtocol(self, 29889),
            local_addr=("0.0.0.0", 29889),
        )
        transports.append(transport2)

        return transports


class _WRCUDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, receiver: WRCUDPReceiver, port: int):
        self.receiver = receiver
        self.port = port

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        print(f"WRC UDP server listening on port {self.port}")

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.receiver.process_packet(data, self.port)

    def error_received(self, exc: Exception) -> None:
        print(f"WRC UDP error on port {self.port}: {exc}")
