"""Reusable telemetry state manager base class for game implementations."""

from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.shared.contracts import GameStateManager, SessionStatus


class BaseStateManager(GameStateManager):
    """Shared haptic/session/csv behavior with game-specific field mapping hooks."""

    _CSV_FIELDS = [
        "timestamp",
        "driver_name",
        "current_rpm",
        "max_rpm",
        "idle_rpm",
        "redline_rpm",
        "downshift_rpm",
        "upshift_rpm",
        "current_gear",
        "max_gears",
        "speed",
        "handbrake",
        "brake",
        "throttle",
        "current_lap_time",
        "track_position_percent",
        "track_length",
        "track_name",
        "car_model",
    ]

    def __init__(self) -> None:
        self.session_status = SessionStatus.IDLE
        self.state: Dict[str, Any] = {
            "max_rpm": 0.0,
            "redline_rpm": 0.0,
            "idle_rpm": 0.0,
            "downshift_rpm": 0.0,
            "upshift_rpm": 0.0,
            "current_rpm": 0.0,
            "max_gears": 0,
            "current_gear": 0,
            "speed": 0.0,
            "handbrake": 0.0,
            "brake": 0.0,
            "throttle": 0.0,
            "current_lap_time": 0.0,
            "track_position_percent": 0.0,
            "track_length": 0.0,
            "track_name": "Unknown",
            "car_model": "Unknown",
        }

        self._update_count = 0
        self._last_sent_params: Optional[dict] = None
        self._pending_haptic_command: Optional[dict] = None
        self._pending_session_command: Optional[dict] = None

        self._csv_file = None
        self._csv_writer = None
        self._csv_path: Optional[Path] = None
        self._driver_name: str = "Default Driver"

        self._min_gap = 50
        self._max_gap = 1000
        self._min_vibration_duration = 100
        self._max_vibration_duration = 200
        self._min_intensity = 0.3
        self._max_intensity = 1.0

    def update_from_session_start(self, packet_data: Dict[str, Any]) -> None:
        self._apply_session_start(packet_data)

    def update_from_session_update(self, packet_data: Dict[str, Any]) -> None:
        self._apply_session_update(packet_data)
        self._update_count += 1
        self._write_csv_row()
        self._update_haptic_state()

    def _apply_session_start(self, packet_data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def _apply_session_update(self, packet_data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def calculate_rpm_position(self) -> float:
        current = float(self.state.get("current_rpm", 0.0))
        idle = float(self.state.get("idle_rpm", 0.0))
        redline = float(self.state.get("redline_rpm", 0.0))

        if redline <= idle or current <= idle:
            return 0.0

        usable_range = redline - idle
        rpm_above_idle = current - idle
        position = rpm_above_idle / usable_range
        return max(0.0, min(1.0, position))

    def calculate_haptic_parameters(self) -> dict:
        downshift_rpm = float(self.state.get("downshift_rpm", 0.0))
        upshift_rpm = float(self.state.get("upshift_rpm", 0.0))
        if downshift_rpm <= 0.0 or upshift_rpm <= 0.0:
            return {
                "intensity": 0.0,
                "duration": 0,
                "gap": 0,
                "mode": "oneshot",
            }

        current_rpm = float(self.state.get("current_rpm", 0.0))
        idle_rpm = float(self.state.get("idle_rpm", 0.0))
        redline_rpm = float(self.state.get("redline_rpm", 0.0))

        if current_rpm < downshift_rpm:
            if downshift_rpm <= idle_rpm:
                return {
                    "intensity": 0.0,
                    "duration": 0,
                    "gap": 0,
                    "mode": "oneshot",
                }

            # Below downshift threshold, increase intensity as we approach downshift rpm
            position = (current_rpm - idle_rpm) / (downshift_rpm - idle_rpm)
            position = max(0.0, min(1.0, position))
            intensity = self._max_intensity + (
                self._min_intensity - self._max_intensity
            ) * (position**2)
            duration = self._min_vibration_duration + int(
                (self._max_vibration_duration - self._min_vibration_duration)
                * (position**2)
            )
            gap = int(self._min_gap + (self._max_gap - self._min_gap) * position)
            return {
                "intensity": intensity,
                "duration": duration,
                "gap": gap,
                "mode": "loop",
            }
        elif current_rpm < upshift_rpm:
            # Between downshift and upshift, constant vibration
            return {
                "intensity": self._min_intensity,
                "duration": self._max_vibration_duration,
                "gap": self._max_gap,
                "mode": "loop",
            }
        else:
            if redline_rpm <= upshift_rpm:
                return {
                    "intensity": self._min_intensity,
                    "duration": self._max_vibration_duration,
                    "gap": self._max_gap,
                    "mode": "loop",
                }

            # Above upshift threshold, increase output as we approach redline rpm.
            position = (current_rpm - upshift_rpm) / (redline_rpm - upshift_rpm)
            position = max(0.0, min(1.0, position))
            intensity = self._min_intensity + (
                self._max_intensity - self._min_intensity
            ) * (position**2)
            duration = self._max_vibration_duration + int(
                (self._min_vibration_duration - self._max_vibration_duration)
                * (position**2)
            )
            gap = int(self._max_gap - (self._max_gap - self._min_gap) * position)
            return {
                "intensity": intensity,
                "duration": duration,
                "gap": gap,
                "mode": "loop",
            }

    def _update_haptic_state(self) -> None:
        if self.session_status != SessionStatus.ACTIVE:
            return

        params = self.calculate_haptic_parameters()
        if self._parameters_changed(params):
            self._pending_haptic_command = self._create_haptic_command(params)
            self._last_sent_params = params.copy()

    def _parameters_changed(self, new_params: dict) -> bool:
        if self._last_sent_params is None:
            return True

        gap_changed = (
            abs(new_params["gap"] - self._last_sent_params.get("gap", 0)) >= 30
        )
        intensity_changed = (
            abs(new_params["intensity"] - self._last_sent_params.get("intensity", 0.0))
            >= 0.05
        )
        mode_changed = new_params["mode"] != self._last_sent_params.get("mode")
        return gap_changed or intensity_changed or mode_changed

    def _create_haptic_command(self, params: dict) -> dict:
        intensity_255 = int(params["intensity"] * 255)
        return {
            "type": "haptic_event",
            "mode": params["mode"],
            "intensity": intensity_255,
            "duration": params["duration"],
            "gap": params["gap"],
        }

    def get_haptic_command(self) -> Optional[dict]:
        cmd = self._pending_haptic_command
        self._pending_haptic_command = None
        return cmd

    def get_session_command(self) -> Optional[dict]:
        cmd = self._pending_session_command
        self._pending_session_command = None
        return cmd

    def set_driver_name(self, name: str) -> None:
        self._driver_name = name
        print(f"Driver name set: {name}")

    def set_session_status(self, status: SessionStatus) -> None:
        if self.session_status == status:
            return

        old_status = self.session_status
        self.session_status = status
        print(f"Session status changed: {old_status.value} -> {status.value}")

        if status == SessionStatus.ACTIVE and old_status == SessionStatus.IDLE:
            self._open_csv_session()

        if status == SessionStatus.IDLE:
            self._close_csv_session()

        if status == SessionStatus.ACTIVE and old_status != SessionStatus.ACTIVE:
            self._pending_session_command = {"type": "command", "command": "start"}
            print("Generated start command for haptic session")
        elif old_status == SessionStatus.ACTIVE and status != SessionStatus.ACTIVE:
            self._pending_session_command = {"type": "command", "command": "stop"}
            print("Generated stop command for haptic session")

    def _open_csv_session(self) -> None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        driver_slug = self._driver_name.strip().lower().replace(" ", "_")
        filename = f"session_{timestamp}_{driver_slug}.csv"
        sessions_dir = Path(__file__).resolve().parent.parent.parent / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        self._csv_path = sessions_dir / filename
        self._csv_file = open(self._csv_path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=self._CSV_FIELDS)
        self._csv_writer.writeheader()
        print(f"CSV logging started: {self._csv_path}")

    def _close_csv_session(self) -> None:
        if self._csv_file is None:
            return

        self._csv_file.flush()
        self._csv_file.close()
        self._csv_file = None
        self._csv_writer = None
        print(f"CSV session saved: {self._csv_path}")

    def _write_csv_row(self) -> None:
        if self._csv_writer is None:
            return

        row = {
            "timestamp": datetime.datetime.now().isoformat(timespec="milliseconds"),
            "driver_name": self._driver_name,
            "current_rpm": self.state["current_rpm"],
            "max_rpm": self.state["max_rpm"],
            "idle_rpm": self.state["idle_rpm"],
            "redline_rpm": self.state["redline_rpm"],
            "downshift_rpm": self.state["downshift_rpm"],
            "upshift_rpm": self.state["upshift_rpm"],
            "current_gear": self.state["current_gear"],
            "max_gears": self.state["max_gears"],
            "speed": self.state["speed"],
            "handbrake": self.state["handbrake"],
            "brake": self.state["brake"],
            "throttle": self.state["throttle"],
            "current_lap_time": self.state["current_lap_time"],
            "track_position_percent": self.state["track_position_percent"],
            "track_length": self.state["track_length"],
            "track_name": self.state["track_name"],
            "car_model": self.state["car_model"],
        }
        self._csv_writer.writerow(row)

    def get_state(self) -> Dict[str, Any]:
        return {k: v for k, v in self.state.items() if not k.startswith("_")}

    def get_full_state(self) -> Dict[str, Any]:
        return {
            "session_status": self.session_status.value,
            "telemetry": self.get_state(),
        }
