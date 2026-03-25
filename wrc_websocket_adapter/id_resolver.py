"""
ID Resolver for WRC telemetry UIDs.

Parses the ids.json file (UTF-16LE encoded) to resolve numeric IDs
to human-readable names for vehicles, locations, and routes.
"""

import json
from pathlib import Path
from typing import Dict, Optional


class IDResolver:
    """Resolves WRC telemetry UIDs to human-readable names."""
    
    def __init__(self, ids_json_path: str = "wrc_deps/readme/ids.json"):
        """Initialize the resolver by loading the ids.json file.
        
        Args:
            ids_json_path: Path to the ids.json file (relative to project root)
        """
        self.vehicles: Dict[int, str] = {}
        self.locations: Dict[int, str] = {}
        self.routes: Dict[int, str] = {}
        
        self._load_ids(ids_json_path)
    
    def _load_ids(self, json_path: str) -> None:
        """Load and parse the ids.json file."""
        try:
            # Construct absolute path relative to this file's directory
            base_path = Path(__file__).parent
            full_path = base_path / json_path
            
            # Read UTF-16 encoded JSON (auto-detects BOM)
            with open(full_path, 'r', encoding='utf-16') as f:
                data = json.load(f)
            
            # Parse vehicles
            if 'vehicles' in data:
                for vehicle in data['vehicles']:
                    self.vehicles[vehicle['id']] = vehicle['name']
            
            # Parse locations
            if 'locations' in data:
                for location in data['locations']:
                    self.locations[location['id']] = location['name']
            
            # Parse routes
            if 'routes' in data:
                for route in data['routes']:
                    self.routes[route['id']] = route['name']
            
            print(f"ID Resolver loaded: {len(self.vehicles)} vehicles, "
                  f"{len(self.locations)} locations, {len(self.routes)} routes")
        
        except FileNotFoundError:
            print(f"Warning: {json_path} not found. ID resolution will return raw IDs.")
        except Exception as e:
            print(f"Error loading {json_path}: {e}. ID resolution will return raw IDs.")
    
    def get_vehicle_name(self, vehicle_id: int) -> str:
        """Get vehicle name from ID.
        
        Args:
            vehicle_id: The vehicle UID from telemetry
            
        Returns:
            Human-readable vehicle name, or "Unknown Vehicle (ID: X)" if not found
        """
        return self.vehicles.get(vehicle_id, f"Unknown Vehicle (ID: {vehicle_id})")
    
    def get_location_name(self, location_id: int) -> str:
        """Get location name from ID.
        
        Args:
            location_id: The location UID from telemetry
            
        Returns:
            Human-readable location name, or "Unknown Location (ID: X)" if not found
        """
        return self.locations.get(location_id, f"Unknown Location (ID: {location_id})")
    
    def get_route_name(self, route_id: int) -> str:
        """Get route name from ID.
        
        Args:
            route_id: The route UID from telemetry
            
        Returns:
            Human-readable route name, or "Unknown Route (ID: X)" if not found
        """
        return self.routes.get(route_id, f"Unknown Route (ID: {route_id})")
    
    def get_track_name(self, location_id: int, route_id: int) -> str:
        """Get combined track name from location and route IDs.
        
        Args:
            location_id: The location UID from telemetry
            route_id: The route UID from telemetry
            
        Returns:
            Combined "Location - Route" string
        """
        location = self.get_location_name(location_id)
        route = self.get_route_name(route_id)
        return f"{location} - {route}"


# Global singleton instance
_resolver: Optional[IDResolver] = None


def get_resolver() -> IDResolver:
    """Get or create the global ID resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = IDResolver()
    return _resolver
