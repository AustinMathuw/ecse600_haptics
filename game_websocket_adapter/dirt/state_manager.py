"""Dirt Rally 2.0 state manager with normalized telemetry mapping."""

from __future__ import annotations

from typing import Any, Dict

from shared.base_state_manager import BaseStateManager


class DirtStateManager(BaseStateManager):
    """Maps Dirt Rally 2.0 UDP fields into the shared telemetry schema."""

    RPM_SCALE = 10.0
    REDLINE_OFFSET_RPM = 200.0
    IDLE_RPM_RATIO = 0.20

    def _apply_session_start(self, packet_data: Dict[str, Any]) -> None:
        self._apply_session_update(packet_data)
        print("Dirt session started")

    def _apply_session_update(self, packet_data: Dict[str, Any]) -> None:
        raw_engine_speed = float(packet_data.get("engine_speed", 0.0))
        raw_max_rpm = float(packet_data.get("maximum_rpm", 0.0))

        current_rpm = max(0.0, raw_engine_speed * self.RPM_SCALE)
        max_rpm = max(0.0, raw_max_rpm * self.RPM_SCALE)

        if max_rpm > 0:
            idle_rpm = max(500.0, max_rpm * self.IDLE_RPM_RATIO)
            redline_rpm = max(idle_rpm + 100.0, max_rpm - self.REDLINE_OFFSET_RPM)
        else:
            idle_rpm = 0.0
            redline_rpm = 0.0

        self.state["current_rpm"] = current_rpm
        self.state["max_rpm"] = max_rpm
        self.state["idle_rpm"] = idle_rpm
        self.state["redline_rpm"] = redline_rpm

        self.state["current_gear"] = int(round(float(packet_data.get("gear", 0.0))))

        speed = float(packet_data.get("speed", 0.0))
        self.state["speed"] = max(0.0, speed)

        self.state["current_lap_time"] = max(0.0, float(packet_data.get("current_lap_stage_time", 0.0)))
        current_lap_stage_distance = max(0.0, float(packet_data.get("current_lap_stage_distance", 0.0)))
        total_distance = max(0.0, float(packet_data.get("total_distance", 0.0)))

        self.state["track_length"] = total_distance
        if total_distance > 0.0:
            self.state["track_position_percent"] = min(1.0, current_lap_stage_distance / total_distance)
        else:
            self.state["track_position_percent"] = 0.0

        # Not available in this DR2 feed, keep normalized schema values deterministic.
        self.state["handbrake"] = 0.0
        self.state["car_model"] = "DiRT Rally 2.0"
        self.state["track_name"] = "Unknown Dirt Track"

        if self.state["current_gear"] > self.state["max_gears"]:
            self.state["max_gears"] = self.state["current_gear"]
