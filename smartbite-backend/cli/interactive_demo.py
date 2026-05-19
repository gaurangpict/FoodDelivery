"""
SmartBite Batch Delivery System - Interactive Prototype
Simple user-input based demonstration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from models.location import Location
from models.order import OrderItem
from models.order_extended import Customer, Restaurant, Order, Partner
from engine.batching_engine import OrderBatchingEngine
from engine.billing_engine import build_bill
from engine.batch_billing import build_batched_bill


def get_float_input(prompt):
    """Get valid float input from user."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_int_input(prompt):
    """Get valid integer input from user."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Invalid input. Please enter an integer.")


def create_restaurant():
    """Create restaurant from user input."""
    print("\n--- Restaurant Details ---")
    restaurant_id = input("Restaurant ID (e.g., R1): ").strip()
    name = input("Restaurant Name: ").strip()
    lat = get_float_input("Latitude: ")
    lon = get_float_input("Longitude: ")
    prep_time = get_int_input("Prep time (minutes): ")
    
    return Restaurant(
        restaurant_id=restaurant_id,
        name=name,
        location=Location(f"{restaurant_id}_loc", lat, lon),
        avg_prep_time_mins=prep_time
    )


def create_customer():
    """Create customer from user input."""
    print("\n--- Customer Details ---")
    customer_id = input("Customer ID (e.g., C1): ").strip()
    name = input("Customer Name: ").strip()
    phone = input("Phone number: ").strip()
    lat = get_float_input("Delivery Latitude: ")
    lon = get_float_input("Delivery Longitude: ")
    
    return Customer(
        customer_id=customer_id,
        name=name,
        location=Location(f"{customer_id}_loc", lat, lon),
        phone=phone
    )


def create_order_items():
    """Create order items from user input."""
    items = []
    print("\n--- Order Items ---")
    count = get_int_input("Number of items: ")
    
    for i in range(count):
        print(f"\nItem {i+1}:")
        name = input("Item name: ").strip()
        price = get_float_input("Price: ")
        qty = get_int_input("Quantity: ")
        items.append(OrderItem(name, price, qty))
    
    return items


def create_order(customer, restaurant):
    """Create order from user input."""
    print("\n--- Order Details ---")
    order_id = input("Order ID (e.g., ORD001): ").strip()
    
    print("Delivery type options: standard, urgent")
    delivery_type = input("Delivery type: ").strip().lower()
    if delivery_type not in ["standard", "urgent"]:
        delivery_type = "standard"
    
    items = create_order_items()
    order_value = sum(item.subtotal for item in items)
    
    return Order(
        order_id=order_id,
        customer=customer,
        restaurant=restaurant,
        items=items,
        delivery_type=delivery_type,
        created_at=datetime.now(),
        order_value=order_value,
        delivery_location=customer.location
    )


def print_order_summary(order):
    """Print order summary."""
    print(f"\nOrder {order.order_id}:")
    print(f"  Customer: {order.customer.name}")
    print(f"  Restaurant: {order.restaurant.name}")
    print(f"  Type: {order.delivery_type.upper()}")
    print(f"  Items:")
    for item in order.items:
        print(f"    - {item.name}: Rs.{item.subtotal:.2f} (qty: {item.quantity})")
    print(f"  Order Value: Rs.{order.order_value:.2f}")


def print_batch_info(batch, engine):
    """Print batch information."""
    summary = engine.get_batch_summary(batch)
    
    print(f"\nBatch {batch.batch_id[:8]}...")
    print(f"  Orders: {len(batch.orders)}")
    print(f"  Order IDs: {', '.join([o.order_id for o in batch.orders])}")
    print(f"  Status: {batch.status}")
    
    if len(batch.orders) > 1:
        print(f"  BATCHED: Yes")
        print(f"  Discount: {batch.batch_discount_percent:.1f}%")
        print(f"  Platform Fee: Rs.{batch.platform_extra_fee:.2f}")
        print(f"  Fuel Saved: {batch.fuel_saved_liters:.4f} liters")
    else:
        print(f"  BATCHED: No")


def print_validation_result(validation):
    """Print ALNS validation result."""
    print(f"\nValidation Results:")
    print(f"  Individual Distance: {validation.individual_distances[0]:.4f} + {validation.individual_distances[1]:.4f} = {sum(validation.individual_distances):.4f} km")
    print(f"  Combined Distance: {validation.total_distance_km:.4f} km")
    print(f"  Fuel Saved: {validation.fuel_saved_liters:.4f} liters ({validation.fuel_saved_percent:.1f}%)")
    print(f"  Max Delay: {validation.max_delay_minutes} minutes")
    print(f"  Feasibility Score: {validation.feasibility_score:.2f}/1.0")
    print(f"  Valid: {'YES' if validation.is_valid else 'NO'}")


def print_billing(orders, batch, manual_discount=0.0):
    """Print billing for orders."""
    print(f"\nBilling Breakdown:")
    print("-" * 50)
    
    total_discount = 0
    total_final = 0
    
    for order in orders:
        distance_km = order.restaurant.location.distance_to(order.delivery_location)
        bill = build_batched_bill(
            order_items=order.items,
            distance_km=distance_km,
            promo=manual_discount,
            rain_choice=0,
            is_batched=batch.batch_discount_percent > 0,
            batch_discount_percent=batch.batch_discount_percent
        )
        base_bill = build_bill(
            order_items=order.items,
            distance_km=distance_km,
            promo=manual_discount,
            rain_choice=0
        )
        
        batch_discount_amount = max(0.0, bill.total_discount - base_bill.total_discount)
        total_percent = (bill.total_discount / bill.item_total * 100) if bill.item_total else 0
        
        print(f"\n{order.order_id} - {order.customer.name}:")
        print(f"  Item Total: Rs.{bill.item_total:.2f}")
        print(f"  Delivery: Rs.{bill.delivery_fee:.2f}")
        print(f"  Taxes: Rs.{bill.food_gst + bill.service_gst:.2f}")
        
        if batch_discount_amount > 0:
            print(f"  Regular Discount: -Rs.{base_bill.total_discount:.2f}")
            print(f"  Batch Discount: -Rs.{batch_discount_amount:.2f}")
        else:
            print(f"  Discount: -Rs.{bill.total_discount:.2f}")
        
        print(f"  Total Discount: -Rs.{bill.total_discount:.2f} ({total_percent:.1f}%)")
        print(f"  Final: Rs.{bill.final_total:.2f}")
        
        total_discount += bill.total_discount
        total_final += bill.final_total
    
    print(f"\n{'-' * 50}")
    print(f"Total Discount: Rs.{total_discount:.2f}")
    print(f"Total Customer Pays: Rs.{total_final:.2f}")
    if batch.platform_extra_fee > 0:
        print(f"Platform Fee: Rs.{batch.platform_extra_fee:.2f}")


def run_interactive_demo():
    """Run interactive demonstration - user input only."""
    
    print("\n" + "=" * 60)
    print("SmartBite Batch Delivery System - User Input Demo")
    print("=" * 60)
    print("Enter your own restaurant, customer, and order data")
    print("=" * 60)
    
    engine = OrderBatchingEngine()
    partner = Partner("P1", "Delivery Partner", Location("P1_loc", 28.6100, 77.2080))
    
    orders = []
    manual_discount = 0.0  # Manual discount amount
    
    # Instructions
    print("\nInstructions:")
    print("1. Add orders one by one")
    print("2. Enter your own restaurant and customer data")
    print("3. Specify delivery coordinates for each order")
    print("4. Set manual discount (optional)")
    print("5. Process when ready to see batching results")
    print()
    
    while True:
        print("\n--- OPTIONS ---")
        print(f"1. Add order (total: {len(orders)})")
        print(f"2. Set manual discount (current: Rs.{manual_discount:.2f})")
        print("3. Process all orders for batching")
        print("4. Exit")
        
        choice = input("\nChoose (1-4): ").strip()
        
        if choice == "1":
            print("\n" + "-" * 40)
            print("Add New Order")
            print("-" * 40)
            
            restaurant = create_restaurant()
            customer = create_customer()
            order = create_order(customer, restaurant)
            
            print("\nOrder added successfully:")
            print_order_summary(order)
            orders.append(order)
            
        elif choice == "2":
            print("\n" + "-" * 40)
            print("Set Manual Discount")
            print("-" * 40)
            print(f"Current discount: Rs.{manual_discount:.2f}")
            manual_discount = get_float_input("Enter new discount amount (Rs.): ")
            print(f"Manual discount set to: Rs.{manual_discount:.2f}")
            
        elif choice == "3":
            if len(orders) == 0:
                print("\nError: Add at least one order first.")
                continue
            
            print("\n" + "=" * 60)
            print(f"PROCESSING {len(orders)} ORDER(S)")
            print("=" * 60)
            
            for order in orders:
                print(f"\n--- Order {order.order_id} ---")
                batch = engine.process_order(order, partner=None)
                print_batch_info(batch, engine)
                
                if len(batch.orders) > 1:
                    print("\nRoute Validation:")
                    validation = engine.alns_validator.validate_combined_route(
                        batch.orders[0], batch.orders[1]
                    )
                    print_validation_result(validation)
                
                print_billing(batch.orders, batch, manual_discount)
                
                if len(batch.orders) > 1:
                    print("\nOptimized Route:")
                    route = engine.optimize_route_with_astar(batch)
                    print(f"  Waypoints: {len(route)}")
                    if route:
                        print(f"  Start: ({route[0].x:.4f}, {route[0].y:.4f})")
                        print(f"  End: ({route[-1].x:.4f}, {route[-1].y:.4f})")
            
            print("\n" + "=" * 60)
            print("RESULTS")
            print("=" * 60)
            print(f"Total batches: {len(engine.batches)}")
            print(f"Batched: {sum(1 for b in engine.batches if len(b.orders) > 1)}")
            print(f"Single: {sum(1 for b in engine.batches if len(b.orders) == 1)}")
            print(f"Fuel saved: {sum(b.fuel_saved_liters for b in engine.batches):.4f}L")
            print(f"Platform fee: Rs.{sum(b.platform_extra_fee for b in engine.batches):.2f}")
            
            orders = []
            engine = OrderBatchingEngine()
            
        elif choice == "4":
            print("\nExit.")
            break
        else:
            print("\nInvalid. Enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    run_interactive_demo()
