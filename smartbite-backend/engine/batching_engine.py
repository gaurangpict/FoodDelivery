"""
Order Batching Engine - Core orchestration for grouping and routing orders.
Manages order pools, partner assignment, and batch creation.
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from models.order_extended import Order, Customer, Restaurant, Partner, Location
from engine.alns_validator import ALNSValidator, RouteValidation
from engine.astar_pathfinder import AStarPathfinder, Coordinates
from engine.billing_engine import build_bill


class DeliveryType(Enum):
    """Enum for delivery types."""
    URGENT = "urgent"
    STANDARD = "standard"


@dataclass
class Batch:
    """Represents a batch of orders to be delivered together."""
    batch_id: str
    orders: List[Order] = field(default_factory=list)
    assigned_partner: Optional[Partner] = None
    route_sequence: List[Order] = field(default_factory=list)
    batch_discount_percent: float = 0.0
    platform_extra_fee: float = 0.0
    fuel_saved_liters: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, assigned, in_transit, completed
    
    def add_order(self, order: Order):
        """Add an order to the batch."""
        self.orders.append(order)
        order.is_batched = True
        order.batch_id = self.batch_id
    
    def get_total_value(self) -> float:
        """Get total order value for the batch."""
        return sum(order.order_value for order in self.orders)


@dataclass
class PooledOrder:
    """Represents an order waiting in the pool."""
    order: Order
    pool_entry_time: datetime
    pool_timeout: timedelta


class OrderBatchingEngine:
    """
    Main batching engine that orchestrates:
    1. Order classification (Urgent vs Standard)
    2. Pool management for standard orders
    3. Order matching and grouping
    4. Route optimization
    5. Discount and fee calculation
    """
    
    # Configuration
    STANDARD_POOL_TIMEOUT_SECS = 60  # seconds to wait in pool
    SAME_AREA_RADIUS_KM = 0.5  # km
    BATCH_DISCOUNT_X_PERCENT = 5.0  # 5% discount per customer
    BATCH_DISCOUNT_Y_PERCENT = 8.0  # 8% discount per customer
    PLATFORM_EXTRA_FEE = 10.0  # ₹10 extra fee for batching
    
    def __init__(self, alns_validator: Optional[ALNSValidator] = None,
                 astar_pathfinder: Optional[AStarPathfinder] = None):
        self.alns_validator = alns_validator or ALNSValidator()
        self.astar_pathfinder = astar_pathfinder or AStarPathfinder()
        
        # Active pools by location/area (not by restaurant, to allow cross-restaurant batching)
        self.order_pools: Dict[str, List[PooledOrder]] = {"main": []}
        
        # Batch history
        self.batches: List[Batch] = []
        self.completed_orders: Set[str] = set()
    
    def classify_order(self, order: Order) -> DeliveryType:
        """Classify order as urgent or standard."""
        if order.delivery_type.lower() == "urgent":
            return DeliveryType.URGENT
        return DeliveryType.STANDARD
    
    def process_urgent_order(self, order: Order, partner: Partner) -> Batch:
        """
        Process urgent order - immediate assignment.
        Route: Restaurant -> Customer
        No discounts, no batching.
        """
        batch = Batch(
            batch_id=str(uuid.uuid4()),
            orders=[order],
            assigned_partner=partner,
            batch_discount_percent=0.0,
            platform_extra_fee=0.0,
            status="assigned"
        )
        batch.route_sequence = [order]
        order.assigned_partner = partner
        order.is_batched = False
        
        self.batches.append(batch)
        return batch
    
    def add_to_standard_pool(self, order: Order) -> None:
        """
        Add standard order to pool for potential batching.
        Orders are pooled centrally to enable cross-restaurant matching.
        """
        pooled = PooledOrder(
            order=order,
            pool_entry_time=datetime.now(),
            pool_timeout=timedelta(seconds=self.STANDARD_POOL_TIMEOUT_SECS)
        )
        
        self.order_pools["main"].append(pooled)
    
    def find_matching_orders(self, order: Order, 
                            restaurant_pool: List[PooledOrder]) -> List[Order]:
        """
        Find matching orders for batching:
        - In same area as order's customer
        - From same or nearby restaurants
        - Not timed out
        """
        matches = []
        current_time = datetime.now()
        
        for pooled in restaurant_pool:
            candidate = pooled.order
            
            # Skip if same order or already batched
            if candidate.order_id == order.order_id or candidate.is_batched:
                continue
            
            # Check if timed out
            time_in_pool = current_time - pooled.pool_entry_time
            if time_in_pool > pooled.pool_timeout:
                continue
            
            # Check if in same area
            if order.delivery_location.is_same_area(
                candidate.delivery_location, 
                self.SAME_AREA_RADIUS_KM
            ):
                matches.append(candidate)
        
        return matches
    
    def try_batch_orders(self, order1: Order, order2: Order) -> Optional[Batch]:
        """
        Attempt to batch two orders.
        Uses ALNS to validate route viability.
        """
        # Validate route using ALNS
        validation = self.alns_validator.validate_combined_route(order1, order2)
        
        if not validation.is_valid:
            return None
        
        # Create batch
        batch = Batch(
            batch_id=str(uuid.uuid4()),
            batch_discount_percent=(self.BATCH_DISCOUNT_X_PERCENT + 
                                   self.BATCH_DISCOUNT_Y_PERCENT) / 2,
            platform_extra_fee=self.PLATFORM_EXTRA_FEE,
            fuel_saved_liters=validation.fuel_saved_liters,
            status="pending"
        )
        
        batch.add_order(order1)
        batch.add_order(order2)
        
        # Set route sequence based on ALNS output
        # Simplified: assume order is Restaurant1 -> Restaurant2 -> Customer1 -> Customer2
        batch.route_sequence = [order1, order2]
        
        return batch
    
    def process_order(self, order: Order, partner: Optional[Partner] = None) -> Batch:
        """
        Main entry point for processing an order.
        Returns the created batch.
        """
        delivery_type = self.classify_order(order)
        
        if delivery_type == DeliveryType.URGENT:
            # Urgent: assign immediately
            if partner is None:
                raise ValueError("Partner must be provided for urgent orders")
            return self.process_urgent_order(order, partner)
        
        else:
            # Standard: attempt to match with existing pooled orders
            main_pool = self.order_pools["main"]
            
            # Check if we can find a matching order from EXISTING pool items
            matches = self.find_matching_orders(order, main_pool)
            
            if matches:
                # Try to batch with first viable match
                for match in matches:
                    batch = self.try_batch_orders(order, match)
                    if batch:
                        # Remove any provisional single-order batches for these orders
                        self.batches = [
                            b for b in self.batches
                            if not (
                                len(b.orders) == 1 and
                                b.orders[0].order_id in [order.order_id, match.order_id]
                            )
                        ]
                        # Remove matched orders from pool
                        self.order_pools["main"] = [
                            p for p in self.order_pools["main"]
                            if p.order.order_id not in [order.order_id, match.order_id]
                        ]
                        self.batches.append(batch)
                        return batch
            
            # If no batch found, add to pool for future matching
            self.add_to_standard_pool(order)
            
            # Create a provisional single-order batch for display while order waits
            batch = Batch(
                batch_id=str(uuid.uuid4()),
                status="pending"
            )
            batch.orders.append(order)
            batch.route_sequence = [order]
            self.batches.append(batch)
            return batch
    
    def assign_partner_to_batch(self, batch: Batch, partner: Partner) -> None:
        """Assign partner to a batch."""
        batch.assigned_partner = partner
        batch.status = "assigned"
        
        for order in batch.orders:
            order.assigned_partner = partner
    
    def optimize_route_with_astar(self, batch: Batch) -> List[Coordinates]:
        """
        Use A* to find the optimal route sequence for the batch.
        """
        if len(batch.orders) == 0:
            return []
        
        # Convert locations to coordinates
        coordinates = []
        
        # START: First restaurant
        first_restaurant = batch.orders[0].restaurant
        start = Coordinates(first_restaurant.location.latitude,
                          first_restaurant.location.longitude)
        coordinates.append(start)
        
        # Add all unique restaurant and customer locations
        seen_locations = set()
        for order in batch.orders:
            r_key = (order.restaurant.location.latitude, 
                    order.restaurant.location.longitude)
            if r_key not in seen_locations:
                coordinates.append(Coordinates(r_key[0], r_key[1]))
                seen_locations.add(r_key)
            
            c_key = (order.delivery_location.latitude,
                    order.delivery_location.longitude)
            if c_key not in seen_locations:
                coordinates.append(Coordinates(c_key[0], c_key[1]))
                seen_locations.add(c_key)
        
        # If only one location, return it
        if len(coordinates) < 2:
            return coordinates
        
        # Find paths between consecutive points
        full_path = []
        for i in range(len(coordinates) - 1):
            segment = self.astar_pathfinder.find_path(
                coordinates[i], 
                coordinates[i + 1]
            )
            if full_path:
                full_path.extend(segment[1:])
            else:
                full_path.extend(segment)
        
        return full_path
    
    def get_batch_summary(self, batch: Batch) -> Dict:
        """Get summary information about a batch."""
        total_value = batch.get_total_value()
        
        return {
            "batch_id": batch.batch_id,
            "order_count": len(batch.orders),
            "orders": [o.order_id for o in batch.orders],
            "status": batch.status,
            "assigned_partner": batch.assigned_partner.partner_id if batch.assigned_partner else None,
            "batch_discount_percent": batch.batch_discount_percent,
            "platform_extra_fee": batch.platform_extra_fee,
            "fuel_saved_liters": batch.fuel_saved_liters,
            "total_order_value": total_value,
            "is_batched": len(batch.orders) > 1,
        }
