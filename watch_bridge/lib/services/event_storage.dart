import 'dart:async';
import '../models/event.dart';

class EventStorage {
  final List<HapticEvent> _events = [];
  final StreamController<List<HapticEvent>> _eventsController =
      StreamController<List<HapticEvent>>.broadcast();

  Stream<List<HapticEvent>> get eventsStream => _eventsController.stream;
  List<HapticEvent> get events => List.unmodifiable(_events);

  void addEvent(HapticEvent event) {
    _events.add(event);
    _notifyListeners();
  }

  void clearEvents() {
    _events.clear();
    _notifyListeners();
  }

  int get eventCount => _events.length;

  void _notifyListeners() {
    if (!_eventsController.isClosed) {
      _eventsController.add(List.unmodifiable(_events));
    }
  }

  void dispose() {
    _eventsController.close();
  }
}
