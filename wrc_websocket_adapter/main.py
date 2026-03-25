"""
WRC Telemetry to WebSocket Adapter

Receives UDP telemetry from EA SPORTS WRC and provides a WebSocket
interface for haptic devices (phone/watch).
"""

import asyncio
from udp_receiver import WRCUDPReceiver, start_udp_servers
from websocket_server import HapticWebSocketServer


async def main():
    """Main entry point - run UDP and WebSocket servers concurrently."""
    print("=" * 60)
    print("WRC Telemetry to WebSocket Adapter")
    print("=" * 60)
    
    # Initialize components
    udp_receiver = WRCUDPReceiver()
    ws_server = HapticWebSocketServer()
    
    # Start UDP servers
    print("\nStarting UDP servers...")
    udp_transports = await start_udp_servers(udp_receiver)
    
    # Start WebSocket server (this blocks until stopped)
    print("Starting WebSocket server...")
    print("\nAdapter is running. Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        await ws_server.start()
    except asyncio.CancelledError:
        pass
    finally:
        # Clean up UDP transports
        print("\nShutting down...")
        for transport in udp_transports:
            transport.close()
        print("Stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"\nError: {e}")
        raise
