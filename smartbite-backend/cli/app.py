from models import bill
from models.order import OrderItem
from engine.billing_engine import build_bill


def run_cli():

    n = int(input("Enter number of items: "))
    items = []

    for i in range(n):
        print(f"\nItem {i+1}")
        name = input("Name: ")
        price = float(input("Price: ₹"))
        qty = int(input("Qty: "))
        items.append(OrderItem(name, price, qty))

    distance = float(input("\nDistance (km): "))
    promo = float(input("Promo discount: ") or 0)

    print("\nRain: 0 None | 1 Light | 2 Medium | 3 Heavy")
    rain = int(input("Enter: "))

    bill = build_bill(items, distance, promo, rain)

    print("\n============================")
    print("      SMARTBITE BILL")
    print("============================")

    for item in bill.order_items:
        print(f"{item.name} x{item.quantity} = ₹{item.subtotal:.2f}")

    print(f"\nItem Total: ₹{bill.item_total:.2f}")
    #print(f"Packaging: ₹{bill.packaging:.2f}")
    print(f"Delivery Fee: ₹{bill.delivery_fee:.2f}")

    # ✅ Show surge only if applicable
    if bill.surge_fee > 0:
        print(f"Surge Fee: ₹{bill.surge_fee:.2f}")

    if bill.rain_fee > 0:
        print(f"Rain Fee: ₹{bill.rain_fee:.2f} ({bill.rain_label})")

    print(f"\nGST on Food (5%): ₹{bill.food_gst:.2f}")
    print(f"GST on Services (18%): ₹{bill.service_gst:.2f}")

    print(f"Discount Applied: -₹{bill.total_discount:.2f}")
    print("----------------------------")
    print(f"Final Total: ₹{bill.final_total:.2f}")
    print("============================")
    print(f"Demand Level: {bill.demand_level.upper()}")
    print(f"Smart Score: {bill.smart_score}")
    print("============================")