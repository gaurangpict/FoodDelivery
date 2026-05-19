import datetime
from config.billing_config import CONFIG
from engine.scoring import compute_smart_score

def get_demand_level():
    hour = datetime.datetime.now().hour
    for start, end, level in CONFIG.demand_windows:
        if start <= hour <= end:
            return level
    return CONFIG.demand_default


def calculate_dynamic_fees(distance_km, order_value, is_batched=False):
    """
    Calculate delivery fees with fixed rates for batched vs non-batched orders.
    - Non-batched: Rs 30
    - Batched: Rs 15
    """
    if is_batched:
        delivery_fee = 15.0
    else:
        delivery_fee = 30.0
    
    # For compatibility, still calculate other components but they won't affect the fixed fee
    hour = datetime.datetime.now().hour
    demand_level = get_demand_level()
    
    smart_score = compute_smart_score(distance_km, order_value, demand_level)
    
    # Surge applies only during unusual/late-night hours (23h, 00-04h → demand_level "high").
    # Peak meal hours (lunch/dinner → "medium") and daytime ("low") carry no surge.
    if smart_score > CONFIG.surge_suppressed_above_score:
        surge_fee = 0.0
    else:
        surge_fee = CONFIG.surge_rate[demand_level] * order_value

    return delivery_fee, round(surge_fee, 2), demand_level, smart_score