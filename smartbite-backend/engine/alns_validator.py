"""
ALNS (Adaptive Large Neighborhood Search) Algorithm for route validation.
Checks if a combined route is economically viable and meets delivery constraints.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from models.order_extended import Order, Restaurant, Partner
from models.location import Coordinates
import math


@dataclass
class RouteValidation:
    """Result of route validation."""
    is_valid: bool
    fuel_saved_liters: float
    fuel_saved_percent: float
    max_delay_minutes: int
    total_distance_km: float
    individual_distances: List[float]
    cost_savings: float
    feasibility_score: float  # 0-1, higher is better


class ALNSValidator:
    """
    Adaptive Large Neighborhood Search validator for evaluating combined routes.
    Checks:
    1. Fuel efficiency improvement
    2. No excessive delivery delays
    3. Cost-benefit analysis
    """
    
    # Configuration
    MIN_FUEL_SAVINGS_PERCENT = 10.0  # Minimum 10% fuel savings required
    MAX_DELIVERY_DELAY_MINS = 15  # Max 15 minutes delay acceptable
    DISTANCE_SCALE = 1.0  # 1 unit = 1 km (in our simplified model)
    
    def __init__(self, 
                 min_fuel_savings_percent: float = MIN_FUEL_SAVINGS_PERCENT,
                 max_delay_mins: int = MAX_DELIVERY_DELAY_MINS):
        self.min_fuel_savings_percent = min_fuel_savings_percent
        self.max_delay_mins = max_delay_mins
    
    def calculate_distance_between_locations(self, 
                                           from_coords: Coordinates,
                                           to_coords: Coordinates) -> float:
        """Calculate distance between two coordinates using Haversine formula approximation."""
        # Convert degrees to kilometers (rough approximation for Delhi area)
        # 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 101 km at Delhi's latitude
        lat_diff_km = (to_coords.x - from_coords.x) * 111
        lon_diff_km = (to_coords.y - from_coords.y) * 101
        return math.sqrt(lat_diff_km**2 + lon_diff_km**2)
    
    def estimate_individual_routes_distance(self, 
                                           order1: Order,
                                           order2: Order) -> Tuple[float, float]:
        """
        Estimate distances for individual routes:
        Route1: Restaurant1 -> Customer1
        Route2: Restaurant2 -> Customer2
        """
        # Get coordinates (use location attributes)
        r1_coords = Coordinates(order1.restaurant.location.latitude, 
                               order1.restaurant.location.longitude)
        c1_coords = Coordinates(order1.delivery_location.latitude,
                               order1.delivery_location.longitude)
        r2_coords = Coordinates(order2.restaurant.location.latitude,
                               order2.restaurant.location.longitude)
        c2_coords = Coordinates(order2.delivery_location.latitude,
                               order2.delivery_location.longitude)
        
        distance1 = self.calculate_distance_between_locations(r1_coords, c1_coords)
        distance2 = self.calculate_distance_between_locations(r2_coords, c2_coords)
        
        return distance1, distance2
    
    def estimate_combined_route_distance(self,
                                        order1: Order,
                                        order2: Order) -> float:
        """
        Estimate combined route distance.
        Optimized path: Restaurant1 -> Restaurant2 -> Customer1 -> Customer2
        (or other optimal permutation)
        """
        r1_coords = Coordinates(order1.restaurant.location.latitude,
                               order1.restaurant.location.longitude)
        r2_coords = Coordinates(order2.restaurant.location.latitude,
                               order2.restaurant.location.longitude)
        c1_coords = Coordinates(order1.delivery_location.latitude,
                               order1.delivery_location.longitude)
        c2_coords = Coordinates(order2.delivery_location.latitude,
                               order2.delivery_location.longitude)
        
        # Try multiple route options and pick the shortest
        # Option 1: R1 -> R2 -> C1 -> C2
        route1 = (self.calculate_distance_between_locations(r1_coords, r2_coords) +
                 self.calculate_distance_between_locations(r2_coords, c1_coords) +
                 self.calculate_distance_between_locations(c1_coords, c2_coords))
        
        # Option 2: R1 -> R2 -> C2 -> C1
        route2 = (self.calculate_distance_between_locations(r1_coords, r2_coords) +
                 self.calculate_distance_between_locations(r2_coords, c2_coords) +
                 self.calculate_distance_between_locations(c2_coords, c1_coords))
        
        # Option 3: R1 -> C1 -> R2 -> C2
        route3 = (self.calculate_distance_between_locations(r1_coords, c1_coords) +
                 self.calculate_distance_between_locations(c1_coords, r2_coords) +
                 self.calculate_distance_between_locations(r2_coords, c2_coords))
        
        # Return minimum distance route
        return min(route1, route2, route3)
    
    def validate_combined_route(self, 
                               order1: Order,
                               order2: Order) -> RouteValidation:
        """
        Validate if combining two orders is economically and operationally viable.
        """
        # Calculate fuel consumption
        partner = Partner("temp", "temp", order1.restaurant.location, "motorcycle", 0.05)
        
        ind_dist1, ind_dist2 = self.estimate_individual_routes_distance(order1, order2)
        individual_total = ind_dist1 + ind_dist2
        
        combined_dist = self.estimate_combined_route_distance(order1, order2)
        
        # Fuel calculations
        fuel_consumption = 0.05  # liters per km
        individual_fuel = individual_total * fuel_consumption
        combined_fuel = combined_dist * fuel_consumption
        fuel_saved = individual_fuel - combined_fuel
        fuel_saved_percent = (fuel_saved / individual_fuel * 100) if individual_fuel > 0 else 0
        
        # Delivery delay calculation (simplified)
        # Assume 5 minutes per km traveled
        individual_time = individual_total * 5
        combined_time = combined_dist * 5
        time_increase = combined_time - individual_time
        
        # Cost savings (assuming ₹100 per liter)
        cost_savings = fuel_saved * 100
        
        # Validation checks
        is_valid = (fuel_saved_percent >= self.min_fuel_savings_percent and
                   time_increase <= self.max_delay_mins)
        
        # Feasibility score (0-1, higher is better)
        fuel_score = min(fuel_saved_percent / 30, 1.0)  # 30% or more = perfect score
        delay_score = max(1.0 - (time_increase / self.max_delay_mins), 0.0)
        feasibility_score = (fuel_score * 0.6) + (delay_score * 0.4)
        
        return RouteValidation(
            is_valid=is_valid,
            fuel_saved_liters=fuel_saved,
            fuel_saved_percent=fuel_saved_percent,
            max_delay_minutes=max(0, int(time_increase)),
            total_distance_km=combined_dist,
            individual_distances=[ind_dist1, ind_dist2],
            cost_savings=cost_savings,
            feasibility_score=feasibility_score
        )


@dataclass
class Partner:
    """Simple partner definition for fuel calculations."""
    partner_id: str
    name: str
    current_location: object
    vehicle_type: str
    fuel_consumption: float
