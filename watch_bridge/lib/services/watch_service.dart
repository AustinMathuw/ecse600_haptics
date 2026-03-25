import 'dart:async';
import 'dart:convert';
import 'package:watch_connectivity/watch_connectivity.dart';
import '../models/event.dart';
import '../models/connection_status.dart';

class WatchService {
  final WatchConnectivity _watch = WatchConnectivity();
  
  final StreamController<WatchConnectionStatus> _statusController =
      StreamController<WatchConnectionStatus>.broadcast();
  final StreamController<String> _messageController =
      StreamController<String>.broadcast();

  Stream<WatchConnectionStatus> get statusStream => _statusController.stream;
  Stream<String> get messageStream => _messageController.stream;

  WatchConnectionStatus _currentStatus = WatchConnectionStatus.unpaired;
  WatchConnectionStatus get currentStatus => _currentStatus;

  bool _isInitialized = false;
  Timer? _pairingCheckTimer;

  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      print('Initializing WatchService...');
      
      // Listen to messages from watch (e.g., stop commands)
      _watch.messageStream.listen((message) {
        print('Message received from watch: $message');
        if (message is Map && message.containsKey('command')) {
          _messageController.add(message['command'] as String);
        }
      });

      // Check initial pairing status
      await _checkPairingStatus();
      
      // Poll for pairing status changes periodically
      _pairingCheckTimer = Timer.periodic(const Duration(seconds: 5), (_) {
        _checkPairingStatus();
      });

      _isInitialized = true;
      print('WatchService initialized successfully');
    } catch (e) {
      print('Error initializing watch service: $e');
      _updateStatus(WatchConnectionStatus.error);
    }
  }

  Future<void> _checkPairingStatus() async {
    try {
      final supported = await _watch.isSupported;
      if (!supported) {
        print('Watch connectivity not supported');
        _updateStatus(WatchConnectionStatus.error);
        return;
      }
      
      final isPaired = await _watch.isPaired;
      final isReachable = await _watch.isReachable;
      
      // On Android, isPaired only checks if Wear OS app is installed
      // isReachable is more accurate - it checks if any nodes are connected
      // So prioritize isReachable for Android compatibility
      if (isReachable) {
        _updateStatus(WatchConnectionStatus.paired);
      } else if (!isPaired) {
        _updateStatus(WatchConnectionStatus.unpaired);
      } else {
        // Paired but not reachable
        _updateStatus(WatchConnectionStatus.unpaired);
      }
    } catch (e) {
      print('Error checking pairing status: $e');
      _updateStatus(WatchConnectionStatus.error);
    }
  }

  Future<void> sendEvent(HapticEvent event) async {
    try {
      final data = event.toJson();
      data['type'] = 'event';
      print('Sending event to watch: ${event.mode}, intensity=${event.intensity}, duration=${event.duration}ms, gap=${event.gap}ms');
      await _watch.sendMessage(data);
    } catch (e) {
      print('Error sending event to watch: $e');
    }
  }

  Future<void> sendStartCommand() async {
    try {
      final message = {
        'type': 'command',
        'command': 'start',
        'timestamp': DateTime.now().toIso8601String(),
      };
      print('Sending start command to watch: $message');
      await _watch.sendMessage(message);
      print('Start command sent successfully');
    } catch (e) {
      print('Error sending start command to watch: $e');
    }
  }

  Future<void> sendStopCommand() async {
    try {
      final message = {
        'type': 'command',
        'command': 'stop',
        'timestamp': DateTime.now().toIso8601String(),
      };
      print('Sending stop command to watch: $message');
      await _watch.sendMessage(message);
      print('Stop command sent successfully');
    } catch (e) {
      print('Error sending stop command to watch: $e');
    }
  }

  void _updateStatus(WatchConnectionStatus status) {
    _currentStatus = status;
    if (!_statusController.isClosed) {
      _statusController.add(status);
    }
  }

  void dispose() {
    _pairingCheckTimer?.cancel();
    _statusController.close();
    _messageController.close();
  }
}
