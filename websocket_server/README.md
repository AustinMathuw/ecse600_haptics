# WebSocket Haptic Event Server

WebSocket servers for testing the Watch Bridge Flutter app with two modes:
- **Automatic mode** (`server.py`): Sends random events every 5 seconds
- **Interactive mode** (`interactive_server.py`): Send custom events on demand

## Features

- Event format: `{"intensity": 0-255, "duration": ms, "timeBetween": ms}`
- Runs on `ws://0.0.0.0:8080` (accessible from any device on your network)
- Interactive mode includes 5 presets for quick testing

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Dependencies are already configured in pyproject.toml
uv sync
```

## Usage

### Automatic Mode (sends events every 5 seconds):

```bash
uv run server.py
```

### Interactive Mode (send custom events):

```bash
uv run interactive_server.py
```

Available commands in interactive mode:
- **1**: Gentle (intensity: 80, duration: 100ms, gap: 0ms)
- **2**: Medium (intensity: 150, duration: 200ms, gap: 50ms)
- **3**: Strong (intensity: 220, duration: 300ms, gap: 100ms)
- **4**: Pulse (intensity: 200, duration: 100ms, gap: 200ms)
- **5**: Alert (intensity: 255, duration: 500ms, gap: 0ms)
- **c**: Custom event (enter your own parameters)
- **q**: Quit

Or run with Python directly:

```bash
uv run python server.py
# or
uv run python interactive_server.py
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
  "timeBetween": 100    // milliseconds: gap between vibrations
}
```

## Testing

The server generates random values within these ranges:
- **intensity**: 50-255 (for noticeable feedback)
- **duration**: 100-500ms
- **timeBetween**: 0-200ms

## Logs

The server logs each event sent:

```
[10:30:45] Sent: intensity=200, duration=350ms, gap=150ms
[10:30:50] Sent: intensity=180, duration=200ms, gap=50ms
```

## Stopping the Server

Press `Ctrl+C` to stop the server.
