class HapticEvent {
  final DateTime timestamp;
  final int intensity; // 0-255
  final int duration; // milliseconds
  final int gap; // milliseconds between vibrations
  final String mode; // 'loop' or 'oneshot'

  HapticEvent({
    required this.timestamp,
    required this.intensity,
    required this.duration,
    required this.gap,
    this.mode = 'oneshot',
  }) : assert(intensity >= 0 && intensity <= 255, 'Intensity must be between 0 and 255');

  factory HapticEvent.fromJson(Map<String, dynamic> json) {
    final gap = json['gap'] as int;
    final mode = json['mode'] as String? ?? 'oneshot';
    
    return HapticEvent(
      timestamp: DateTime.now(),
      intensity: json['intensity'] as int,
      duration: json['duration'] as int,
      gap: gap,
      mode: mode,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'intensity': intensity,
      'duration': duration,
      'gap': gap,
      'mode': mode,
    };
  }

  @override
  String toString() {
    return 'HapticEvent(timestamp: $timestamp, intensity: $intensity, duration: ${duration}ms, gap: ${gap}ms, mode: $mode)';
  }
}
