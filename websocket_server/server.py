#!/usr/bin/env python3
"""
WebSocket server that sends haptic event data every 5 seconds.
Sends JSON messages with format: {"intensity": 0-255, "duration": ms, "timeBetween": ms}
"""

import asyncio
import json
import random
import websockets
from datetime import datetime


async def send_haptic_events(websocket):
    """Send haptic events to connected client every 5 seconds."""
    print(f"Client connected: {websocket.remote_address}")
    
    try:
        while True:
            # Generate random haptic parameters
            intensity = random.randint(50, 255)  # 50-255 for noticeable feedback
            duration = random.randint(100, 500)  # 100-500ms
            time_between = random.randint(0, 200)  # 0-200ms gap
            
            event = {
                "intensity": intensity,
                "duration": duration,
                "timeBetween": time_between
            }
            
            # Send the event
            message = json.dumps(event)
            await websocket.send(message)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Sent: intensity={intensity}, duration={duration}ms, gap={time_between}ms")
            
            # Wait 5 seconds before sending next event
            await asyncio.sleep(5)
            
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Start the WebSocket server."""
    host = "0.0.0.0"  # Listen on all interfaces
    port = 8080
    
    print(f"Starting WebSocket server on ws://{host}:{port}")
    print("Waiting for clients to connect...")
    print("Press Ctrl+C to stop\n")
    
    async with websockets.serve(send_haptic_events, host, port):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
