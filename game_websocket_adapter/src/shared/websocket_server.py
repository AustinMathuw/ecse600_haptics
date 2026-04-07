"""WebSocket server that broadcasts haptic/session events."""

from __future__ import annotations

import asyncio
import importlib
import json
from typing import Any, Set
from urllib.parse import parse_qs, urlparse

from src.shared.contracts import GameStateManager


class HapticWebSocketServer:
    """WebSocket server for haptic device connections."""

    def __init__(
        self, state_manager: GameStateManager, host: str = "0.0.0.0", port: int = 8080
    ):
        self.host = host
        self.port = port
        self.state_manager = state_manager
        self.clients: Set[Any] = set()
        self._broadcast_task: asyncio.Task | None = None
        self._running = False
        self._websockets_module = None

    @property
    def websockets(self):
        if self._websockets_module is None:
            self._websockets_module = importlib.import_module("websockets")
        return self._websockets_module

    async def register(self, websocket: Any) -> None:
        self.clients.add(websocket)
        remote = websocket.remote_address
        print(f"Client connected: {remote[0]}:{remote[1]} (total: {len(self.clients)})")

    async def unregister(self, websocket: Any) -> None:
        self.clients.discard(websocket)
        remote = websocket.remote_address
        print(
            f"Client disconnected: {remote[0]}:{remote[1]} (total: {len(self.clients)})"
        )

    async def handle_client(self, websocket: Any) -> None:
        path = websocket.request.path if websocket.request is not None else "/"
        params = parse_qs(urlparse(path).query)
        driver_name = params.get("driver", ["Default Driver"])[0]
        self.state_manager.set_driver_name(driver_name)
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "get_state":
                        await websocket.send(
                            json.dumps(self.state_manager.get_full_state())
                        )
                except json.JSONDecodeError:
                    print(f"Invalid JSON from client: {message}")
        except self.websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def broadcast(self, message: str) -> None:
        if not self.clients:
            return

        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True,
        )

    async def broadcast_message(self, message_dict: dict) -> None:
        await self.broadcast(json.dumps(message_dict))

    async def _broadcast_loop(self) -> None:
        interval = 0.05
        while self._running:
            try:
                if self.clients:
                    session_cmd = self.state_manager.get_session_command()
                    if session_cmd:
                        await self.broadcast_message(session_cmd)

                    haptic_cmd = self.state_manager.get_haptic_command()
                    if haptic_cmd:
                        await self.broadcast_message(haptic_cmd)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except (RuntimeError, self.websockets.exceptions.WebSocketException) as exc:
                print(f"Error in broadcast loop: {exc}")
                await asyncio.sleep(interval)

    async def start(self) -> None:
        self._running = True
        async with self.websockets.serve(self.handle_client, self.host, self.port):
            print(f"WebSocket server started on ws://{self.host}:{self.port}")
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
            try:
                await asyncio.Future()
            finally:
                self._running = False
                if self._broadcast_task is not None:
                    self._broadcast_task.cancel()
                    try:
                        await self._broadcast_task
                    except asyncio.CancelledError:
                        pass
