#!/usr/bin/env python3
"""
Interactive WebSocket server for manual haptic event testing.
Allows you to send custom haptic events or use presets.
"""

import asyncio
import json
import websockets
from datetime import datetime


# Preset haptic patterns
PRESETS = {
    "1": {"name": "Gentle", "intensity": 80, "duration": 100, "timeBetween": 0},
    "2": {"name": "Medium", "intensity": 150, "duration": 200, "timeBetween": 50},
    "3": {"name": "Strong", "intensity": 220, "duration": 300, "timeBetween": 100},
    "4": {"name": "Pulse", "intensity": 200, "duration": 100, "timeBetween": 200},
    "5": {"name": "Alert", "intensity": 255, "duration": 500, "timeBetween": 0},
}


class InteractiveServer:
    def __init__(self):
        self.clients = set()
    
    async def register(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        print(f"\n✓ Client connected: {websocket.remote_address}")
        print(f"  Total clients: {len(self.clients)}\n")
    
    async def unregister(self, websocket):
        """Unregister a disconnected client."""
        self.clients.discard(websocket)
        print(f"\n✗ Client disconnected")
        print(f"  Total clients: {len(self.clients)}\n")
    
    async def broadcast(self, event):
        """Send event to all connected clients."""
        if not self.clients:
            print("⚠ No clients connected")
            return
        
        message = json.dumps(event)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"[{timestamp}] Broadcasting haptic event:")
        print(f"  intensity={event['intensity']}, duration={event['duration']}ms, gap={event['timeBetween']}ms")
        print(f"  Sent to {len(self.clients)} client(s)")
        
        # Send to all connected clients
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    async def broadcast_message(self, message_dict):
        """Send a generic message to all connected clients."""
        if not self.clients:
            print("⚠ No clients connected")
            return
        
        message = json.dumps(message_dict)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"[{timestamp}] Broadcasting command:")
        print(f"  {message_dict}")
        print(f"  Sent to {len(self.clients)} client(s)")
        
        # Send to all connected clients
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_client(self, websocket):
        """Handle a client connection."""
        await self.register(websocket)
        try:
            async for message in websocket:
                # Echo back or handle client messages if needed
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def user_input_loop(self):
        """Handle user input for sending events."""
        print("\n" + "="*60)
        print("INTERACTIVE HAPTIC EVENT SERVER")
        print("="*60)
        print("\nPresets:")
        for key, preset in PRESETS.items():
            print(f"  {key}. {preset['name']:10} - intensity:{preset['intensity']:3}, duration:{preset['duration']:3}ms, gap:{preset['timeBetween']:3}ms")
        print("\nCommands:")
        print("  s - Send START command (start session)")
        print("  x - Send STOP command (stop session)")
        print("  c - Send custom haptic event")
        print("  q - Quit server")
        print("="*60 + "\n")
        
        while True:
            await asyncio.sleep(0.1)  # Allow other tasks to run
            
            try:
                # Use run_in_executor to avoid blocking
                loop = asyncio.get_event_loop()
                choice = await loop.run_in_executor(None, input, ">>> ")
                
                if choice.lower() == 'q':
                    print("Shutting down server...")
                    break
                
                if choice.lower() == 's':
                    # Send start command
                    command = {
                        "type": "command",
                        "command": "start"
                    }
                    await self.broadcast_message(command)
                
                elif choice.lower() == 'x':
                    # Send stop command
                    command = {
                        "type": "command",
                        "command": "stop"
                    }
                    await self.broadcast_message(command)
                
                elif choice.lower() == 'c':
                    # Custom event
                    intensity = await loop.run_in_executor(None, input, "Intensity (0-255): ")
                    duration = await loop.run_in_executor(None, input, "Duration (ms): ")
                    time_between = await loop.run_in_executor(None, input, "Time between (ms): ")
                    
                    event = {
                        "intensity": int(intensity),
                        "duration": int(duration),
                        "timeBetween": int(time_between)
                    }
                    await self.broadcast(event)
                
                elif choice in PRESETS:
                    # Preset event
                    preset = PRESETS[choice]
                    event = {
                        "intensity": preset["intensity"],
                        "duration": preset["duration"],
                        "timeBetween": preset["timeBetween"]
                    }
                    await self.broadcast(event)
                
                else:
                    print(f"Unknown command: {choice}")
            
            except (EOFError, KeyboardInterrupt):
                print("\nShutting down server...")
                break
            except ValueError:
                print("Invalid input. Please enter numbers for custom events.")
            except Exception as e:
                print(f"Error: {e}")


async def main():
    """Start the interactive WebSocket server."""
    host = "0.0.0.0"
    port = 8080
    
    server_instance = InteractiveServer()
    
    print(f"Starting WebSocket server on ws://{host}:{port}")
    print("Waiting for clients to connect...\n")
    
    # Start WebSocket server
    async with websockets.serve(server_instance.handle_client, host, port):
        # Run user input loop
        await server_instance.user_input_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
