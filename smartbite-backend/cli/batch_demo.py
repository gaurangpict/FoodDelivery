"""
Prototype CLI for demonstrating the order batching and routing system.
Shows complete workflow: order placement, batching, validation, and routing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from models.location import Location
from models.order import OrderItem
from models.order_extended import Customer, Restaurant, Order, Partner
from engine.batching_engine import OrderBatchingEngine, DeliveryType
from engine.batch_billing import build_batched_bill
from engine.alns_validator import ALNSValidator
from engine.astar_pathfinder import AStarPathfinder, Coordinates


def create_sample_scenario():
    """Create a sample delivery scenario with restaurants and customers."""
    
    # Define locations in a coordinate system
    restaurant_1 = Restaurant(
        restaurant_id="R1",
        name="Pizzeria Downtown",
        location=Location("R1", 28.6139, 77.2090),  # Delhi coordinates (simplified)
        avg_prep_time_mins=10
    )
    
    restaurant_2 = Restaurant(
        restaurant_id="R2",
        name="Burger House",
        location=Location("R2", 28.6145, 77.2095),  # Near R1
        avg_prep_time_mins=8
    )
    
    customer_1 = Customer(
        customer_id="C1",
        name="Alice Singh",
        location=Location("C1_loc", 28.6680, 77.2680),
        phone="9876543210"
    )
    
    customer_2 = Customer(
        customer_id="C2",
        name="Bob Kumar",
        location=Location("C2_loc", 28.6690, 77.2690),  # Near C1
        phone="9876543211"
    )
    
    partner_1 = Partner(
        partner_id="P1",
        name="Rajesh Delivery",
        current_location=Location("P1_loc", 28.6100, 77.2080),
        vehicle_type="motorcycle",
        fuel_consumption_per_km=0.05
    )
    
    return {
        "restaurants": [restaurant_1, restaurant_2],
        "customers": [customer_1, customer_2],
        "partner": partner_1
    }


def create_order_1(scenario):
    """Create first order - Standard delivery."""
    items = [
        OrderItem("Margherita Pizza", 350, 1),
        OrderItem("Garlic Bread", 150, 1),
        OrderItem("Coke 500ml", 60, 2),
    ]
    
    order = Order(
        order_id="ORD001",
        customer=scenario["customers"][0],
        restaurant=scenario["restaurants"][0],
        items=items,
        delivery_type="standard",
        created_at=datetime.now(),
        order_value=620.0,
        delivery_location=scenario["customers"][0].location
    )
    
    return order


def create_order_2(scenario):
    """Create second order - Standard delivery, same area."""
    items = [
        OrderItem("Classic Burger", 280, 2),
        OrderItem("Fries", 120, 1),
        OrderItem("Milkshake", 150, 1),
    ]
    
    order = Order(
        order_id="ORD002",
        customer=scenario["customers"][1],
        restaurant=scenario["restaurants"][1],
        items=items,
        delivery_type="standard",
        created_at=datetime.now(),
        order_value=530.0,
        delivery_location=scenario["customers"][1].location
    )
    
    return order


def create_urgent_order(scenario):
    """Create urgent delivery order."""
    items = [
        OrderItem("Biryani", 450, 1),
        OrderItem("Raita", 80, 1),
    ]
    
    order = Order(
        order_id="ORD003",
        customer=scenario["customers"][0],
        restaurant=scenario["restaurants"][0],
        items=items,
        delivery_type="urgent",
        created_at=datetime.now(),
        order_value=530.0,
        delivery_location=scenario["customers"][0].location,
        urgency_premium=50.0
    )
    
    return order


def print_separator(title=""):
    """Print a formatted separator."""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'-'*70}\n")


def print_order_details(order):
    """Print order details."""
    print(f"📦 Order ID: {order.order_id}")
    print(f"   Customer: {order.customer.name} ({order.customer.customer_id})")
    print(f"   Restaurant: {order.restaurant.name} ({order.restaurant.restaurant_id})")
    print(f"   Delivery Type: {order.delivery_type.upper()}")
    print(f"   Order Value: ₹{order.order_value:.2f}")
    print(f"   Items:")
    for item in order.items:
        print(f"      - {item.name}: ₹{item.subtotal:.2f} (qty: {item.quantity})")


def print_batch_summary(batch, engine):
    """Print batch summary with validation results."""
    summary = engine.get_batch_summary(batch)
    
    print(f"🎁 Batch ID: {batch.batch_id}")
    print(f"   Orders in batch: {summary['order_count']}")
    print(f"   Order IDs: {', '.join(summary['orders'])}")
    print(f"   Status: {batch.status}")
    
    if summary['is_batched']:
        print(f"   ✅ BATCHED & OPTIMIZED")
        print(f"      Discount per customer: {batch.batch_discount_percent:.1f}%")
        print(f"      Platform extra fee: ₹{batch.platform_extra_fee:.2f}")
        print(f"      Fuel saved: {batch.fuel_saved_liters:.3f} liters")
    else:
        print(f"   ⚠️  Single order (no batching possible)")
    
    if summary['assigned_partner']:
        print(f"   Assigned Partner: {summary['assigned_partner']}")


def print_batch_billing(orders, batch):
    """Calculate and print bills for batched orders."""
    print(f"\n💳 BATCH BILLING BREAKDOWN")
    print(f"{'-'*70}")
    
    total_customer_discount = 0
    total_final = 0
    
    for i, order in enumerate(orders, 1):
        # Calculate distance (simplified)
        distance_km = order.restaurant.location.distance_to(order.delivery_location)
        
        # Build bill with batch discount
        bill = build_batched_bill(
            order_items=order.items,
            distance_km=distance_km,
            promo=0.0,
            rain_choice=0,
            is_batched=batch.batch_discount_percent > 0,
            batch_discount_percent=batch.batch_discount_percent
        )
        
        print(f"\n📋 Order {i}: {order.order_id}")
        print(f"   Item Total: ₹{bill.item_total:.2f}")
        print(f"   Delivery Fee: ₹{bill.delivery_fee:.2f}")
        print(f"   GST (Food): ₹{bill.food_gst:.2f}")
        print(f"   GST (Service): ₹{bill.service_gst:.2f}")
        print(f"   Discount Applied: -₹{bill.total_discount:.2f} ({batch.batch_discount_percent:.1f}%)")
        print(f"   ────────────────")
        print(f"   Final Total: ₹{bill.final_total:.2f}")
        
        total_customer_discount += bill.total_discount
        total_final += bill.final_total
    
    print(f"\n{'-'*70}")
    print(f"💰 BATCH TOTALS:")
    print(f"   Total Customer Discount: ₹{total_customer_discount:.2f}")
    print(f"   Total Customer Pays: ₹{total_final:.2f}")
    print(f"   Platform Extra Fee: ₹{batch.platform_extra_fee:.2f}")
    print(f"   Platform Profit: ₹{total_customer_discount + batch.platform_extra_fee:.2f}")


def run_prototype_demo():
    """Run the complete prototype demonstration."""
    
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "SMARTBITE BATCH DELIVERY SYSTEM" + " "*22 + "║")
    print("║" + " "*10 + "Advanced Routing & Order Optimization Prototype" + " "*11 + "║")
    print("╚" + "="*68 + "╝")
    
    # Initialize system
    alns_validator = ALNSValidator()
    astar_pathfinder = AStarPathfinder()
    engine = OrderBatchingEngine(alns_validator, astar_pathfinder)
    
    # Create scenario
    scenario = create_sample_scenario()
    
    print_separator("SCENARIO SETUP")
    print("🏪 Restaurants:")
    for r in scenario["restaurants"]:
        print(f"   {r.restaurant_id}: {r.name} at ({r.location.latitude}, {r.location.longitude})")
    
    print("\n👥 Customers:")
    for c in scenario["customers"]:
        print(f"   {c.customer_id}: {c.name} at ({c.location.latitude}, {c.location.longitude})")
    
    print("\n🚗 Delivery Partner:")
    print(f"   {scenario['partner'].partner_id}: {scenario['partner'].name} (Motorcycle)")
    
    # SCENARIO 1: Standard Order from Customer 1
    print_separator("SCENARIO 1: CUSTOMER C1 PLACES STANDARD ORDER")
    order1 = create_order_1(scenario)
    print_order_details(order1)
    
    batch1 = engine.process_order(order1)
    print_batch_summary(batch1, engine)
    print("   ⏳ Order added to pool, waiting for matching customer...")
    
    # SCENARIO 2: Second Customer Places Order (Same Area)
    print_separator("SCENARIO 2: CUSTOMER C2 PLACES STANDARD ORDER (SAME AREA)")
    order2 = create_order_2(scenario)
    print_order_details(order2)
    
    print("\n   🔍 ALNS Algorithm: Checking route viability...")
    validation = engine.alns_validator.validate_combined_route(order1, order2)
    
    print(f"   ✅ Route Validation Results:")
    print(f"      Individual routes distance: {validation.individual_distances[0]:.2f} + {validation.individual_distances[1]:.2f} = {sum(validation.individual_distances):.2f} km")
    print(f"      Combined optimized route: {validation.total_distance_km:.2f} km")
    print(f"      Fuel saved: {validation.fuel_saved_liters:.3f} liters ({validation.fuel_saved_percent:.1f}%)")
    print(f"      Max delivery delay: {validation.max_delay_minutes} minutes")
    print(f"      Cost savings: ₹{validation.cost_savings:.2f}")
    print(f"      Feasibility score: {validation.feasibility_score:.2f}/1.0")
    
    if validation.is_valid:
        print(f"      Status: ✅ VALID - Batching approved!")
    else:
        print(f"      Status: ❌ INVALID - Route doesn't meet criteria")
    
    # Process order 2 (should batch with order 1)
    batch2 = engine.process_order(order2)
    print_batch_summary(batch2, engine)
    
    # Assign partner
    print_separator("PARTNER ASSIGNMENT & ROUTING")
    engine.assign_partner_to_batch(batch2, scenario["partner"])
    print(f"✅ Partner {scenario['partner'].partner_id} ({scenario['partner'].name}) assigned to batch")
    
    # Optimize route with A*
    print("\n🗺️  A* Route Optimization:")
    route = engine.optimize_route_with_astar(batch2)
    print(f"   Route points: {len(route)} waypoints computed")
    if route:
        print(f"   Start: ({route[0].x:.4f}, {route[0].y:.4f})")
        print(f"   End: ({route[-1].x:.4f}, {route[-1].y:.4f})")
        estimated_distance = engine.astar_pathfinder.estimate_travel_distance(route)
        print(f"   Estimated travel distance: {estimated_distance:.2f} units (~{estimated_distance:.2f} km)")
    
    # Billing
    print_separator("BILLING WITH BATCH DISCOUNT")
    print(f"\n💰 Batch Discount Applied: {batch2.batch_discount_percent:.1f}%")
    print(f"   (Both customers receive discount for order consolidation)")
    print_batch_billing(batch2.orders, batch2)
    
    # SCENARIO 3: Urgent Order
    print_separator("SCENARIO 3: URGENT DELIVERY ORDER")
    order3 = create_urgent_order(scenario)
    print_order_details(order3)
    
    print("\n   ⚡ Processing as URGENT...")
    batch3 = engine.process_urgent_order(order3, scenario["partner"])
    print_batch_summary(batch3, engine)
    print(f"   ✅ Partner assigned immediately")
    print(f"   Route: Direct from {order3.restaurant.name} to {order3.customer.name}")
    print(f"   No discount (urgent premium: ₹{order3.urgency_premium:.2f})")
    
    # Summary Statistics
    print_separator("SYSTEM SUMMARY")
    print(f"📊 Total Orders Processed: {len(engine.batches)} batches created")
    
    batched_count = sum(1 for b in engine.batches if len(b.orders) > 1)
    single_count = sum(1 for b in engine.batches if len(b.orders) == 1)
    
    print(f"   ✅ Batched deliveries: {batched_count}")
    print(f"   ⚠️  Single-order deliveries: {single_count}")
    
    total_orders = sum(len(b.orders) for b in engine.batches)
    print(f"   Total orders in all batches: {total_orders}")
    
    total_fuel_saved = sum(b.fuel_saved_liters for b in engine.batches)
    print(f"\n⛽ Total Fuel Saved: {total_fuel_saved:.3f} liters")
    print(f"🌱 Environmental Impact: Reduced emissions by ~{total_fuel_saved * 2.3:.2f} kg CO2")
    
    total_discount_given = sum(
        build_batched_bill(
            order_items=o.items,
            distance_km=o.restaurant.location.distance_to(o.delivery_location),
            promo=0.0,
            rain_choice=0,
            is_batched=True,
            batch_discount_percent=b.batch_discount_percent
        ).total_discount
        for b in engine.batches if b.batch_discount_percent > 0
        for o in b.orders
    )
    
    total_platform_fee = sum(b.platform_extra_fee for b in engine.batches if b.platform_extra_fee > 0)
    
    print(f"\n💸 Financial Summary:")
    print(f"   Customer discounts given: -₹{total_discount_given:.2f}")
    print(f"   Platform extra fees earned: +₹{total_platform_fee:.2f}")
    print(f"   Net platform benefit per batch: ₹{total_platform_fee - (total_discount_given / max(batched_count, 1)):.2f}")
    
    print_separator()
    print("✅ Prototype demonstration complete!")
    print("   Ready for full deployment with real routing APIs\n")


if __name__ == "__main__":
    run_prototype_demo()
