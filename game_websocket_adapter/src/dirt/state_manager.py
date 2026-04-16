"""Dirt Rally 2.0 state manager with normalized telemetry mapping."""

from __future__ import annotations

from typing import Any, Dict

from src.shared.base_state_manager import BaseStateManager


class DirtStateManager(BaseStateManager):
    """Maps Dirt Rally 2.0 UDP fields into the shared telemetry schema."""

    RPM_SCALE = 1.0 / 10.0

    def _apply_session_start(self, packet_data: Dict[str, Any]) -> None:
        self._apply_session_update(packet_data)
        print("Dirt session started")

    def _apply_session_update(self, packet_data: Dict[str, Any]) -> None:
        raw_engine_speed = float(packet_data.get("engine_rate", 0.0))
        raw_idle_rpm = float(packet_data.get("idle_rpm", 0.0))
        raw_red_rpm = float(packet_data.get("red_rpm", 0.0))
        raw_max_rpm = float(packet_data.get("max_rpm", 0.0))
        raw_downshift_rpm = float(packet_data.get("downshift_rpm", 0.0))
        raw_upshift_rpm = float(packet_data.get("upshift_rpm", 0.0))

        current_rpm = max(0.0, raw_engine_speed * self.RPM_SCALE)
        idle_rpm = max(0.0, raw_idle_rpm * self.RPM_SCALE)
        red_rpm = max(0.0, raw_red_rpm * self.RPM_SCALE)
        max_rpm = max(0.0, raw_max_rpm * self.RPM_SCALE)
        downshift_rpm = max(0.0, raw_downshift_rpm * self.RPM_SCALE)
        upshift_rpm = max(0.0, raw_upshift_rpm * self.RPM_SCALE)

        self.state["current_rpm"] = current_rpm
        self.state["max_rpm"] = max_rpm
        self.state["idle_rpm"] = idle_rpm
        self.state["redline_rpm"] = red_rpm
        self.state["downshift_rpm"] = downshift_rpm
        self.state["upshift_rpm"] = upshift_rpm

        self.state["current_gear"] = int(round(float(packet_data.get("gear", 0.0))))
        self.state["max_gears"] = int(
            round(float(packet_data.get("max_gear_number", 0.0)))
        )

        speed = float(packet_data.get("speed", 0.0))
        self.state["speed"] = max(0.0, speed)

        self.state["current_lap_time"] = max(
            0.0, float(packet_data.get("lap_time", 0.0))
        )
        self.state["track_length"] = max(0.0, float(packet_data.get("track_size", 0.0)))
        self.state["track_position_percent"] = min(
            1.0, max(0.0, float(packet_data.get("percent_complete", 0.0)))
        )

        self.state["brake"] = float(packet_data.get("brake", 0.0))
        self.state["throttle"] = float(packet_data.get("throttle", 0.0))

        # Not available in this DR2 feed, keep normalized schema values deterministic.
        self.state["handbrake"] = 0.0
        self.state["car_model"] = "DiRT Rally 2.0"
        self.state["track_name"] = "Unknown Dirt Track"


# expotiental: weber function
# Litterally get the mapping

# discreatize:

# 1-2-3- approching

# How fast to approch

# shorten the band

# Could be a P (position) ID ()


# Timing weber fraction
