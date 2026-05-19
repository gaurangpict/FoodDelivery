from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from models.location import Location
from models.order import OrderItem


@dataclass
class Customer:
    """Represents a customer placing an order."""
    customer_id: str
    name: str
    location: Location
    phone: str


@dataclass
class Restaurant:
    """Represents a restaurant."""
    restaurant_id: str
    name: str
    location: Location
    avg_prep_time_mins: int = 15


@dataclass
class Partner:
    """Represents a delivery partner."""
    partner_id: str
    name: str
    current_location: Location
    vehicle_type: str = "motorcycle"
    fuel_consumption_per_km: float = 0.05  # liters per km


@dataclass
class Order:
    """Extended Order model with delivery details and location info."""
    order_id: str
    customer: Customer
    restaurant: Restaurant
    items: List[OrderItem]
    delivery_type: str  # "urgent" or "standard"
    created_at: datetime
    order_value: float  # total item value before billing
    urgency_premium: float = 0.0  # value added for urgent delivery
    is_batched: bool = False
    batch_id: Optional[str] = None
    assigned_partner: Optional[Partner] = None
    delivery_location: Optional[Location] = None
    
    def __hash__(self):
        return hash(self.order_id)
    
    def __eq__(self, other):
        if not isinstance(other, Order):
            return False
        return self.order_id == other.order_id
