# WRC Telemetry to WebSocket Adapter

Receives UDP telemetry from EA SPORTS™ WRC and provides a WebSocket interface for haptic devices (phone/watch).

## Features

- **UDP Telemetry Reception**: Listens on ports 29888 and 29889 for WRC telemetry packets
- **Session Lifecycle Management**: Tracks session start/pause/resume/end events
- **Real-time Telemetry State**: Maintains current values for:
  - RPM data (max, idle, current, redline)
  - Gear data (max gears, current gear)
  - Handbrake state
  - Lap/stage time
  - Track position percentage
  - Track length
  - Track name (location + route)
  - Car model
- **WebSocket Server**: Provides connection infrastructure on ws://0.0.0.0:8080
- **ID Resolution**: Converts numeric vehicle/location/route IDs to readable names

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
uv sync
```

## WRC Game Configuration

To enable telemetry output from EA SPORTS™ WRC:

1. **Launch EA SPORTS WRC**, progress to the first interactive screen (click Start), then quit
2. **Navigate to**: `Documents/My Games/WRC/telemetry/`
3. **Edit config.json** — Set `"bEnabled": true` for these 5 `wrc_haptic_watch` packets:
   - `session_start` (port 29889, frequencyHz: 0)
   - `session_update` (port 29888, frequencyHz: -1)
   - `session_end` (port 29889, frequencyHz: 0)
   - `session_pause` (port 29889, frequencyHz: 0)
   - `session_resume` (port 29889, frequencyHz: 0)
   
   Or copy the provided [wrc_deps/config.json](wrc_deps/config.json) to your WRC telemetry folder
4. **Verify settings**: IP should be `"127.0.0.1"` for localhost
5. **Re-launch EA SPORTS WRC** to reload the configuration
6. **Check log.txt** in the telemetry folder for errors/confirmations

## Usage

### Start the Adapter

```bash
uv run python main.py
```

The adapter will start both:
- UDP servers on ports 29888 (session_update) and 29889 (session events)
- WebSocket server on ws://0.0.0.0:8080

### Connect Haptic Devices

Connect your haptic device (phone/watch) to `ws://<adapter-ip>:8080`

### Test WebSocket Connection

You can test the WebSocket connection using a browser console or wscat:

```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8080');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
ws.send(JSON.stringify({type: 'get_state'}));
```

## Architecture

- **id_resolver.py**: Parses ids.json to resolve vehicle/location/rout using custom wrc_haptic_watch structure
- **websocket_server.py**: Manages WebSocket connections to haptic devices
- **main.py**: Orchestrates all components using asyncio
- **wrc_deps/udp/wrc_haptic_watch.json**: Custom packet structure defining only needed telemetry channels

## Telemetry Data

### Custom Packet Structure

The adapter uses a custom `wrc_haptic_watch` packet structure that includes only the necessary channels for haptic feedback:

- **session_start**: vehicle_engine_rpm_max, vehicle_engine_rpm_idle, shiftlights_rpm_end, vehicle_gear_maximum, stage_length, vehicle_id, location_id, route_id
- **session_update**: vehicle_engine_rpm_current, vehicle_gear_index, vehicle_handbrake, stage_current_time, stage_progress
- **session_start**: vehicle_engine_rpm_max, vehicle_engine_rpm_idle, vehicle_gear_maximum, stage_length, vehicle_id, location_id, route_id
- **session_update**: vehicle_engine_rpm_current, vehicle_gear_index, vehicle_handbrake, stage_current_time, stage_progress, shiftlights_rpm_end

### State Fields

The adapter maintains the following telemetry fields:

```python
{
  "max_rpm": float,              # Maximum engine RPM
  "redline_rpm": float,          # Redline RPM (shiftlights_rpm_end)
  "idle_rpm": float,             # Idle RPM
  "current_rpm": float,          # Current engine RPM
  "max_gears": int,              # Number of forward gears
  "current_gear": int,           # Current gear (0=neutral, negative=reverse)
  "handbrake": float,            # Handbrake position (0-1)
  "current_lap_time": float,     # Current lap/stage time (seconds)
  "track_position_percent": float, # Track progress (0-1)
  "track_length": float,         # Total track length (meters)
  "track_name": str,             # "Location - Route"
  "car_model": str               # Vehicle name
}
```

## Future Enhancements

- Haptic event generation based on telemetry (e.g., gear shifts, collisions)
- WebSocket broadcasting of haptic commands to connected devices
- Configurable haptic profiles based on car/surface/conditions

## Troubleshooting

- **No telemetry received**: Check WRC's `telemetry/log.txt` for errors
- **Port conflicts**: Ensure ports 29888, 29889, and 8080 are not in use
- **Unknown vehicle/track names**: Verify `wrc_deps/readme/ids.json` exists and is up to date
```

### Connect from Flutter app:

1. Find your computer's IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - Mac/Linux: `ifconfig` or `ip addr`

2. In the Flutter app, enter the WebSocket URL:
   ```
   ws://YOUR_COMPUTER_IP:8080
   ```
   Example: `ws://192.168.1.100:8080`

3. Click "Connect" in the Flutter app

4. You should see events arriving every 5 seconds

## Event Format

Each event contains:

```json
{
  "intensity": 150,     // 0-255: vibration strength
  "duration": 250,      // milliseconds: how long to vibrate
  "gap": 100    // milliseconds: gap between vibrations
}
```

## Testing

The server generates random values within these ranges:
- **intensity**: 50-255 (for noticeable feedback)
- **duration**: 100-500ms
- **gap**: 0-200ms

## Logs

The server logs each event sent:

```
[10:30:45] Sent: intensity=200, duration=350ms, gap=150ms
[10:30:50] Sent: intensity=180, duration=200ms, gap=50ms
```

## Stopping the Server

Press `Ctrl+C` to stop the server.
