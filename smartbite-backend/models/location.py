from dataclasses import dataclass
from typing import Tuple
import math


@dataclass
class Location:
    """Represents a geographic location with latitude and longitude."""
    name: str
    latitude: float
    longitude: float
    
    def distance_to(self, other: 'Location') -> float:
        """
        Calculate Euclidean distance to another location.
        In a real system, this would use a mapping API or haversine formula.
        """
        lat_diff = self.latitude - other.latitude
        lon_diff = self.longitude - other.longitude
        return math.sqrt(lat_diff**2 + lon_diff**2)
    
    def is_same_area(self, other: 'Location', radius_km: float = 0.5) -> bool:
        """Check if another location is within the same area."""
        return self.distance_to(other) <= radius_km


@dataclass
class Coordinates:
    """Simple coordinate pair."""
    x: float
    y: float
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __eq__(self, other):
        if not isinstance(other, Coordinates):
            return False
        return abs(self.x - other.x) < 0.0001 and abs(self.y - other.y) < 0.0001
