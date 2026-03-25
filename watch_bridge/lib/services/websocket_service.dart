import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/event.dart';
import '../models/connection_status.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  String? _url;
  Timer? _reconnectTimer;
  bool _isDisposed = false;

  final StreamController<HapticEvent> _eventController =
      StreamController<HapticEvent>.broadcast();
  final StreamController<String> _commandController =
      StreamController<String>.broadcast();
  final StreamController<WebSocketConnectionStatus> _statusController =
      StreamController<WebSocketConnectionStatus>.broadcast();

  Stream<HapticEvent> get eventStream => _eventController.stream;
  Stream<String> get commandStream => _commandController.stream;
  Stream<WebSocketConnectionStatus> get statusStream =>
      _statusController.stream;

  WebSocketConnectionStatus _currentStatus = WebSocketConnectionStatus.disconnected;
  WebSocketConnectionStatus get currentStatus => _currentStatus;

  void connect(String url) {
    if (_isDisposed) return;
    
    _url = url;
    _updateStatus(WebSocketConnectionStatus.connecting);

    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      
      _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
        cancelOnError: false,
      );

      _updateStatus(WebSocketConnectionStatus.connected);
    } catch (e) {
      _updateStatus(WebSocketConnectionStatus.error);
      _scheduleReconnect();
    }
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _channel?.sink.close();
    _channel = null;
    _url = null;
    _updateStatus(WebSocketConnectionStatus.disconnected);
  }

  void _onMessage(dynamic message) {
    if (_isDisposed) return;

    try {
      final data = jsonDecode(message as String);
      final type = data['type'] as String?;
      
      if (type == 'command') {
        // Handle command messages (start/stop)
        final command = data['command'] as String?;
        if (command != null) {
          print('WebSocket command received: $command');
          _commandController.add(command);
        }
      } else if (type == 'haptic_event') {
        // Handle haptic event messages only
        final event = HapticEvent.fromJson(data);
        _eventController.add(event);
      }
      // Ignore other message types (like telemetry state updates)
    } catch (e) {
      print('Error parsing WebSocket message: $e');
    }
  }

  void _onError(error) {
    if (_isDisposed) return;
    
    print('WebSocket error: $error');
    _updateStatus(WebSocketConnectionStatus.error);
    _scheduleReconnect();
  }

  void _onDone() {
    if (_isDisposed) return;

    print('WebSocket connection closed');
    if (_currentStatus != WebSocketConnectionStatus.disconnected) {
      _updateStatus(WebSocketConnectionStatus.disconnected);
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_isDisposed || _url == null || _reconnectTimer != null) return;

    _reconnectTimer = Timer(const Duration(seconds: 5), () {
      _reconnectTimer = null;
      if (!_isDisposed && _url != null) {
        print('Attempting to reconnect to WebSocket...');
        connect(_url!);
      }
    });
  }

  void _updateStatus(WebSocketConnectionStatus status) {
    _currentStatus = status;
    if (!_statusController.isClosed) {
      _statusController.add(status);
    }
  }

  void dispose() {
    _isDisposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _eventController.close();
    _commandController.close();
    _statusController.close();
  }
}
