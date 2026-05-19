"""
Batch-aware billing engine - Extended billing with batch discounts and fees.
"""

from typing import List, Optional
from models.order import OrderItem
from models.bill import BillBreakdown
from engine.billing_engine import build_bill
from config.billing_config import CONFIG


def calculate_batch_discount(order_value: float, 
                             batch_discount_percent: float) -> float:
    """
    Temporarily disabled batch discounts - returns 0
    """
    return 0.0


def build_batched_bill(order_items: List[OrderItem],
                       distance_km: float,
                       promo: float,
                       rain_choice: int,
                       is_batched: bool = False,
                       batch_discount_percent: float = 0.0) -> BillBreakdown:
    """
    Build bill for an order, accounting for batch discounts.
    
    If is_batched=True and batch_discount_percent > 0:
    - Apply batch discount on top of regular discounts
    - Keep platform fee (no suppression)
    """
    
    # Get base bill using existing engine
    base_bill = build_bill(order_items, distance_km, promo, rain_choice, is_batched)
    
    if not is_batched or batch_discount_percent == 0:
        return base_bill
    
    # Apply additional batch discount
    batch_discount = calculate_batch_discount(base_bill.item_total, batch_discount_percent)
    
    # Total discount = regular discount + batch discount
    total_discount = base_bill.total_discount + batch_discount
    
    # Cap total discount at max fraction
    total_discount = min(total_discount, CONFIG.max_discount_fraction * base_bill.item_total)
    
    # Recalculate final total
    subtotal = base_bill.item_total + base_bill.delivery_fee + base_bill.rain_fee
    final_total = round(subtotal + base_bill.food_gst + base_bill.service_gst - total_discount, 2)
    
    return BillBreakdown(
        order_items=base_bill.order_items,
        item_total=base_bill.item_total,
        packaging=base_bill.packaging,
        delivery_fee=base_bill.delivery_fee,
        surge_fee=base_bill.surge_fee,
        rain_fee=base_bill.rain_fee,
        rain_label=base_bill.rain_label,
        food_gst=base_bill.food_gst,
        service_gst=base_bill.service_gst,
        total_discount=round(total_discount, 2),
        final_total=final_total,
        demand_level=base_bill.demand_level,
        smart_score=base_bill.smart_score,
    )


def apply_platform_fee_for_batch(base_bill: BillBreakdown,
                                platform_extra_fee: float) -> BillBreakdown:
    """
    Apply platform extra fee for batched orders.
    This is added to the platform's revenue.
    """
    # The extra fee doesn't affect customer's bill - it's kept by platform
    # So we return the bill as-is, but in a real system, we'd track this separately
    return base_bill
