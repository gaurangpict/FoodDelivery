

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import NamedTuple



@dataclass(frozen=True)
class BillingConfig:
    """Single source of truth for all tunable billing parameters."""

    # Scoring weights
    score_weight_value: float    = 0.5
    score_weight_distance: float = 0.3
    score_weight_demand: float   = 0.2
    score_distance_epsilon: float = 0.1   # prevents division by zero
    score_value_normaliser: float = 500.0

    # Demand multipliers  {level: T-factor}
    demand_score_multipliers: dict = field(default_factory=lambda: {
        "high":   1.5,
        "medium": 1.2,
        "low":    1.0,
    })

    # Demand window hours  [(start_hour, end_hour, level), ...]
    # "high" = late-night/unusual hours (low supply, surge applies)
    # "medium" = peak meal hours (high volume, efficient batching, no surge)
    demand_windows: tuple = (
        (23, 23, "high"),   # 11pm late night start
        (0,   4, "high"),   # midnight to 4am
        (12, 14, "medium"), # lunch peak
        (19, 22, "medium"), # dinner peak
        (15, 18, "medium"), # afternoon
    )
    demand_default: str = "low"

    # Delivery fee
    delivery_rate_per_km: float = 4.0
    delivery_min: float         = 5.0
    delivery_max: float         = 60.0
    delivery_user_share: float  = 0.5    # customer pays 50 %

    # Value-based delivery multipliers  {(min, max): factor}
    delivery_value_factors: tuple = (
        (0,    200,  0.60),
        (200,  500,  0.85),
        (500,  1000, 1.00),
        (1000, None, 1.20),
    )

    # Smart-score delivery reduction  {threshold: multiplier}
    smart_score_delivery_factors: tuple = (
        (0.7, 0.6),
        (0.5, 0.8),
    )

    # Surge fees  {level: fraction_of_order_value}
    # Surge applies only at unusual/late-night hours, not at peak meal times
    surge_rate: dict = field(default_factory=lambda: {
        "high":   0.04,   # late night: 4% surcharge (low partner supply)
        "medium": 0.0,    # peak hours: no surge (efficient batching)
        "low":    0.0,
    })
    surge_suppressed_above_score: float = 0.7

    # Discounts
    dynamic_discount_rates: dict = field(default_factory=lambda: {
        "low":    0.10,
        "medium": 0.05,
        "high":   0.0,
    })

    smart_discount_tiers: tuple = (
        (1.5, 0.15),
        (0.8, 0.10),
        (0.5, 0.05),
    )
    smart_discount_halving: float  = 0.5   # controlled dampening
    max_discount_fraction: float   = 0.40  # global safety cap

    demand_discount_weights: dict = field(default_factory=lambda: {
        "high":   0.4,
        "medium": 0.7,
        "low":    1.0,
    })

    # Packaging
    packaging_rate: float = 0.0
    packaging_cap: float  = 0.0

    # Platform
    platform_fee: float  = 5.0

    # Rain fees  {level: (fee, label)}
    rain_fee_map: dict = field(default_factory=lambda: {
        0: (0,  "No Rain"),
        1: (10, "Light Rain"),
        2: (20, "Moderate Rain"),
        3: (35, "Heavy Rain"),
    })

    # GST
    food_gst_rate: float    = 0.05
    service_gst_rate: float = 0.18


CONFIG = BillingConfig()




@dataclass
class OrderItem:
    name: str
    price: float
    quantity: int

    @property
    def subtotal(self) -> float:
        return self.price * self.quantity


@dataclass
class BillBreakdown:
    order_items:      list[OrderItem]
    item_total:       float
    packaging:        float
    delivery_fee:     float
    surge_fee:        float
    #platform_fee:     float
    rain_fee:         float
    rain_label:       str
    food_gst:         float
    service_gst:      float
    total_discount:   float
    final_total:      float
    demand_level:     str
    smart_score:      float
    surge_visible_hours: tuple = (23, 2)  


class DynamicFeeResult(NamedTuple):
    delivery_fee:  float
    surge_fee:     float
    demand_level:  str
    smart_score:   float




def get_demand_level(hour: int, cfg: BillingConfig = CONFIG) -> str:
    """Return demand level for a given hour using the configured windows."""
    for start, end, level in cfg.demand_windows:
        if start <= hour <= end:
            return level
    return cfg.demand_default


def compute_smart_score(
    distance_km: float,
    order_value: float,
    demand_level: str,
    cfg: BillingConfig = CONFIG,
) -> float:
    """
    Composite score reflecting order attractiveness.
    Higher → better order for the platform (closer, more valuable, lower demand).
    """
    proximity  = 1.0 / (distance_km + cfg.score_distance_epsilon)
    value_norm = order_value / cfg.score_value_normaliser
    demand_t   = cfg.demand_score_multipliers[demand_level]

    score = (
        cfg.score_weight_value    * value_norm
        + cfg.score_weight_distance * proximity
        + cfg.score_weight_demand   * (1.0 / demand_t)
    )
    return round(score, 3)


def _delivery_value_factor(order_value: float, cfg: BillingConfig = CONFIG) -> float:
    """Look up the delivery multiplier for a given order value."""
    for low, high, factor in cfg.delivery_value_factors:
        if high is None or order_value < high:
            if order_value >= low:
                return factor
    return 1.0


def _smart_delivery_factor(smart_score: float, cfg: BillingConfig = CONFIG) -> float:
    """Return the delivery-reduction multiplier based on smart score thresholds."""
    for threshold, factor in cfg.smart_score_delivery_factors:
        if smart_score > threshold:
            return factor
    return 1.0


def calculate_dynamic_fees(
    distance_km: float,
    order_value: float,
    hour: int | None = None,
    cfg: BillingConfig = CONFIG,
) -> DynamicFeeResult:

    hour = hour if hour is not None else datetime.datetime.now().hour
    demand_level = get_demand_level(hour, cfg)
    smart_score  = compute_smart_score(distance_km, order_value, demand_level, cfg)

    base_delivery   = cfg.delivery_rate_per_km * distance_km
    value_factor    = _delivery_value_factor(order_value, cfg)
    delivery_fee    = base_delivery * value_factor * _smart_delivery_factor(smart_score, cfg)
    delivery_fee    = max(cfg.delivery_min, min(cfg.delivery_max, delivery_fee))

    surge_fee = (
        0.0
        if smart_score > cfg.surge_suppressed_above_score
        else cfg.surge_rate.get(demand_level, 0.0) * order_value
    )

    return DynamicFeeResult(
        delivery_fee  = round(delivery_fee, 2),
        surge_fee     = round(surge_fee,    2),
        demand_level  = demand_level,
        smart_score   = smart_score,
    )


def calculate_packaging(order_items: list[OrderItem], cfg: BillingConfig = CONFIG) -> float:
    """Dynamic packaging cost, capped at the configured maximum."""
    raw = sum(cfg.packaging_rate * item.price * item.quantity for item in order_items)
    return round(min(raw, cfg.packaging_cap), 2)


def calculate_smart_discount(
    order_value: float,
    smart_score: float,
    surge_fee: float,
    cfg: BillingConfig = CONFIG,
) -> float:
    """Return smart discount; suppressed when a surge fee is active."""
    if surge_fee > 0:
        return 0.0
    for threshold, rate in cfg.smart_discount_tiers:
        if smart_score > threshold:
            return rate * order_value
    return 0.0


def apply_demand_weight(
    total_discount: float,
    demand_level: str,
    cfg: BillingConfig = CONFIG,
) -> float:
    """Scale discount by demand level — protect margins during peak hours."""
    return total_discount * cfg.demand_discount_weights[demand_level]


def calculate_total_discount(
    order_value: float,
    demand_level: str,
    smart_score: float,
    surge_fee: float,
    additional_discount: float,
    cfg: BillingConfig = CONFIG,
) -> float:
    """Aggregate all discount sources, apply demand weighting and the global cap."""
    dynamic_discount = cfg.dynamic_discount_rates.get(demand_level, 0.0) * order_value
    smart_discount   = calculate_smart_discount(order_value, smart_score, surge_fee, cfg) * cfg.smart_discount_halving

    raw_discount      = dynamic_discount + smart_discount + additional_discount
    weighted_discount = apply_demand_weight(raw_discount, demand_level, cfg)
    max_discount      = cfg.max_discount_fraction * order_value

    return round(min(weighted_discount, max_discount), 2)


def build_bill(
    order_items: list[OrderItem],
    distance_km: float,
    additional_discount: float,
    rain_choice: int,
    hour: int | None = None,
    cfg: BillingConfig = CONFIG,
) -> BillBreakdown:
    """
    Assemble the full bill.  Pure function — no I/O, fully testable.
    """
    item_total  = sum(item.subtotal for item in order_items)
    fees        = calculate_dynamic_fees(distance_km, item_total, hour, cfg)
    packaging   = calculate_packaging(order_items, cfg)

    rain_fee, rain_label = cfg.rain_fee_map.get(rain_choice, (0, "No Rain"))

    user_delivery = round(fees.delivery_fee * cfg.delivery_user_share, 2)
    total_discount = calculate_total_discount(
        item_total, fees.demand_level, fees.smart_score,
        fees.surge_fee, additional_discount, cfg,
    )

    food_gst    = round(cfg.food_gst_rate    * (item_total + packaging), 2)
    service_base = user_delivery + cfg.platform_fee + rain_fee + fees.surge_fee
    service_gst  = round(cfg.service_gst_rate * service_base, 2)

    subtotal    = item_total + packaging + service_base
    final_total = round(subtotal + food_gst + service_gst - total_discount, 2)

    return BillBreakdown(
        order_items    = order_items,
        item_total     = item_total,
        packaging      = packaging,
        delivery_fee   = user_delivery,
        surge_fee      = fees.surge_fee,
        platform_fee   = cfg.platform_fee,
        rain_fee       = rain_fee,
        rain_label     = rain_label,
        food_gst       = food_gst,
        service_gst    = service_gst,
        total_discount = total_discount,
        final_total    = final_total,
        demand_level   = fees.demand_level,
        smart_score    = fees.smart_score,
    )




def _prompt_items() -> list[OrderItem]:
    n = int(input("Enter number of items: "))
    items = []
    for i in range(n):
        print(f"\nItem {i + 1}:")
        name     = input("  Name: ")
        price    = float(input("  Price: ₹"))
        quantity = int(input("  Quantity: "))
        items.append(OrderItem(name=name, price=price, quantity=quantity))
    return items


def _prompt_rain() -> int:
    print("\nRain Intensity:  1. Light   2. Moderate   3. Heavy   0. None")
    return int(input("Enter rain level (0–3): "))


def _print_bill(bill: BillBreakdown) -> None:
    w = 32
    print("\n" + "=" * w)
    print("      SMARTBITE BILL")
    print("=" * w)

    for item in bill.order_items:
        print(f"  {item.name} x{item.quantity:<3} ₹{item.subtotal:>8.2f}")

    print("-" * w)
    print(f"  {'Item Total':<22} ₹{bill.item_total:>7.2f}")
    print(f"  {'Packaging':<22} ₹{bill.packaging:>7.2f}")
    print(f"  {'Delivery Fee':<22} ₹{bill.delivery_fee:>7.2f}")
    print(f"  {'Surge Fee':<22} ₹{bill.surge_fee:>7.2f}")
    print(f"  {'Platform Fee':<22} ₹{bill.platform_fee:>7.2f}")

    if bill.rain_fee:
        print(f"  {f'Rain Fee ({bill.rain_label})':<22} ₹{bill.rain_fee:>7.2f}")

    print("-" * w)
    print(f"  {'GST on Food (5%)':<22} ₹{bill.food_gst:>7.2f}")
    print(f"  {'GST on Services (18%)':<22} ₹{bill.service_gst:>7.2f}")
    print(f"  {'Discount Applied':<22}-₹{bill.total_discount:>7.2f}")
    print("=" * w)
    print(f"  {'FINAL TOTAL':<22} ₹{bill.final_total:>7.2f}")
    print("=" * w)
    print(f"  Demand : {bill.demand_level.upper()}")
    print(f"  Score  : {bill.smart_score}")
    print("=" * w)


def run_cli() -> None:
    order_items         = _prompt_items()
    distance_km         = float(input("\nDelivery distance (km): "))
    additional_discount = float(input("Promo discount (₹, 0 if none): ") or 0)
    rain_choice         = _prompt_rain()

    bill = build_bill(order_items, distance_km, additional_discount, rain_choice)
    _print_bill(bill)


if __name__ == "__main__":
    run_cli()