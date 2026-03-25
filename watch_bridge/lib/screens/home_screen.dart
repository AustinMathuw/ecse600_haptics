import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/connection_status.dart';
import 'package:intl/intl.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    final appState = Provider.of<AppState>(context, listen: false);
    _urlController = TextEditingController(text: appState.websocketUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Watch Bridge'),
        backgroundColor: Theme.of(context).colorScheme.onPrimary,
      ),
      body: Consumer<AppState>(
        builder: (context, appState, child) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildWebSocketSection(context, appState),
                const SizedBox(height: 24),
                _buildWatchSection(context, appState),
                const SizedBox(height: 24),
                _buildSessionSection(context, appState),
                const SizedBox(height: 24),
                _buildEventHistorySection(context, appState),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildWebSocketSection(BuildContext context, AppState appState) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.cloud),
                const SizedBox(width: 8),
                const Text(
                  'WebSocket Connection',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                _buildStatusChip(appState.wsStatus),
              ],
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(
                labelText: 'WebSocket URL',
                hintText: 'ws://192.168.1.100:8080',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.link),
              ),
              controller: _urlController,
              onChanged: (value) => appState.setWebSocketUrl(value),
              enabled: appState.wsStatus != WebSocketConnectionStatus.connected,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: appState.wsStatus == WebSocketConnectionStatus.connected
                        ? null
                        : () => appState.connectWebSocket(),
                    icon: const Icon(Icons.power),
                    label: const Text('Connect'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: appState.wsStatus == WebSocketConnectionStatus.disconnected
                        ? null
                        : () => appState.disconnectWebSocket(),
                    icon: const Icon(Icons.power_off),
                    label: const Text('Disconnect'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWatchSection(BuildContext context, AppState appState) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.watch),
                const SizedBox(width: 8),
                const Text(
                  'Watch',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                _buildWatchStatusChip(appState.watchStatus),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              _getWatchStatusMessage(appState.watchStatus),
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSessionSection(BuildContext context, AppState appState) {
    final canStart = appState.wsStatus == WebSocketConnectionStatus.connected &&
        appState.watchStatus == WatchConnectionStatus.paired &&
        appState.sessionState == SessionState.idle;
    final canStop = appState.sessionState == SessionState.active;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.radio_button_checked),
                const SizedBox(width: 8),
                const Text(
                  'Haptic Session',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                _buildSessionStatusChip(appState.sessionState),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: canStart ? () => appState.startSession() : null,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Session'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: canStop ? () => appState.stopSession() : null,
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop Session'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            if (!canStart && appState.sessionState == SessionState.idle) ...[
              const SizedBox(height: 12),
              Text(
                _getStartRequirementMessage(appState),
                style: TextStyle(
                  color: Colors.orange[700],
                  fontSize: 13,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEventHistorySection(BuildContext context, AppState appState) {
    final events = appState.events;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.history),
                const SizedBox(width: 8),
                const Text(
                  'Event History',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Text(
                  '${events.length} events',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 14,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: events.isEmpty ? null : () => appState.clearEventHistory(),
                  tooltip: 'Clear history',
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (events.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Text(
                    'No events received yet',
                    style: TextStyle(
                      color: Colors.grey[400],
                      fontSize: 16,
                    ),
                  ),
                ),
              )
            else
              SizedBox(
                height: 300,
                child: ListView.builder(
                  itemCount: events.length,
                  reverse: true,
                  itemBuilder: (context, index) {
                    final event = events[events.length - 1 - index];
                    return ListTile(
                      leading: CircleAvatar(
                        backgroundColor: _getIntensityColor(event.intensity),
                        child: Text(
                          '${event.intensity}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      title: Text(
                        'Duration: ${event.duration}ms, Gap: ${event.gap}ms',
                        style: const TextStyle(fontSize: 14),
                      ),
                      subtitle: Text(
                        DateFormat('HH:mm:ss.SSS').format(event.timestamp),
                        style: const TextStyle(fontSize: 12),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusChip(WebSocketConnectionStatus status) {
    Color color;
    String label;
    
    switch (status) {
      case WebSocketConnectionStatus.connected:
        color = Colors.green;
        label = 'Connected';
        break;
      case WebSocketConnectionStatus.connecting:
        color = Colors.orange;
        label = 'Connecting';
        break;
      case WebSocketConnectionStatus.error:
        color = Colors.red;
        label = 'Error';
        break;
      case WebSocketConnectionStatus.disconnected:
        color = Colors.grey;
        label = 'Disconnected';
        break;
    }
    
    return Chip(
      label: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 12),
      ),
      backgroundColor: color,
      padding: EdgeInsets.zero,
    );
  }

  Widget _buildWatchStatusChip(WatchConnectionStatus status) {
    Color color;
    String label;
    
    switch (status) {
      case WatchConnectionStatus.paired:
        color = Colors.green;
        label = 'Paired';
        break;
      case WatchConnectionStatus.connecting:
        color = Colors.orange;
        label = 'Connecting';
        break;
      case WatchConnectionStatus.error:
        color = Colors.red;
        label = 'Error';
        break;
      case WatchConnectionStatus.unpaired:
        color = Colors.grey;
        label = 'Unpaired';
        break;
    }
    
    return Chip(
      label: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 12),
      ),
      backgroundColor: color,
      padding: EdgeInsets.zero,
    );
  }

  Widget _buildSessionStatusChip(SessionState state) {
    Color color;
    String label;
    
    switch (state) {
      case SessionState.active:
        color = Colors.green;
        label = 'Active';
        break;
      case SessionState.stopping:
        color = Colors.orange;
        label = 'Stopping';
        break;
      case SessionState.idle:
        color = Colors.grey;
        label = 'Idle';
        break;
    }
    
    return Chip(
      label: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 12),
      ),
      backgroundColor: color,
      padding: EdgeInsets.zero,
    );
  }

  String _getWatchStatusMessage(WatchConnectionStatus status) {
    switch (status) {
      case WatchConnectionStatus.paired:
        return 'Watch is connected and ready';
      case WatchConnectionStatus.connecting:
        return 'Connecting to watch...';
      case WatchConnectionStatus.error:
        return 'Error connecting to watch';
      case WatchConnectionStatus.unpaired:
        return 'Please pair your watch in settings';
    }
  }

  String _getStartRequirementMessage(AppState appState) {
    if (appState.wsStatus != WebSocketConnectionStatus.connected) {
      return 'Connect to WebSocket first';
    }
    if (appState.watchStatus != WatchConnectionStatus.paired) {
      return 'Pair watch first';
    }
    return '';
  }

  Color _getIntensityColor(int intensity) {
    if (intensity < 85) {
      return Colors.blue;
    } else if (intensity < 170) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }
}
