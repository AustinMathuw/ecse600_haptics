"""ID resolver for EA SPORTS WRC telemetry UIDs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.shared.contracts import IdentityResolver


class WRCIDResolver(IdentityResolver):
    """Resolves WRC numeric IDs to human-readable names."""

    def __init__(self, ids_json_path: str = "src/wrc/deps/readme/ids.json"):
        self.vehicles: Dict[int, str] = {}
        self.locations: Dict[int, str] = {}
        self.routes: Dict[int, str] = {}
        self._load_ids(ids_json_path)

    def _load_ids(self, json_path: str) -> None:
        try:
            base_path = Path(__file__).resolve().parent.parent
            full_path = base_path / json_path
            with open(full_path, "r", encoding="utf-16") as f:
                data = json.load(f)

            for vehicle in data.get("vehicles", []):
                self.vehicles[vehicle["id"]] = vehicle["name"]
            for location in data.get("locations", []):
                self.locations[location["id"]] = location["name"]
            for route in data.get("routes", []):
                self.routes[route["id"]] = route["name"]

            print(
                "WRC ID Resolver loaded: "
                f"{len(self.vehicles)} vehicles, {len(self.locations)} locations, {len(self.routes)} routes"
            )
        except FileNotFoundError:
            print(f"Warning: {json_path} not found. ID resolution will return raw IDs.")
        except (
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            print(
                f"Error loading {json_path}: {exc}. ID resolution will return raw IDs."
            )

    def get_vehicle_name(self, vehicle_id: int) -> str:
        return self.vehicles.get(vehicle_id, f"Unknown Vehicle (ID: {vehicle_id})")

    def get_location_name(self, location_id: int) -> str:
        return self.locations.get(location_id, f"Unknown Location (ID: {location_id})")

    def get_route_name(self, route_id: int) -> str:
        return self.routes.get(route_id, f"Unknown Route (ID: {route_id})")

    def get_track_name(self, location_id: int, route_id: int) -> str:
        return (
            f"{self.get_location_name(location_id)} - {self.get_route_name(route_id)}"
        )
