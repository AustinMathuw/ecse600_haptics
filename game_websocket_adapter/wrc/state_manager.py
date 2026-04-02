"""WRC-specific telemetry state mapping."""

from __future__ import annotations

from typing import Any, Dict

from shared.base_state_manager import BaseStateManager
from shared.contracts import IdentityResolver


class WRCStateManager(BaseStateManager):
    """State manager that maps WRC packet channels into normalized telemetry."""

    def __init__(self, id_resolver: IdentityResolver):
        super().__init__()
        self.id_resolver = id_resolver
        self.state.update(
            {
                "_vehicle_id": 0,
                "_location_id": 0,
                "_route_id": 0,
            }
        )

    def _apply_session_start(self, packet_data: Dict[str, Any]) -> None:
        if "vehicle_engine_rpm_max" in packet_data:
            self.state["max_rpm"] = packet_data["vehicle_engine_rpm_max"]
        if "vehicle_engine_rpm_idle" in packet_data:
            self.state["idle_rpm"] = packet_data["vehicle_engine_rpm_idle"]
        if "shiftlights_rpm_end" in packet_data:
            self.state["redline_rpm"] = packet_data["shiftlights_rpm_end"]
        if "vehicle_gear_maximum" in packet_data:
            self.state["max_gears"] = packet_data["vehicle_gear_maximum"]
        if "stage_length" in packet_data:
            self.state["track_length"] = packet_data["stage_length"]

        if "vehicle_id" in packet_data:
            self.state["_vehicle_id"] = packet_data["vehicle_id"]
            self.state["car_model"] = self.id_resolver.get_vehicle_name(packet_data["vehicle_id"])

        if "location_id" in packet_data and "route_id" in packet_data:
            self.state["_location_id"] = packet_data["location_id"]
            self.state["_route_id"] = packet_data["route_id"]
            self.state["track_name"] = self.id_resolver.get_track_name(
                packet_data["location_id"], packet_data["route_id"]
            )

        print(f"WRC session started: {self.state['car_model']} on {self.state['track_name']}")

    def _apply_session_update(self, packet_data: Dict[str, Any]) -> None:
        if "vehicle_engine_rpm_current" in packet_data:
            self.state["current_rpm"] = packet_data["vehicle_engine_rpm_current"]
        if "vehicle_engine_rpm_max" in packet_data:
            self.state["max_rpm"] = packet_data["vehicle_engine_rpm_max"]
        if "vehicle_engine_rpm_idle" in packet_data:
            self.state["idle_rpm"] = packet_data["vehicle_engine_rpm_idle"]
        if "shiftlights_rpm_end" in packet_data:
            self.state["redline_rpm"] = packet_data["shiftlights_rpm_end"]

        if "vehicle_gear_index" in packet_data:
            self.state["current_gear"] = packet_data["vehicle_gear_index"]
        if "vehicle_gear_maximum" in packet_data:
            self.state["max_gears"] = packet_data["vehicle_gear_maximum"]

        if "vehicle_transmission_speed" in packet_data:
            self.state["speed"] = packet_data["vehicle_transmission_speed"]
        elif "vehicle_speed" in packet_data:
            self.state["speed"] = packet_data["vehicle_speed"]

        if "vehicle_handbrake" in packet_data:
            self.state["handbrake"] = packet_data["vehicle_handbrake"]
        if "stage_current_time" in packet_data:
            self.state["current_lap_time"] = packet_data["stage_current_time"]
        if "stage_progress" in packet_data:
            self.state["track_position_percent"] = packet_data["stage_progress"]
        if "stage_length" in packet_data:
            self.state["track_length"] = packet_data["stage_length"]

        if "vehicle_id" in packet_data:
            vehicle_id = packet_data["vehicle_id"]
            if self.state["_vehicle_id"] != vehicle_id:
                self.state["_vehicle_id"] = vehicle_id
                self.state["car_model"] = self.id_resolver.get_vehicle_name(vehicle_id)

        if "location_id" in packet_data and "route_id" in packet_data:
            location_id = packet_data["location_id"]
            route_id = packet_data["route_id"]
            if self.state["_location_id"] != location_id or self.state["_route_id"] != route_id:
                self.state["_location_id"] = location_id
                self.state["_route_id"] = route_id
                self.state["track_name"] = self.id_resolver.get_track_name(location_id, route_id)
