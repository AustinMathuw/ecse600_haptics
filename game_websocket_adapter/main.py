"""Game telemetry to WebSocket adapter for haptic devices."""

import asyncio
import os

from shared.websocket_server import HapticWebSocketServer
from wrc.id_resolver import WRCIDResolver
from wrc.state_manager import WRCStateManager
from wrc.udp_receiver import WRCUDPReceiver
from dirt.state_manager import DirtStateManager
from dirt.udp_receiver import DirtUDPReceiver


def _create_game_services():
    """Create state manager and receiver for the selected game mode."""
    game_mode = os.getenv("GAME_ADAPTER", "wrc").strip().lower()
    if game_mode == "wrc":
        state_manager = WRCStateManager(WRCIDResolver())
        receiver = WRCUDPReceiver(state_manager)
        banner = "EA SPORTS WRC"
    elif game_mode in {"dirt", "dirt2", "dr2", "dirt_rally_2_0"}:
        state_manager = DirtStateManager()
        receiver = DirtUDPReceiver(state_manager)
        banner = "DiRT Rally 2.0"
    else:
        raise ValueError(
            f"Unsupported GAME_ADAPTER '{game_mode}'. Use 'wrc' or 'dirt2'."
        )

    return game_mode, banner, state_manager, receiver


async def main():
    """Main entry point - run UDP and WebSocket servers concurrently."""
    game_mode, banner, state_manager, telemetry_receiver = _create_game_services()

    print("=" * 60)
    print("Game Telemetry to WebSocket Adapter")
    print(f"Mode: {game_mode} ({banner})")
    print("=" * 60)

    ws_server = HapticWebSocketServer(state_manager=state_manager)

    print("\nStarting UDP servers...")
    udp_transports = await telemetry_receiver.start_servers()

    print("Starting WebSocket server...")
    print("\nAdapter is running. Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        await ws_server.start()
    except asyncio.CancelledError:
        pass
    finally:
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
