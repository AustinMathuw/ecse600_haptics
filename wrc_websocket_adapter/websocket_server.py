"""
WebSocket server for haptic device communication.

Manages WebSocket connections to haptic devices (phone/watch).
Provides infrastructure for future haptic event broadcasting.
"""

import asyncio
import json
import websockets
from typing import Set
from websockets.server import WebSocketServerProtocol
from state_manager import get_state_manager


class HapticWebSocketServer:
    """WebSocket server for haptic device connections."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """Initialize WebSocket server.
        
        Args:
            host: Host address to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.state_manager = get_state_manager()
        self._broadcast_task = None
        self._running = False
    
    async def register(self, websocket: WebSocketServerProtocol) -> None:
        """Register a new client connection.
        
        Args:
            websocket: Client WebSocket connection
        """
        self.clients.add(websocket)
        remote = websocket.remote_address
        print(f"Client connected: {remote[0]}:{remote[1]} (total: {len(self.clients)})")
    
    async def unregister(self, websocket: WebSocketServerProtocol) -> None:
        """Unregister a client connection.
        
        Args:
            websocket: Client WebSocket connection
        """
        self.clients.discard(websocket)
        remote = websocket.remote_address
        print(f"Client disconnected: {remote[0]}:{remote[1]} (total: {len(self.clients)})")
    
    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """Handle a client connection.
        
        Args:
            websocket: Client WebSocket connection
        """
        await self.register(websocket)
        
        try:
            # Listen for messages from client
            async for message in websocket:
                # For now, just log received messages
                # Future: Handle client commands/requests
                try:
                    data = json.loads(message)
                    print(f"Received from client: {data}")
                    
                    # Example: Client could request current state
                    if data.get("type") == "get_state":
                        state = self.state_manager.get_full_state()
                        await websocket.send(json.dumps(state))
                
                except json.JSONDecodeError:
                    print(f"Invalid JSON from client: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            pass
        
        finally:
            await self.unregister(websocket)
    
    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients.
        
        Args:
            message: JSON string to broadcast
        """
        if not self.clients:
            return
        
        # Send to all clients, handling failures gracefully
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )
    
    async def broadcast_message(self, message_dict: dict) -> None:
        """Broadcast a dictionary as JSON to all clients.
        
        Args:
            message_dict: Dictionary to serialize and broadcast
        """
        message = json.dumps(message_dict)
        await self.broadcast(message)
    
    async def _broadcast_loop(self) -> None:
        """Periodically broadcast state to all clients at 10Hz."""
        interval = 0.1  # 10Hz = 100ms
        
        while self._running:
            try:
                # Get current state and broadcast to all clients
                if self.clients:
                    # Check for pending session commands (start/stop)
                    session_cmd = self.state_manager.get_session_command()
                    if session_cmd:
                        await self.broadcast_message(session_cmd)
                        print(f"Sent session command: {session_cmd['command']}")
                    
                    # Check for pending haptic commands
                    haptic_cmd = self.state_manager.get_haptic_command()
                    if haptic_cmd:
                        await self.broadcast_message(haptic_cmd)
                        print(f"Sent haptic command: mode={haptic_cmd['mode']}, "
                              f"intensity={haptic_cmd['intensity']}/255, "
                              f"duration={haptic_cmd['duration']}ms, "
                              f"gap={haptic_cmd['gap']}ms")
                
                await asyncio.sleep(interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in broadcast loop: {e}")
                await asyncio.sleep(interval)
    
    async def start(self) -> None:
        """Start the WebSocket server (blocking)."""
        self._running = True
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"WebSocket server started on ws://{self.host}:{self.port}")
            
            # Start broadcast loop
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
            
            try:
                # Keep server running
                await asyncio.Future()  # Run forever
            finally:
                # Clean up broadcast task
                self._running = False
                if self._broadcast_task:
                    self._broadcast_task.cancel()
                    try:
                        await self._broadcast_task
                    except asyncio.CancelledError:
                        pass
