"""
UDP receiver for WRC telemetry packets.

Listens for UDP packets from EA SPORTS WRC game, parses binary data, and updates the state manager.
"""

import asyncio
import struct
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from state_manager import get_state_manager, SessionStatus


class PacketStructure:
    """Represents a parsed packet structure with channel info."""
    
    def __init__(self, packet_id: str, channels: List[str], channel_types: Dict[str, str]):
        """Initialize packet structure.
        
        Args:
            packet_id: Packet identifier (e.g., "session_start")
            channels: Ordered list of channel IDs in this packet
            channel_types: Mapping of channel ID to data type
        """
        self.packet_id = packet_id
        self.channels = channels
        self.channel_types = channel_types
        
        # Build struct format string for unpacking
        self.format_string = self._build_format_string()
        self.struct_size = struct.calcsize(self.format_string)
    
    def _build_format_string(self) -> str:
        """Build struct format string from channel types.
        
        Returns:
            Format string for struct.unpack (e.g., "<Iff...")
        """
        # Little Endian format
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
            "fourcc": "4s",  # 4-byte string
        }
        
        for channel_id in self.channels:
            channel_type = self.channel_types.get(channel_id, "float32")
            format_code = type_mapping.get(channel_type, "f")
            format_parts.append(format_code)
        
        return "".join(format_parts)
    
    def parse(self, data: bytes) -> Dict[str, Any]:
        """Parse binary packet data.
        
        Args:
            data: Raw binary packet data
            
        Returns:
            Dictionary mapping channel IDs to parsed values
        """
        if len(data) < self.struct_size:
            raise ValueError(f"Packet too small: expected {self.struct_size}, got {len(data)}")
        
        # Unpack binary data
        values = struct.unpack(self.format_string, data[:self.struct_size])
        
        # Build result dictionary
        result = {}
        for i, channel_id in enumerate(self.channels):
            value = values[i]
            
            # Convert fourcc bytes to string
            if self.channel_types.get(channel_id) == "fourcc":
                value = value.decode('ascii', errors='ignore')
            
            result[channel_id] = value
        
        return result


class WRCUDPReceiver:
    """Receives and parses WRC UDP telemetry packets."""
    
    def __init__(self):
        """Initialize UDP receiver."""
        self.state_manager = get_state_manager()
        self.packet_structures: Dict[str, PacketStructure] = {}
        self.fourcc_map: Dict[str, str] = {}
        
        # Load packet structures
        self._load_packet_definitions()
    
    def _load_packet_definitions(self) -> None:
        """Load packet structure definitions from JSON files."""
        base_path = Path(__file__).parent
        
        # Load channel types from channels.json
        channels_path = base_path / "wrc_deps" / "readme" / "channels.json"
        try:
            with open(channels_path, 'r', encoding='utf-8-sig') as f:
                channels_data = json.load(f)
            
            channel_types = {}
            for channel in channels_data.get('channels', []):
                channel_types[channel['id']] = channel['type']
            
            print(f"Loaded {len(channel_types)} channel type definitions")
        except Exception as e:
            print(f"Error loading channels.json: {e}")
            channel_types = {}
        
        # Load wrc_haptic_watch packet structure
        haptic_watch_path = base_path / "wrc_deps" / "udp" / "wrc_haptic_watch.json"
        try:
            with open(haptic_watch_path, 'r', encoding='utf-8-sig') as f:
                haptic_watch_data = json.load(f)
            
            # Get header channels (common to all packets)
            header_channels = haptic_watch_data.get('header', {}).get('channels', [])
            
            # Parse each packet type
            for packet in haptic_watch_data.get('packets', []):
                packet_id = packet['id']
                packet_channels = header_channels + packet['channels']
                
                structure = PacketStructure(packet_id, packet_channels, channel_types)
                self.packet_structures[packet_id] = structure
                
                print(f"Loaded packet structure: {packet_id} "
                      f"({len(packet_channels)} channels, {structure.struct_size} bytes)")
        except Exception as e:
            print(f"Error loading wrc_haptic_watch.json: {e}")
        
        # Load packet fourCC mappings
        packets_path = base_path / "wrc_deps" / "readme" / "packets.json"
        try:
            with open(packets_path, 'r', encoding='utf-8-sig') as f:
                packets_data = json.load(f)
            
            for packet in packets_data.get('packets', []):
                fourcc = packet.get('fourCC', '')
                packet_id = packet['id']
                self.fourcc_map[fourcc] = packet_id
        except Exception as e:
            print(f"Error loading packets.json: {e}")
    
    def _identify_packet(self, data: bytes) -> Optional[str]:
        """Identify packet type from data.
        
        Args:
            data: Raw packet data
            
        Returns:
            Packet ID string, or None if unable to identify
        """
        # Check if packet has header with fourCC
        if len(data) >= 4:
            # Try to extract fourCC from the first field (after packet_4cc in header)
            # The packet_4cc is a fourcc type (4 bytes)
            try:
                fourcc = data[:4].decode('ascii', errors='ignore').upper()
                if fourcc in self.fourcc_map:
                    return self.fourcc_map[fourcc]
            except (UnicodeDecodeError, AttributeError):
                pass
        
        return None
    
    def process_packet(self, data: bytes, from_port: int) -> None:
        """Process a received UDP packet.
        
        Args:
            data: Raw packet data
            from_port: Port the packet was received on
        """
        try:
            # Try to identify packet type from fourCC
            packet_id = self._identify_packet(data)
            
            # If no fourCC or not found, infer from port
            if packet_id is None:
                print(f"Warning: Could not identify packet from fourCC for port {from_port}")
                return
            
            # Get packet structure
            if packet_id not in self.packet_structures:
                print(f"Warning: No structure defined for packet {packet_id}")
                return
            
            structure = self.packet_structures[packet_id]
            
            # Parse packet
            packet_data = structure.parse(data)
            
            # Handle different packet types
            if packet_id == "session_start":
                self.state_manager.update_from_session_start(packet_data)
                self.state_manager.set_session_status(SessionStatus.ACTIVE)
            
            elif packet_id == "session_update":
                self.state_manager.update_from_session_update(packet_data)
            
            elif packet_id == "session_end":
                self.state_manager.set_session_status(SessionStatus.IDLE)
                print("Session ended")
            
            elif packet_id == "session_pause":
                self.state_manager.set_session_status(SessionStatus.PAUSED)
                print("Session paused")
            
            elif packet_id == "session_resume":
                self.state_manager.set_session_status(SessionStatus.ACTIVE)
                print("Session resumed")
        
        except Exception as e:
            print(f"Error processing packet: {e}")


class UDPServerProtocol(asyncio.DatagramProtocol):
    """Async UDP server protocol."""
    
    def __init__(self, receiver: WRCUDPReceiver, port: int):
        """Initialize protocol.
        
        Args:
            receiver: WRCUDPReceiver instance to handle packets
            port: Port this server is listening on
        """
        self.receiver = receiver
        self.port = port
        self.transport = None
    
    def connection_made(self, transport):
        """Called when connection is established."""
        self.transport = transport
        print(f"UDP server listening on port {self.port}")
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Called when a datagram is received.
        
        Args:
            data: Received data
            addr: Source address (host, port)
        """
        self.receiver.process_packet(data, self.port)
    
    def error_received(self, exc):
        """Called when an error is received."""
        print(f"UDP error on port {self.port}: {exc}")


async def start_udp_servers(receiver: WRCUDPReceiver) -> List[asyncio.DatagramTransport]:
    """Start UDP servers on ports 29888 and 29889.
    
    Args:
        receiver: WRCUDPReceiver instance to handle packets
        
    Returns:
        List of transport objects
    """
    loop = asyncio.get_running_loop()
    transports = []
    
    # Start server on port 29888 (session_update)
    transport1, _ = await loop.create_datagram_endpoint(
        lambda: UDPServerProtocol(receiver, 29888),
        local_addr=('0.0.0.0', 29888)
    )
    transports.append(transport1)
    
    # Start server on port 29889 (session_start/end/pause/resume)
    transport2, _ = await loop.create_datagram_endpoint(
        lambda: UDPServerProtocol(receiver, 29889),
        local_addr=('0.0.0.0', 29889)
    )
    transports.append(transport2)
    
    return transports
