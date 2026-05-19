from config.billing_config import CONFIG

def calculate_smart_discount(order_value, smart_score, surge_fee):
    if surge_fee > 0:
        return 0

    for threshold, rate in CONFIG.smart_discount_tiers:
        if smart_score > threshold:
            return rate * order_value

    return 0


def apply_demand_weight(discount, demand_level):
    return discount * CONFIG.demand_discount_weights[demand_level]


def calculate_total_discount(order_value, demand_level, smart_score, surge_fee, promo):
    """
    Compute demand-aware discount as per SmartBite research paper (Section 3.6, Table II).
    - Dynamic discount: low=10%, medium=5%, high=0%
    - Smart discount: score-tiered, suppressed when surge active
    - Demand weighting: low=1.0, medium=0.7, high=0.4
    - Plus any manual promo discount from user
    - Capped at 40% of order value
    """
    dynamic_discount = CONFIG.dynamic_discount_rates.get(demand_level, 0.0) * order_value
    smart_discount = calculate_smart_discount(order_value, smart_score, surge_fee) * CONFIG.smart_discount_halving

    raw_discount = dynamic_discount + smart_discount + promo
    weighted_discount = apply_demand_weight(raw_discount, demand_level)
    max_discount = CONFIG.max_discount_fraction * order_value

    return round(min(weighted_discount, max_discount), 2)
