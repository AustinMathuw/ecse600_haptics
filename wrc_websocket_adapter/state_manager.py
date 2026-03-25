"""
State manager for WRC telemetry data.

Maintains a shared state dictionary with the current telemetry values
and manages session lifecycle (IDLE, ACTIVE, PAUSED).
"""

from enum import Enum
from typing import Dict, Any, Optional
from id_resolver import get_resolver


class SessionStatus(Enum):
    """Session lifecycle states."""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"


class StateManager:
    """Manages telemetry state and session status."""
    
    def __init__(self):
        """Initialize state manager with default values."""
        self.session_status = SessionStatus.IDLE
        self.state: Dict[str, Any] = {
            # RPM data
            "max_rpm": 0.0,
            "redline_rpm": 0.0,  # Using shiftlights_rpm_end as proxy
            "idle_rpm": 0.0,
            "current_rpm": 0.0,
            
            # Gear data
            "max_gears": 0,
            "current_gear": 0,
            
            # Speed (m/s)
            "speed": 0.0,
            
            # Controls
            "handbrake": 0.0,
            
            # Lap/Stage data
            "current_lap_time": 0.0,
            "track_position_percent": 0.0,
            "track_length": 0.0,
            
            # Track and car info
            "track_name": "Unknown",
            "car_model": "Unknown",
            
            # Internal IDs for tracking
            "_vehicle_id": 0,
            "_location_id": 0,
            "_route_id": 0,
        }
        
        self.id_resolver = get_resolver()
        self._update_count = 0
        
        # Haptic feedback state - continuous mode
        self._last_sent_params = None
        self._pending_haptic_command = None
        self._pending_session_command = None
        
        # Haptic configuration (adjustable)
        self._min_gap = 50        # Gap at redline (ms) - fastest pulses
        self._max_gap = 1000       # Gap at idle (ms) - slowest pulses
        self._vibration_duration = 100  # Fixed vibration duration (ms)
        self._base_intensity = 0.7      # Base intensity (0.0-1.0)
    
    def update_from_session_start(self, packet_data: Dict[str, Any]) -> None:
        """Update state from session_start packet.
        
        Args:
            packet_data: Parsed packet data with channel names as keys
        """
        # RPM data (max and idle set at session start)
        if "vehicle_engine_rpm_max" in packet_data:
            self.state["max_rpm"] = packet_data["vehicle_engine_rpm_max"]
        
        if "vehicle_engine_rpm_idle" in packet_data:
            self.state["idle_rpm"] = packet_data["vehicle_engine_rpm_idle"]
        
        if "shiftlights_rpm_end" in packet_data:
            self.state["redline_rpm"] = packet_data["shiftlights_rpm_end"]
        
        # Gear data
        if "vehicle_gear_maximum" in packet_data:
            self.state["max_gears"] = packet_data["vehicle_gear_maximum"]
        
        # Track length
        if "stage_length" in packet_data:
            self.state["track_length"] = packet_data["stage_length"]
        
        # Store IDs and resolve names
        if "vehicle_id" in packet_data:
            self.state["_vehicle_id"] = packet_data["vehicle_id"]
            self.state["car_model"] = self.id_resolver.get_vehicle_name(
                packet_data["vehicle_id"]
            )
        
        if "location_id" in packet_data and "route_id" in packet_data:
            self.state["_location_id"] = packet_data["location_id"]
            self.state["_route_id"] = packet_data["route_id"]
            self.state["track_name"] = self.id_resolver.get_track_name(
                packet_data["location_id"],
                packet_data["route_id"]
            )
        
        print(f"Session started: {self.state['car_model']} on {self.state['track_name']}")
    
    def update_from_session_update(self, packet_data: Dict[str, Any]) -> None:
        """Update state from session_update packet.
        
        Args:
            packet_data: Parsed packet data with channel names as keys
        """
        # Current RPM
        if "vehicle_engine_rpm_current" in packet_data:
            self.state["current_rpm"] = packet_data["vehicle_engine_rpm_current"]
        
        # Also update max RPM and redline if present (session_update includes them)
        if "vehicle_engine_rpm_max" in packet_data:
            self.state["max_rpm"] = packet_data["vehicle_engine_rpm_max"]
        
        if "vehicle_engine_rpm_idle" in packet_data:
            self.state["idle_rpm"] = packet_data["vehicle_engine_rpm_idle"]
        
        if "shiftlights_rpm_end" in packet_data:
            self.state["redline_rpm"] = packet_data["shiftlights_rpm_end"]
        
        # Current gear
        if "vehicle_gear_index" in packet_data:
            self.state["current_gear"] = packet_data["vehicle_gear_index"]
        
        # Max gears (also in session_update)
        if "vehicle_gear_maximum" in packet_data:
            self.state["max_gears"] = packet_data["vehicle_gear_maximum"]
        
        # Speed (m/s) - using transmission speed for speedometer accuracy
        if "vehicle_transmission_speed" in packet_data:
            self.state["speed"] = packet_data["vehicle_transmission_speed"]
        elif "vehicle_speed" in packet_data:
            self.state["speed"] = packet_data["vehicle_speed"]
        
        # Handbrake (0-1 float)
        if "vehicle_handbrake" in packet_data:
            self.state["handbrake"] = packet_data["vehicle_handbrake"]
        
        # Lap/stage time
        if "stage_current_time" in packet_data:
            self.state["current_lap_time"] = packet_data["stage_current_time"]
        
        # Track position percentage (0-1 during race)
        if "stage_progress" in packet_data:
            self.state["track_position_percent"] = packet_data["stage_progress"]
        
        # Track length (also in session_update)
        if "stage_length" in packet_data:
            self.state["track_length"] = packet_data["stage_length"]
        
        # Update IDs and names if present (session_update includes them)
        if "vehicle_id" in packet_data:
            vehicle_id = packet_data["vehicle_id"]
            if self.state["_vehicle_id"] != vehicle_id:
                self.state["_vehicle_id"] = vehicle_id
                self.state["car_model"] = self.id_resolver.get_vehicle_name(vehicle_id)
        
        if "location_id" in packet_data and "route_id" in packet_data:
            location_id = packet_data["location_id"]
            route_id = packet_data["route_id"]
            if (self.state["_location_id"] != location_id or 
                self.state["_route_id"] != route_id):
                self.state["_location_id"] = location_id
                self.state["_route_id"] = route_id
                self.state["track_name"] = self.id_resolver.get_track_name(
                    location_id, route_id
                )
        
        self._update_count += 1
        
        # Update haptic state based on RPM (continuous mode)
        self._update_haptic_state()
    
    def calculate_rpm_position(self) -> float:
        """Calculate current RPM position between idle and redline.
        
        Returns:
            Float from 0.0 (at/below idle) to 1.0 (at/above redline)
        """
        current = self.state["current_rpm"]
        idle = self.state["idle_rpm"]
        redline = self.state["redline_rpm"]
        
        # No RPM data or invalid range
        if redline <= idle or current <= idle:
            return 0.0
        
        # Calculate position in usable range
        usable_range = redline - idle
        rpm_above_idle = current - idle
        position = rpm_above_idle / usable_range
        
        # Clamp to 0.0-1.0 range
        return max(0.0, min(1.0, position))
    
    def calculate_haptic_parameters(self) -> dict:
        """Calculate haptic parameters based on current RPM.
        
        Uses linear interpolation for gap:
        - At idle (position=0.0): max gap (slow pulses)
        - At redline (position=1.0): min gap (fast pulses)
        
        Returns:
            Dictionary with intensity (0.0-1.0), duration (ms), gap (ms), and mode
        """
        position = self.calculate_rpm_position()
        
        # If below idle, return stop signal
        if position <= 0.0:
            return {
                'intensity': 0.0,
                'duration': 0,
                'gap': 0,
                'mode': 'oneshot'
            }
        
        # Linear interpolation for gap: 
        # gap = max_gap - (max_gap - min_gap) * position
        # As position increases (0→1), gap decreases (max_gap→min_gap)
        gap = int(self._max_gap - (self._max_gap - self._min_gap) * position)
        
        # Optional: Increase intensity as RPM increases
        intensity = 1.0
        
        return {
            'intensity': intensity,
            'duration': self._vibration_duration,
            'gap': gap,
            'mode': 'loop'
        }
    
    def _update_haptic_state(self) -> None:
        """Update haptic state and generate commands when needed."""
        # Only generate haptic feedback when actively racing
        if self.session_status != SessionStatus.ACTIVE:
            return
        
        # Calculate current haptic parameters
        params = self.calculate_haptic_parameters()
        
        # Check if parameters changed significantly
        if self._parameters_changed(params):
            self._pending_haptic_command = self._create_haptic_command(params)
            self._last_sent_params = params.copy()
    
    def _parameters_changed(self, new_params: dict) -> bool:
        """Check if haptic parameters have changed significantly.
        
        Args:
            new_params: New parameters to compare
        
        Returns:
            True if parameters changed enough to warrant update
        """
        if self._last_sent_params is None:
            return True
        
        # Check for significant changes (avoid spam from tiny variations)
        gap_changed = abs(new_params['gap'] - self._last_sent_params.get('gap', 0)) >= 30
        intensity_changed = abs(new_params['intensity'] - self._last_sent_params.get('intensity', 0)) >= 0.05
        mode_changed = new_params['mode'] != self._last_sent_params.get('mode')
        
        return gap_changed or intensity_changed or mode_changed
    
    def _create_haptic_command(self, params: dict) -> dict:
        """Create haptic command message from parameters.
        
        Args:
            params: Haptic parameters with intensity (0.0-1.0), duration, gap, mode
        
        Returns:
            Command dictionary ready for WebSocket transmission
        """
        # Convert intensity from 0.0-1.0 to 0-255
        intensity_255 = int(params['intensity'] * 255)
        
        return {
            'type': 'haptic_event',
            'mode': params['mode'],
            'intensity': intensity_255,
            'duration': params['duration'],
            'gap': params['gap']
        }
    
    def get_haptic_command(self) -> Optional[dict]:
        """Get pending haptic command and clear it.
        
        Returns:
            Haptic command dictionary or None if no command pending
        """
        cmd = self._pending_haptic_command
        self._pending_haptic_command = None
        return cmd
    
    def get_session_command(self) -> Optional[dict]:
        """Get pending session command and clear it.
        
        Returns:
            Session command dictionary or None if no command pending
        """
        cmd = self._pending_session_command
        self._pending_session_command = None
        return cmd
    
    def adjust_haptic_gap_range(self, min_gap: int = 200, max_gap: int = 1000) -> None:
        """Adjust the gap range for haptic feedback.
        
        Args:
            min_gap: Minimum gap at redline (ms)
            max_gap: Maximum gap at idle (ms)
        """
        self._min_gap = min_gap
        self._max_gap = max_gap
        print(f"Haptic gap range adjusted: {min_gap}ms (redline) to {max_gap}ms (idle)")
        
        # Force update on next calculation
        self._last_sent_params = None
    
    def adjust_haptic_duration(self, duration: int = 150) -> None:
        """Adjust vibration duration.
        
        Args:
            duration: Vibration duration (ms)
        """
        self._vibration_duration = duration
        print(f"Haptic duration adjusted: {duration}ms")
        
        # Force update on next calculation
        self._last_sent_params = None
    
    def set_session_status(self, status: SessionStatus) -> None:
        """Set the session status and generate start/stop commands.
        
        Args:
            status: New session status
        """
        if self.session_status != status:
            old_status = self.session_status
            print(f"Session status changed: {old_status.value} → {status.value}")
            self.session_status = status
            
            # Generate session commands for watch
            # Start when transitioning to ACTIVE
            if status == SessionStatus.ACTIVE and old_status != SessionStatus.ACTIVE:
                self._pending_session_command = {
                    'type': 'command',
                    'command': 'start'
                }
                print("Generated start command for haptic session")
            
            # Stop when transitioning away from ACTIVE to IDLE or PAUSED
            elif old_status == SessionStatus.ACTIVE and status != SessionStatus.ACTIVE:
                self._pending_session_command = {
                    'type': 'command',
                    'command': 'stop'
                }
                print("Generated stop command for haptic session")
    
    def get_state(self) -> Dict[str, Any]:
        """Get a copy of the current state.
        
        Returns:
            Dictionary containing all current telemetry values
        """
        # Return copy without internal fields
        return {k: v for k, v in self.state.items() if not k.startswith("_")}
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get complete state including session status.
        
        Returns:
            Dictionary with state and session_status
        """
        return {
            "session_status": self.session_status.value,
            "telemetry": self.get_state()
        }


# Global singleton instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get or create the global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
