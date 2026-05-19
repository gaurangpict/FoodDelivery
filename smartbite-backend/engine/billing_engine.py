from config.billing_config import CONFIG
from engine.fees import calculate_dynamic_fees
from engine.discounts import calculate_total_discount
from models.bill import BillBreakdown


def calculate_packaging(order_items):
    total = sum(CONFIG.packaging_rate * i.price * i.quantity for i in order_items)
    return round(min(total, CONFIG.packaging_cap), 2)


def build_bill(order_items, distance_km, promo, rain_choice, is_batched=False):

    # -------------------------------
    # 🧾 Item total
    # -------------------------------
    item_total = sum(i.subtotal for i in order_items)

    # -------------------------------
    # 🚚 Delivery + Surge (merged internally)
    # -------------------------------
    delivery_fee, surge_fee, demand_level, smart_score = calculate_dynamic_fees(
        distance_km, item_total, is_batched
    )

    # -------------------------------
    # 📦 Packaging
    # -------------------------------
    packaging = calculate_packaging(order_items)

    # -------------------------------
    # 🌧 Rain
    # -------------------------------
    rain_fee, rain_label = CONFIG.rain_fee_map.get(rain_choice, (0, "No Rain"))

    # -------------------------------
    # 👤 User pays only portion of delivery
    # -------------------------------
    user_delivery = round(delivery_fee * CONFIG.delivery_user_share, 2)

    # -------------------------------
    # 💸 Discounts
    # -------------------------------
    total_discount = calculate_total_discount(
        item_total, demand_level, smart_score, surge_fee, promo
    )

    # -------------------------------
    # 🧾 GST
    # -------------------------------
    food_gst = round(CONFIG.food_gst_rate * (item_total + packaging), 2)

    # ❌ NO platform fee
    # ❌ NO separate surge in service base
    service_base = user_delivery + rain_fee
    service_gst = round(CONFIG.service_gst_rate * service_base, 2)

    # -------------------------------
    # 🧮 Final Calculation
    # -------------------------------
    subtotal = item_total + packaging + service_base
    final_total = round(subtotal + food_gst + service_gst - total_discount, 2)

    # -------------------------------
    # 📦 Return Breakdown
    # -------------------------------
    return BillBreakdown(
        order_items=order_items,
        item_total=item_total,
        packaging=packaging,
        delivery_fee=user_delivery,
        surge_fee=surge_fee,  # shown conditionally in UI
        rain_fee=rain_fee,
        rain_label=rain_label,
        food_gst=food_gst,
        service_gst=service_gst,
        total_discount=total_discount,
        final_total=final_total,
        demand_level=demand_level,
        smart_score=smart_score,
    )