from dataclasses import dataclass
from typing import List
from models.order import OrderItem

@dataclass
class BillBreakdown:
    order_items: List[OrderItem]
    item_total: float
    packaging: float
    delivery_fee: float
    surge_fee: float   # now optional display
    rain_fee: float
    rain_label: str
    food_gst: float
    service_gst: float
    total_discount: float
    final_total: float
    demand_level: str
    smart_score: float