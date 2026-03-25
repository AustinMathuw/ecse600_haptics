import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import '../models/event.dart';
import '../models/connection_status.dart';
import '../services/websocket_service.dart';
import '../services/watch_service.dart';
import '../services/event_storage.dart';

class AppState extends ChangeNotifier {
  final WebSocketService _webSocketService = WebSocketService();
  final WatchService _watchService = WatchService();
  final EventStorage _eventStorage = EventStorage();
  
  static const platform = MethodChannel('edu.cwru.watch_bridge/foreground_service');

  SessionState _sessionState = SessionState.idle;
  WebSocketConnectionStatus _wsStatus = WebSocketConnectionStatus.disconnected;
  WatchConnectionStatus _watchStatus = WatchConnectionStatus.unpaired;
  String _websocketUrl = 'ws://10.0.1.77:8080';

  SessionState get sessionState => _sessionState;
  WebSocketConnectionStatus get wsStatus => _wsStatus;
  WatchConnectionStatus get watchStatus => _watchStatus;
  List<HapticEvent> get events => _eventStorage.events;
  String get websocketUrl => _websocketUrl;

  AppState() {
    _initialize();
  }

  void _initialize() {
    // Initialize watch service
    _watchService.initialize();

    // Listen to WebSocket status
    _webSocketService.statusStream.listen((status) async {
      final previousStatus = _wsStatus;
      _wsStatus = status;
      
      print('WebSocket status changed: $previousStatus -> $status');
      
      // Start foreground service when connected, stop when disconnected
      if (status == WebSocketConnectionStatus.connected && 
          previousStatus != WebSocketConnectionStatus.connected) {
        print('Starting foreground service...');
        try {
          await platform.invokeMethod('startForegroundService');
          print('Foreground service started successfully');
        } catch (e) {
          print('Error starting foreground service: $e');
        }
      } else if (status == WebSocketConnectionStatus.disconnected && 
                 previousStatus == WebSocketConnectionStatus.connected) {
        print('Stopping foreground service...');
        try {
          await platform.invokeMethod('stopForegroundService');
          print('Foreground service stopped successfully');
        } catch (e) {
          print('Error stopping foreground service: $e');
        }
      }
      
      notifyListeners();
    });

    // Listen to watch status
    _watchService.statusStream.listen((status) {
      _watchStatus = status;
      notifyListeners();
    });

    // Listen to WebSocket events
    _webSocketService.eventStream.listen((event) {
      _eventStorage.addEvent(event);
      
      // Forward event to watch if session is active
      if (_sessionState == SessionState.active) {
        _watchService.sendEvent(event);
      }
      
      notifyListeners();
    });

    // Listen to WebSocket commands
    _webSocketService.commandStream.listen((command) {
      if (command == 'start') {
        startSession();
      } else if (command == 'stop') {
        stopSession();
      }
    });

    // Listen to watch messages (e.g., stop command from watch)
    _watchService.messageStream.listen((command) {
      if (command == 'stop') {
        stopSession();
      }
    });

    // Listen to event storage changes
    _eventStorage.eventsStream.listen((_) {
      notifyListeners();
    });
  }

  void setWebSocketUrl(String url) {
    _websocketUrl = url;
    notifyListeners();
  }

  void connectWebSocket() {
    _webSocketService.connect(_websocketUrl);
  }

  void disconnectWebSocket() {
    _webSocketService.disconnect();
  }

  Future<void> startSession() async {
    if (_sessionState == SessionState.active) return;
    
    _sessionState = SessionState.active;
    await _watchService.sendStartCommand();
    notifyListeners();
  }

  Future<void> stopSession() async {
    if (_sessionState == SessionState.idle) return;
    
    _sessionState = SessionState.stopping;
    notifyListeners();
    
    await _watchService.sendStopCommand();
    
    _sessionState = SessionState.idle;
    notifyListeners();
  }

  void clearEventHistory() {
    _eventStorage.clearEvents();
    notifyListeners();
  }

  @override
  void dispose() {
    // Stop foreground service if WebSocket is connected
    if (_wsStatus == WebSocketConnectionStatus.connected) {
      platform.invokeMethod('stopForegroundService').catchError((e) {
        print('Error stopping foreground service on dispose: $e');
      });
    }
    
    _webSocketService.dispose();
    _watchService.dispose();
    _eventStorage.dispose();
    super.dispose();
  }
}
