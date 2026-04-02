"""Compatibility wrapper for moved WRC UDP receiver."""

from __future__ import annotations

from wrc.udp_receiver import WRCUDPReceiver


async def start_udp_servers(receiver: WRCUDPReceiver):
    """Backward-compatible helper for starting WRC UDP servers."""
    return await receiver.start_servers()
