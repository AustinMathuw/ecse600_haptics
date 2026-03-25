class HapticEvent {
  final DateTime timestamp;
  final int intensity; // 0-255
  final int duration; // milliseconds
  final int timeBetween; // milliseconds between vibrations

  HapticEvent({
    required this.timestamp,
    required this.intensity,
    required this.duration,
    required this.timeBetween,
  }) : assert(intensity >= 0 && intensity <= 255, 'Intensity must be between 0 and 255');

  factory HapticEvent.fromJson(Map<String, dynamic> json) {
    return HapticEvent(
      timestamp: DateTime.now(),
      intensity: json['intensity'] as int,
      duration: json['duration'] as int,
      timeBetween: json['timeBetween'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'intensity': intensity,
      'duration': duration,
      'timeBetween': timeBetween,
    };
  }

  @override
  String toString() {
    return 'HapticEvent(timestamp: $timestamp, intensity: $intensity, duration: ${duration}ms, timeBetween: ${timeBetween}ms)';
  }
}
