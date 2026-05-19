"""
SmartBite Web Application — Modern UI Prototype
Flask-based frontend that integrates with the existing billing & batching engine.
"""

import sys
import os
import uuid
from datetime import datetime

# Add parent directory so we can import existing engine modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from models.order import OrderItem
from engine.billing_engine import build_bill

import math
import threading
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "smartbite-prototype-key-2026"

# ─────────────────────────────────────────────
# Global Order Pool — shared across all users for ALNS batching demo
# ─────────────────────────────────────────────

ORDER_POOL = []           # list of pooled order dicts
BATCH_HISTORY = []        # completed batch results
POOL_LOCK = threading.Lock()
POOL_TIMEOUT_SECS = 120   # orders expire from pool after 2 min (prototype)
AREA_RADIUS_KM = 0.5      # ALNS spatial threshold
MIN_FUEL_SAVINGS_PCT = 10  # minimum fuel savings to approve batch


def haversine_km(lat1, lon1, lat2, lon2):
    """Haversine distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def alns_validate(order1, order2):
    """Run ALNS validation on two orders. Returns dict with results."""
    r1 = order1["restaurant_loc"]
    c1 = order1["delivery_loc"]
    r2 = order2["restaurant_loc"]
    c2 = order2["delivery_loc"]

    # Individual route distances
    d1 = haversine_km(r1[0], r1[1], c1[0], c1[1])
    d2 = haversine_km(r2[0], r2[1], c2[0], c2[1])
    individual_total = d1 + d2

    # Combined route — test 3 permutations, pick shortest
    route_a = haversine_km(r1[0],r1[1],r2[0],r2[1]) + haversine_km(r2[0],r2[1],c1[0],c1[1]) + haversine_km(c1[0],c1[1],c2[0],c2[1])
    route_b = haversine_km(r1[0],r1[1],r2[0],r2[1]) + haversine_km(r2[0],r2[1],c2[0],c2[1]) + haversine_km(c2[0],c2[1],c1[0],c1[1])
    route_c = haversine_km(r1[0],r1[1],c1[0],c1[1]) + haversine_km(c1[0],c1[1],r2[0],r2[1]) + haversine_km(r2[0],r2[1],c2[0],c2[1])
    combined = min(route_a, route_b, route_c)

    fuel_saved_pct = ((individual_total - combined) / individual_total * 100) if individual_total > 0 else 0
    time_increase = max(0, (combined - individual_total) * 5)  # 5 min/km
    fuel_score = min(fuel_saved_pct / 30, 1.0)
    delay_score = max(1.0 - time_increase / 15, 0.0)
    feasibility = 0.6 * fuel_score + 0.4 * delay_score
    is_valid = fuel_saved_pct >= MIN_FUEL_SAVINGS_PCT and time_increase <= 15

    return {
        "is_valid": is_valid,
        "fuel_saved_pct": round(fuel_saved_pct, 1),
        "fuel_saved_liters": round((individual_total - combined) * 0.05, 4),
        "distance_saved_km": round(individual_total - combined, 2),
        "individual_km": round(individual_total, 2),
        "combined_km": round(combined, 2),
        "time_increase_min": round(time_increase, 1),
        "feasibility_score": round(feasibility, 2),
    }


def try_match_in_pool(new_order):
    """Check pool for a compatible order and run ALNS. Returns (matched_order, alns_result) or (None, None)."""
    now = datetime.now()
    with POOL_LOCK:
        # Clean expired entries
        ORDER_POOL[:] = [o for o in ORDER_POOL if (now - o["timestamp"]).total_seconds() < POOL_TIMEOUT_SECS and o["status"] == "waiting"]

        for pooled in ORDER_POOL:
            # Check spatial proximity (delivery locations)
            dist = haversine_km(
                new_order["delivery_loc"][0], new_order["delivery_loc"][1],
                pooled["delivery_loc"][0], pooled["delivery_loc"][1]
            )
            if dist > AREA_RADIUS_KM:
                continue

            # Run ALNS
            result = alns_validate(new_order, pooled)
            if result["is_valid"]:
                pooled["status"] = "batched"
                return pooled, result

    return None, None

# ─────────────────────────────────────────────
# Sample Data — Restaurants & Menus
# ─────────────────────────────────────────────

RESTAURANTS = {
    "r1": {
        "id": "r1",
        "name": "Pizzeria Downtown",
        "cuisine": "Italian",
        "rating": 4.5,
        "delivery_time": "25-35 min",
        "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&h=400&fit=crop",
        "location": {"lat": 18.5196, "lon": 73.8553},  # FC Road, Pune
        "menu": [
            {"id": "r1_1", "name": "Margherita Pizza", "price": 350, "desc": "Classic cheese & basil", "category": "Pizza", "image": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=200&h=200&fit=crop", "veg": True},
            {"id": "r1_2", "name": "Pepperoni Pizza", "price": 450, "desc": "Loaded with pepperoni", "category": "Pizza", "image": "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=200&h=200&fit=crop", "veg": False},
            {"id": "r1_3", "name": "Garlic Bread", "price": 150, "desc": "Crispy with butter & garlic", "category": "Sides", "image": "https://images.unsplash.com/photo-1619535860434-ba1d8fa12536?w=200&h=200&fit=crop", "veg": True},
            {"id": "r1_4", "name": "Pasta Alfredo", "price": 320, "desc": "Creamy white sauce pasta", "category": "Pasta", "image": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=200&h=200&fit=crop", "veg": True},
            {"id": "r1_5", "name": "Coke 500ml", "price": 60, "desc": "Chilled Coca-Cola", "category": "Drinks", "image": "https://images.unsplash.com/photo-1554866585-cd94860890b7?w=200&h=200&fit=crop", "veg": True},
            {"id": "r1_6", "name": "Tiramisu", "price": 220, "desc": "Classic Italian dessert", "category": "Desserts", "image": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=200&h=200&fit=crop", "veg": True},
        ],
    },
    "r2": {
        "id": "r2",
        "name": "Burger House",
        "cuisine": "American",
        "rating": 4.3,
        "delivery_time": "20-30 min",
        "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&h=400&fit=crop",
        "location": {"lat": 18.5362, "lon": 73.8950},  # Kalyani Nagar, Pune
        "menu": [
            {"id": "r2_1", "name": "Classic Burger", "price": 280, "desc": "Beef patty, lettuce, tomato", "category": "Burgers", "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=200&h=200&fit=crop", "veg": False},
            {"id": "r2_2", "name": "Veggie Burger", "price": 250, "desc": "Crispy aloo tikki patty", "category": "Burgers", "image": "https://images.unsplash.com/photo-1520072959219-c595e6cdc07a?w=200&h=200&fit=crop", "veg": True},
            {"id": "r2_3", "name": "Cheese Fries", "price": 180, "desc": "Loaded with melted cheese", "category": "Sides", "image": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=200&h=200&fit=crop", "veg": True},
            {"id": "r2_4", "name": "Chicken Wings", "price": 320, "desc": "Spicy buffalo wings (6 pcs)", "category": "Sides", "image": "https://images.unsplash.com/photo-1608039829572-9b0189c512c3?w=200&h=200&fit=crop", "veg": False},
            {"id": "r2_5", "name": "Milkshake", "price": 150, "desc": "Creamy chocolate milkshake", "category": "Drinks", "image": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=200&h=200&fit=crop", "veg": True},
            {"id": "r2_6", "name": "Onion Rings", "price": 140, "desc": "Golden crispy onion rings", "category": "Sides", "image": "https://images.unsplash.com/photo-1639024471283-03518883512d?w=200&h=200&fit=crop", "veg": True},
        ],
    },
    "r3": {
        "id": "r3",
        "name": "Biryani Palace",
        "cuisine": "Indian",
        "rating": 4.7,
        "delivery_time": "30-40 min",
        "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=400&fit=crop",
        "location": {"lat": 18.5074, "lon": 73.8077},  # Deccan, Pune
        "menu": [
            {"id": "r3_1", "name": "Chicken Biryani", "price": 350, "desc": "Hyderabadi dum biryani", "category": "Biryani", "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=200&h=200&fit=crop", "veg": False},
            {"id": "r3_2", "name": "Veg Biryani", "price": 280, "desc": "Aromatic vegetable biryani", "category": "Biryani", "image": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=200&h=200&fit=crop", "veg": True},
            {"id": "r3_3", "name": "Butter Chicken", "price": 380, "desc": "Rich creamy tomato gravy", "category": "Curries", "image": "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=200&h=200&fit=crop", "veg": False},
            {"id": "r3_4", "name": "Paneer Tikka", "price": 300, "desc": "Tandoori spiced paneer", "category": "Starters", "image": "https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=200&h=200&fit=crop", "veg": True},
            {"id": "r3_5", "name": "Naan (2 pcs)", "price": 80, "desc": "Soft butter naan", "category": "Breads", "image": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=200&h=200&fit=crop", "veg": True},
            {"id": "r3_6", "name": "Raita", "price": 60, "desc": "Cool yogurt with cucumber", "category": "Sides", "image": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=200&h=200&fit=crop", "veg": True},
            {"id": "r3_7", "name": "Gulab Jamun (2)", "price": 100, "desc": "Sweet milk dumplings", "category": "Desserts", "image": "https://images.unsplash.com/photo-1666190410093-4a5e7e036ea1?w=200&h=200&fit=crop", "veg": True},
        ],
    },
    "r4": {
        "id": "r4",
        "name": "Sushi Express",
        "cuisine": "Japanese",
        "rating": 4.6,
        "delivery_time": "35-45 min",
        "image": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600&h=400&fit=crop",
        "location": {"lat": 18.5590, "lon": 73.9146},  # Viman Nagar, Pune
        "menu": [
            {"id": "r4_1", "name": "Salmon Sushi Roll", "price": 480, "desc": "Fresh salmon, 8 pieces", "category": "Sushi", "image": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=200&h=200&fit=crop", "veg": False},
            {"id": "r4_2", "name": "Veg Tempura Roll", "price": 350, "desc": "Crispy veggie roll, 6 pieces", "category": "Sushi", "image": "https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?w=200&h=200&fit=crop", "veg": True},
            {"id": "r4_3", "name": "Miso Soup", "price": 180, "desc": "Traditional Japanese soup", "category": "Soups", "image": "https://images.unsplash.com/photo-1607301405390-d831c242f59b?w=200&h=200&fit=crop", "veg": True},
            {"id": "r4_4", "name": "Edamame", "price": 160, "desc": "Steamed & salted soybeans", "category": "Starters", "image": "https://images.unsplash.com/photo-1564834724105-918b73d1b8e0?w=200&h=200&fit=crop", "veg": True},
            {"id": "r4_5", "name": "Teriyaki Chicken", "price": 420, "desc": "Glazed chicken with rice", "category": "Mains", "image": "https://images.unsplash.com/photo-1569058242567-93de6f36f8e6?w=200&h=200&fit=crop", "veg": False},
            {"id": "r4_6", "name": "Green Tea", "price": 120, "desc": "Authentic Japanese matcha", "category": "Drinks", "image": "https://images.unsplash.com/photo-1556881286-fc6915169721?w=200&h=200&fit=crop", "veg": True},
        ],
    },
    "r5": {
        "id": "r5",
        "name": "Dragon Wok",
        "cuisine": "Chinese",
        "rating": 4.2,
        "delivery_time": "25-35 min",
        "image": "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&h=400&fit=crop",
        "location": {"lat": 18.5308, "lon": 73.8474},  # Shivajinagar, Pune
        "menu": [
            {"id": "r5_1", "name": "Veg Hakka Noodles", "price": 220, "desc": "Stir-fried noodles with veggies", "category": "Noodles", "image": "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=200&h=200&fit=crop", "veg": True},
            {"id": "r5_2", "name": "Chicken Manchurian", "price": 300, "desc": "Indo-Chinese gravy", "category": "Mains", "image": "https://images.unsplash.com/photo-1525755662778-989d0524087e?w=200&h=200&fit=crop", "veg": False},
            {"id": "r5_3", "name": "Spring Rolls (4)", "price": 180, "desc": "Crispy vegetable rolls", "category": "Starters", "image": "https://images.unsplash.com/photo-1606525437817-0fd2beb3ca60?w=200&h=200&fit=crop", "veg": True},
            {"id": "r5_4", "name": "Fried Rice", "price": 240, "desc": "Veg Schezwan fried rice", "category": "Rice", "image": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=200&h=200&fit=crop", "veg": True},
            {"id": "r5_5", "name": "Chilli Paneer", "price": 280, "desc": "Spicy paneer in chilli sauce", "category": "Starters", "image": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=200&h=200&fit=crop", "veg": True},
            {"id": "r5_6", "name": "Sweet Corn Soup", "price": 150, "desc": "Thick creamy corn soup", "category": "Soups", "image": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=200&h=200&fit=crop", "veg": True},
        ],
    },
    "r6": {
        "id": "r6",
        "name": "Dosa Corner",
        "cuisine": "South Indian",
        "rating": 4.4,
        "delivery_time": "20-30 min",
        "image": "https://images.unsplash.com/photo-1668236543090-82eb5eaf35ee?w=600&h=400&fit=crop",
        "location": {"lat": 18.4623, "lon": 73.8672},  # Sinhagad Road, Pune
        "menu": [
            {"id": "r6_1", "name": "Masala Dosa", "price": 150, "desc": "Crispy dosa with potato filling", "category": "Dosa", "image": "https://images.unsplash.com/photo-1668236543090-82eb5eaf35ee?w=200&h=200&fit=crop", "veg": True},
            {"id": "r6_2", "name": "Idli Sambhar (3)", "price": 120, "desc": "Soft idlis with sambhar & chutney", "category": "Breakfast", "image": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=200&h=200&fit=crop", "veg": True},
            {"id": "r6_3", "name": "Uttapam", "price": 160, "desc": "Thick pancake with toppings", "category": "Dosa", "image": "https://images.unsplash.com/photo-1630383249896-424e482df921?w=200&h=200&fit=crop", "veg": True},
            {"id": "r6_4", "name": "Vada (2)", "price": 100, "desc": "Crispy lentil fritters", "category": "Snacks", "image": "https://images.unsplash.com/photo-1626132647523-66f5bf380027?w=200&h=200&fit=crop", "veg": True},
            {"id": "r6_5", "name": "Filter Coffee", "price": 80, "desc": "South Indian drip coffee", "category": "Drinks", "image": "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=200&h=200&fit=crop", "veg": True},
            {"id": "r6_6", "name": "Rava Dosa", "price": 170, "desc": "Thin crispy semolina dosa", "category": "Dosa", "image": "https://images.unsplash.com/photo-1645177628172-a94c1f96e6db?w=200&h=200&fit=crop", "veg": True},
        ],
    },
}


# ─────────────────────────────────────────────
# Helper — get / update session cart
# ─────────────────────────────────────────────

def get_cart():
    """Return the current cart from session."""
    if "cart" not in session:
        session["cart"] = {}
    return session["cart"]


def get_cart_count():
    """Total item count in cart."""
    cart = get_cart()
    return sum(item["qty"] for item in cart.values())


def get_cart_restaurant():
    """Return the restaurant id of items currently in the cart, or None."""
    cart = get_cart()
    if not cart:
        return None
    first_item_id = next(iter(cart))
    return cart[first_item_id].get("restaurant_id")


@app.context_processor
def inject_cart_count():
    """Make cart_count available in all templates."""
    return {"cart_count": get_cart_count()}


# ─────────────────────────────────────────────
# Routes — Pages
# ─────────────────────────────────────────────

@app.route("/")
def home():
    featured = list(RESTAURANTS.values())[:3]
    return render_template("index.html", featured=featured)


@app.route("/restaurants")
def restaurants():
    cuisine_filter = request.args.get("cuisine", "all")
    search_query = request.args.get("q", "").strip().lower()

    filtered = list(RESTAURANTS.values())

    if cuisine_filter != "all":
        filtered = [r for r in filtered if r["cuisine"].lower() == cuisine_filter.lower()]

    if search_query:
        filtered = [
            r for r in filtered
            if search_query in r["name"].lower() or search_query in r["cuisine"].lower()
        ]

    cuisines = sorted(set(r["cuisine"] for r in RESTAURANTS.values()))
    all_restaurants = list(RESTAURANTS.values())  # for map markers
    return render_template(
        "restaurants.html",
        restaurants=filtered,
        all_restaurants=all_restaurants,
        cuisines=cuisines,
        current_cuisine=cuisine_filter,
        search_query=request.args.get("q", ""),
    )


@app.route("/restaurant/<restaurant_id>")
def menu(restaurant_id):
    restaurant = RESTAURANTS.get(restaurant_id)
    if not restaurant:
        return redirect(url_for("restaurants"))

    categories = sorted(set(item["category"] for item in restaurant["menu"]))
    cart_restaurant = get_cart_restaurant()
    return render_template(
        "menu.html",
        restaurant=restaurant,
        categories=categories,
        cart_restaurant=cart_restaurant,
    )


@app.route("/cart")
def cart():
    cart_data = get_cart()
    items = []
    subtotal = 0

    restaurant_id = get_cart_restaurant()
    restaurant = RESTAURANTS.get(restaurant_id) if restaurant_id else None

    for item_id, item_info in cart_data.items():
        total = item_info["price"] * item_info["qty"]
        subtotal += total
        items.append({**item_info, "id": item_id, "total": total})

    return render_template(
        "cart.html",
        items=items,
        subtotal=subtotal,
        restaurant=restaurant,
    )


@app.route("/checkout", methods=["POST"])
def checkout():
    """Process the order through the SmartBite billing engine."""
    cart_data = get_cart()
    if not cart_data:
        return redirect(url_for("cart"))

    # Collect form inputs
    delivery_type = request.form.get("delivery_type", "standard")
    distance_km = float(request.form.get("distance", 5.0))
    promo_discount = float(request.form.get("promo_discount", 0))
    payment_method = request.form.get("payment_method", "cod")

    # Build OrderItem list from cart
    order_items = []
    for item_id, info in cart_data.items():
        order_items.append(OrderItem(name=info["name"], price=info["price"], quantity=info["qty"]))

    # Generate order ID
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    restaurant_id = get_cart_restaurant()
    restaurant = RESTAURANTS.get(restaurant_id) if restaurant_id else None

    # Build order info for the pool
    user_lat = float(request.form.get("user_lat", 0))
    user_lon = float(request.form.get("user_lon", 0))
    # Fallback delivery location: offset from restaurant if no GPS
    if user_lat == 0:
        user_lat = restaurant["location"]["lat"] + 0.003 if restaurant else 18.52
        user_lon = restaurant["location"]["lon"] + 0.003 if restaurant else 73.86

    new_order = {
        "order_id": order_id,
        "restaurant_id": restaurant_id,
        "restaurant_name": restaurant["name"] if restaurant else "Unknown",
        "restaurant_loc": (restaurant["location"]["lat"], restaurant["location"]["lon"]) if restaurant else (18.52, 73.86),
        "delivery_loc": (user_lat, user_lon),
        "order_value": sum(info["price"] * info["qty"] for info in cart_data.values()),
        "delivery_type": delivery_type,
        "items_summary": ", ".join(f"{info['name']} x{info['qty']}" for info in cart_data.values()),
        "timestamp": datetime.now(),
        "status": "waiting",
    }

    # --- ALNS Batching ---
    batch_result = None
    matched_order = None
    is_batched = False

    if delivery_type == "standard":
        matched_order, batch_result = try_match_in_pool(new_order)
        if batch_result and batch_result["is_valid"]:
            is_batched = True
            new_order["status"] = "batched"
            BATCH_HISTORY.append({
                "order1": matched_order["order_id"],
                "order2": order_id,
                "alns": batch_result,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            })
        else:
            # No match — add to pool for future matching
            with POOL_LOCK:
                ORDER_POOL.append(new_order)

    # Build bill with batching status
    bill = build_bill(order_items, distance_km, promo_discount, 0, is_batched)

    order_summary = {
        "order_id": order_id,
        "restaurant": restaurant,
        "delivery_type": delivery_type,
        "payment_method": payment_method,
        "distance_km": distance_km,
        "bill": bill,
        "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "is_batched": is_batched,
        "batch_result": batch_result,
        "matched_order": matched_order,
    }

    # Clear the cart
    session["cart"] = {}
    session.modified = True

    return render_template("order_confirmation.html", order=order_summary)


# ─────────────────────────────────────────────
# Routes — Cart API (JSON)
# ─────────────────────────────────────────────

@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.get_json()
    item_id = data.get("item_id")
    restaurant_id = data.get("restaurant_id")

    # Find the item
    restaurant = RESTAURANTS.get(restaurant_id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    item = next((i for i in restaurant["menu"] if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    cart = get_cart()

    # Check if switching restaurants — clear cart
    cart_rest = get_cart_restaurant()
    if cart_rest and cart_rest != restaurant_id:
        session["cart"] = {}
        cart = get_cart()

    if item_id in cart:
        cart[item_id]["qty"] += 1
    else:
        cart[item_id] = {
            "name": item["name"],
            "price": item["price"],
            "qty": 1,
            "image": item["image"],
            "restaurant_id": restaurant_id,
        }

    session.modified = True
    return jsonify({"cart_count": get_cart_count(), "item_qty": cart[item_id]["qty"]})


@app.route("/api/cart/update", methods=["POST"])
def api_cart_update():
    data = request.get_json()
    item_id = data.get("item_id")
    action = data.get("action")  # "increment" or "decrement"

    cart = get_cart()
    if item_id not in cart:
        return jsonify({"error": "Item not in cart"}), 404

    if action == "increment":
        cart[item_id]["qty"] += 1
    elif action == "decrement":
        cart[item_id]["qty"] -= 1
        if cart[item_id]["qty"] <= 0:
            del cart[item_id]

    session.modified = True

    # Recalculate totals
    subtotal = sum(i["price"] * i["qty"] for i in cart.values())
    item_qty = cart[item_id]["qty"] if item_id in cart else 0
    item_total = cart[item_id]["price"] * cart[item_id]["qty"] if item_id in cart else 0

    return jsonify({
        "cart_count": get_cart_count(),
        "item_qty": item_qty,
        "item_total": item_total,
        "subtotal": subtotal,
    })


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    data = request.get_json()
    item_id = data.get("item_id")

    cart = get_cart()
    if item_id in cart:
        del cart[item_id]
    session.modified = True

    subtotal = sum(i["price"] * i["qty"] for i in cart.values())
    return jsonify({"cart_count": get_cart_count(), "subtotal": subtotal})


@app.route("/api/cart/clear", methods=["POST"])
def api_cart_clear():
    session["cart"] = {}
    session.modified = True
    return jsonify({"cart_count": 0})


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """Live bill calculation for the cart page."""
    data = request.get_json()
    cart_data = get_cart()

    if not cart_data:
        return jsonify({"error": "Cart is empty"}), 400

    distance_km = float(data.get("distance", 5.0))
    promo_discount = float(data.get("promo_discount", 0))
    delivery_type = data.get("delivery_type", "standard")

    order_items = []
    for item_id, info in cart_data.items():
        order_items.append(OrderItem(name=info["name"], price=info["price"], quantity=info["qty"]))

    is_batched = delivery_type == "standard"
    bill = build_bill(order_items, distance_km, promo_discount, 0, is_batched)

    return jsonify({
        "item_total": bill.item_total,
        "delivery_fee": bill.delivery_fee,
        "food_gst": bill.food_gst,
        "service_gst": bill.service_gst,
        "total_discount": bill.total_discount,
        "final_total": bill.final_total,
        "demand_level": bill.demand_level,
        "smart_score": bill.smart_score,
        "is_batched": is_batched,
    })


@app.route("/pool")
def pool_page():
    """Live order pool visualization page."""
    return render_template("pool.html")


@app.route("/api/pool")
def api_pool():
    """Return current pool state and batch history."""
    now = datetime.now()
    with POOL_LOCK:
        active = [
            {"order_id": o["order_id"], "restaurant": o["restaurant_name"],
             "r_lat": o["restaurant_loc"][0], "r_lon": o["restaurant_loc"][1],
             "d_lat": o["delivery_loc"][0], "d_lon": o["delivery_loc"][1],
             "value": o["order_value"], "status": o["status"],
             "items": o["items_summary"],
             "age_sec": int((now - o["timestamp"]).total_seconds())}
            for o in ORDER_POOL
            if (now - o["timestamp"]).total_seconds() < POOL_TIMEOUT_SECS
        ]
    return jsonify({"pool": active, "batches": BATCH_HISTORY[-20:]})


@app.route("/api/restaurants")
def api_restaurants():
    """Return restaurant list with locations for map rendering."""
    return jsonify([
        {"id": r["id"], "name": r["name"], "cuisine": r["cuisine"],
         "rating": r["rating"], "lat": r["location"]["lat"], "lon": r["location"]["lon"]}
        for r in RESTAURANTS.values()
    ])


# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
