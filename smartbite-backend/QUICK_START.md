# Quick Start Guide - SmartBite Batching System

## 30-Second Overview

SmartBite intelligently groups food delivery orders from customers in the same area, optimizes routes, and gives both customers discounts while the platform earns fees.

## Running the System

### Step 1: Navigate to Project
```bash
cd c:\Users\ASUS\Desktop\Pricing Project\smartbite-backend
```

### Step 2: Run Demo
```bash
# Show enhanced batching demonstration
python cli/batch_demo_enhanced.py
```

### Step 3: Watch Output
The system will demonstrate:
- ✅ Two customers in same area placing orders
- ✅ ALNS validation (showing 40%+ fuel savings)
- ✅ Batch creation with 6.5% discounts
- ✅ A* route optimization (4 waypoints)
- ✅ Billing with applied discounts
- ✅ Platform profitability analysis

## How It Works in 5 Steps

### Step 1: Order Arrives
```
Customer C1 orders Pizza (₹620) → Standard Delivery
System: Added to pool, waiting for matching customer
```

### Step 2: Second Order Arrives  
```
Customer C2 orders Burger (₹530) → Standard Delivery (Same area)
System: Found C1 waiting! Checking if batching is viable...
```

### Step 3: ALNS Validates Routes
```
Individual routes: R1→C1 + R2→C2 = 0.017 km
Combined route:   R1→R2→C1→C2 = 0.010 km
Fuel saved: 41.5% ✅ APPROVED

Delay check: 0 minutes < 15 minutes limit ✅ APPROVED

Status: ✅ VALID - Creating batch!
```

### Step 4: A* Optimizes Path
```
Waypoints computed: 4 (R1, R2, C1, C2)
Estimated distance: 0.024 km
Status: ✅ Route ready
```

### Step 5: Billing & Dispatch
```
Customer C1 Bill:
  Item Total: ₹620
  Discount: -₹40 (6.5% batch discount)
  Final: ₹580

Customer C2 Bill:
  Item Total: ₹830
  Discount: -₹54 (6.5% batch discount)
  Final: ₹776

Platform Earns: ₹25 (batch fee) + fuel savings
```

## API Usage Example

### Creating and Processing an Order

```python
from models.order_extended import Customer, Restaurant, Order
from models.order import OrderItem
from engine.batching_engine import OrderBatchingEngine
from models.location import Location
from datetime import datetime

# Initialize engine
engine = OrderBatchingEngine()

# Define locations
customer_1 = Customer(
    customer_id="C1",
    name="Alice Singh",
    location=Location("Alice", 28.6200, 77.2150),
    phone="9876543210"
)

restaurant_1 = Restaurant(
    restaurant_id="R1",
    name="Pizzeria Downtown",
    location=Location("R1", 28.6139, 77.2090)
)

# Create order
items = [
    OrderItem("Margherita Pizza", 350, 1),
    OrderItem("Garlic Bread", 150, 1),
]

order = Order(
    order_id="ORD001",
    customer=customer_1,
    restaurant=restaurant_1,
    items=items,
    delivery_type="standard",
    created_at=datetime.now(),
    order_value=500.0,
    delivery_location=customer_1.location
)

# Process order
batch = engine.process_order(order)

# Get batch info
summary = engine.get_batch_summary(batch)
print(f"Batch ID: {summary['batch_id']}")
print(f"Orders: {summary['order_count']}")
print(f"Discount: {summary['batch_discount_percent']:.1f}%")
```

## Configuration

Edit these values in `engine/batching_engine.py` to customize behavior:

```python
# How long to wait for a matching customer (seconds)
STANDARD_POOL_TIMEOUT_SECS = 60

# Maximum distance to consider "same area" (km)
SAME_AREA_RADIUS_KM = 0.5

# Customer discounts for batched orders
BATCH_DISCOUNT_X_PERCENT = 5.0
BATCH_DISCOUNT_Y_PERCENT = 8.0

# Platform revenue per batch
PLATFORM_EXTRA_FEE = 25.0

# In alns_validator.py - Route validation thresholds
MIN_FUEL_SAVINGS_PERCENT = 10.0   # Minimum fuel efficiency improvement
MAX_DELIVERY_DELAY_MINS = 15      # Maximum acceptable delay
```

## Understanding the Output

### ALNS Validation Results
```
Individual route distance: 0.009 + 0.008 = 0.017 km
  ↑ Distance for Order 1 alone + Distance for Order 2 alone

Combined route distance: 0.010 km
  ↑ Optimized distance for both together (R1 → R2 → C1 → C2)

Fuel saved: 0.0004 liters (41.5%)
  ↑ Liters saved × Percentage improvement

Max delivery delay: 0 minutes
  ↑ How much longer customers wait (within 15-minute threshold)

Cost savings: ₹0.02
  ↑ Fuel cost × Liters saved

Feasibility: 100.09%
  ↑ Score from 0-100% (higher is better)

Status: ✅ VALID
  ↑ Batch will be created if all checks pass
```

### Batch Info
```
🎁 ✅ BATCHED!
   Batch ID: fac82f36-fadc-4555-9371-f4c3c742113e
   Orders: ORD001, ORD002
   Status: pending
   Discount: 6.5%
   Platform Fee: ₹25.00
   Fuel Saved: 0.000 L
```

### Customer Billing
```
📋 ORD001 (Alice Singh):
   Item Total: ₹620.00
   Delivery: ₹2.50
   Taxes: ₹31.45
   Discount: -₹40.30 (6.5% batch discount)
   Final: ₹595.05
           ↑ Customer saves ₹40!
```

## Common Scenarios

### Scenario 1: Successful Batch
```
Conditions:
  ✓ Two standard orders within 60 seconds
  ✓ Customers within 0.5 km of each other
  ✓ ALNS validates 10%+ fuel savings

Result:
  ✅ Batch created
  ✅ Both customers get 6.5% discount
  ✅ Platform earns ₹25 + fuel savings
```

### Scenario 2: No Match Found
```
Conditions:
  ✓ Standard order arrives
  ✗ No other orders in pool

Result:
  ✅ Order added to pool (waits 60 seconds)
  ⚠️ Delivered as single order (no discount)
  ❌ Pool timeout reached → Single delivery
```

### Scenario 3: Urgent Order
```
Conditions:
  ✓ Order marked as "urgent" delivery

Result:
  ✅ Partner assigned immediately
  ✅ Direct route (no batching)
  ❌ No discount applied
  ✅ Premium fee may apply
```

### Scenario 4: ALNS Validation Fails
```
Conditions:
  ✓ Two orders found to match
  ✗ Combined route saves only 5% fuel (< 10% minimum)

Result:
  ❌ Batch not created
  ⚠️ Both delivered separately
  ❌ No discounts applied
```

## Performance Tips

### To Increase Batching Success Rate
```python
# Increase pool wait time
STANDARD_POOL_TIMEOUT_SECS = 120  # From 60 to 120 seconds

# Expand geographic area
SAME_AREA_RADIUS_KM = 1.0  # From 0.5 to 1.0 km

# Relax fuel savings requirement
MIN_FUEL_SAVINGS_PERCENT = 5.0  # From 10 to 5%

# Result: More batches but longer wait times for customers
```

### To Prioritize Speed
```python
# Decrease pool wait time
STANDARD_POOL_TIMEOUT_SECS = 30  # From 60 to 30 seconds

# Tighten geographic area
SAME_AREA_RADIUS_KM = 0.3  # From 0.5 to 0.3 km

# Increase fuel savings requirement
MIN_FUEL_SAVINGS_PERCENT = 15.0  # From 10 to 15%

# Result: Faster delivery but fewer batches
```

## Monitoring & Metrics

After running, check these metrics:

```python
# Total batches created
len(engine.batches)

# Batched vs single orders
batched = sum(1 for b in engine.batches if len(b.orders) > 1)
single = sum(1 for b in engine.batches if len(b.orders) == 1)

# Total fuel saved
total_fuel = sum(b.fuel_saved_liters for b in engine.batches)

# Platform revenue captured
total_fees = sum(b.platform_extra_fee for b in engine.batches)

# Print summary
print(f"Batching success rate: {batched/(batched+single)*100:.1f}%")
print(f"Fuel saved: {total_fuel:.3f} liters")
print(f"Platform revenue: ₹{total_fees:,.2f}")
```

## Troubleshooting

### Problem: No Batches Created
```
Check:
  1. Are orders within 60 seconds of each other?
  2. Are customers within 0.5 km radius?
  3. Does ALNS find 10%+ fuel savings?
  4. Are delivery types both "standard"?

Debug:
  - Reduce SAME_AREA_RADIUS_KM to 1.0 km
  - Reduce MIN_FUEL_SAVINGS_PERCENT to 5%
  - Increase STANDARD_POOL_TIMEOUT_SECS to 120
```

### Problem: All Orders Single Delivery
```
This is normal if:
  - Orders are far apart (> 0.5 km)
  - Orders have different delivery times
  - System can't find matching customers

Check ALNS output for feasibility score.
```

### Problem: Discounts Not Applied
```
Check:
  1. Is batch successfully created (len(batch.orders) > 1)?
  2. Is batch_discount_percent > 0?
  3. Check billing calculation in batch_billing.py

Remember: Only successful batches get discounts
```

## Next Steps

1. ✅ **Understand the System**: Read BATCHING_SYSTEM.md
2. ✅ **Run the Demo**: Execute batch_demo_enhanced.py
3. ⬜ **Integrate APIs**: Connect to real mapping services
4. ⬜ **Test with Real Data**: Use actual restaurant locations
5. ⬜ **Deploy**: Set up production infrastructure
6. ⬜ **Monitor**: Track batching metrics and ROI

## Documentation

- [README.md](./README.md) - Project overview
- [BATCHING_SYSTEM.md](./BATCHING_SYSTEM.md) - Complete system docs
- [TECHNICAL_SPEC.md](./TECHNICAL_SPEC.md) - Algorithm details

## Support

For questions:
1. Check the technical specification for algorithm details
2. Review code comments in engine/ folder
3. Run demo files to see live examples
4. Examine test cases in cli/ folder

---

**Ready to optimize deliveries? Start with `python cli/batch_demo_enhanced.py`!**
