"""
simulate_shopping.py
────────────────────
Simulates a full 7-day week at Mini Meijer (Monday - Sunday).
Each day runs 4 time blocks with customer counts scaled by a daily
traffic multiplier.  Delivery trucks arrive from the warehouse on
Tuesday and Friday mornings.  On Friday, high-inventory items are
flagged and put on sale for the weekend.  Customers are generated
with demographic profiles that drive shopping time and category
preferences.
"""

import random
import time
from config import CONFIG
from inventory import (
    seed_inventory, inventory, purchase, restock,
    print_inventory, get_low_stock, get_total_value, update_price,
    get_all_products
)

# ─── Configuration (pulled from central config.py) ─────────────────

DELAY_BETWEEN        = CONFIG["delay_between"]
DAY_NAMES            = CONFIG["day_names"]
DAY_TRAFFIC          = CONFIG["day_traffic"]
DELIVERY_DAYS        = CONFIG["delivery_days"]
WAREHOUSE_STOCK      = CONFIG["warehouse_stock"]
HIGH_STOCK_THRESHOLD = CONFIG["high_stock_threshold"]
SALE_DISCOUNT        = CONFIG["sale_discount"]
TIME_BLOCKS          = CONFIG["time_blocks"]
SHOPPER_PROFILES     = CONFIG["shopper_profiles"]
PROFESSION_TO_PROFILE = CONFIG["profession_to_profile"]
FIRST_NAMES          = CONFIG["first_names"]
LAST_NAMES           = CONFIG["last_names"]
RACES                = CONFIG["races"]
PROFESSIONS          = CONFIG["professions"]
RESTOCK_TARGET       = CONFIG["restock_target"]
DELIVERY_RESTOCK_MAX = CONFIG["delivery_restock_max"]

# ─── Week Schedule ─────────────────────────────────────────────────

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Customer traffic multiplier per day (1.0 = normal)
# Weekends are busier, midweek is slower
DAY_TRAFFIC = {
    "Monday":    0.8,
    "Tuesday":   0.9,
    "Wednesday": 0.85,
    "Thursday":  0.95,
    "Friday":    1.1,
    "Saturday":  1.4,
    "Sunday":    1.2,
}

# ─── Warehouse & Delivery System ──────────────────────────────────
# The warehouse holds backup stock. Delivery trucks arrive Tuesday
# and Friday mornings BEFORE the store opens, restocking shelves
# from the warehouse.

WAREHOUSE_STOCK = {
    # category: units delivered per truck
    "Dairy":      60,
    "Produce":    80,
    "Meat":       40,
    "Bakery":     50,
    "Beverages":  70,
    "Pantry":     60,
    "Snacks":     40,
    "Desserts":   30,
}

DELIVERY_DAYS = ["Tuesday", "Friday"]   # Trucks arrive these mornings

HIGH_STOCK_THRESHOLD = 50   # Products above this on Friday get sale suggestion
SALE_DISCOUNT = 0.50        # 50% off suggested sale price


def process_delivery(day_name):
    """Simulate a delivery truck arriving from the warehouse.

    Distributes warehouse stock evenly across products in each category.
    Only restocks products that have {DELIVERY_RESTOCK_MAX} or fewer units remaining.

    Args:
        day_name: The day of the week (e.g. 'Tuesday').
    """
    print(f"\n  {'=' * 55}")
    print(f"  DELIVERY TRUCK -- {day_name} Morning")
    print(f"  {'=' * 55}")
    print(f"  Truck arriving from warehouse...")
    print(f"  (Only restocking items with {DELIVERY_RESTOCK_MAX} or fewer units)")

    total_units = 0

    for category, units in WAREHOUSE_STOCK.items():
        # Find products in this category that need restocking
        products_in_cat = [
            e.value for e in inventory.all_entries()
            if e.value.category == category and e.value.quantity <= DELIVERY_RESTOCK_MAX
        ]
        if not products_in_cat:
            continue

        # Split delivery evenly across products that need it
        per_product = units // len(products_in_cat)
        remainder = units % len(products_in_cat)

        for i, p in enumerate(products_in_cat):
            amount = per_product + (1 if i < remainder else 0)
            if amount > 0:
                p.quantity += amount
                total_units += amount
                print(f"    [OK] +{amount} {p.name} (now {p.quantity})")

    print(f"  [OK] Delivery complete: {total_units} total units restocked.")
    print(f"  {'=' * 55}")


def friday_sale_suggestions():
    """Check inventory for high-stock items and suggest putting them on sale.

    Products with quantity above HIGH_STOCK_THRESHOLD on Friday are
    flagged. Returns the top 5 most overstocked as (product, suggested_price) tuples.
    """
    candidates = []
    for entry in inventory.all_entries():
        p = entry.value
        if p.quantity >= HIGH_STOCK_THRESHOLD:
            sale_price = round(p.price * (1 - SALE_DISCOUNT), 2)
            candidates.append((p, sale_price))
    # Return only the top 5 most overstocked items
    candidates.sort(key=lambda x: x[0].quantity, reverse=True)
    return candidates[:5]


def print_sale_suggestions(suggestions):
    """Print formatted sale suggestions for high-stock Friday items."""
    if not suggestions:
        print("\n  [OK] No overstocked items -- no sales needed.")
        return

    print(f"\n  {'=' * 55}")
    print(f"  FRIDAY SALE -- TOP {len(suggestions)} OVERSTOCKED ITEMS")
    print(f"  {'=' * 55}")
    print(f"  Highest-stock items (above {HIGH_STOCK_THRESHOLD} units) discounted")
    print(f"  to move product before the weekend rush.\n")
    print(f"  {'Name':<20} {'Qty':>5} {'Current':>9} {'Sale Price':>11}  {'Savings':>8}")
    print(f"  {'-' * 58}")
    for p, sale_price in suggestions:
        savings = p.price - sale_price
        print(f"  {p.name:<20} {p.quantity:>5} ${p.price:>7.2f}  ${sale_price:>8.2f}   -${savings:.2f}")

    return suggestions


def apply_sales(suggestions):
    """Apply the suggested sale prices to products."""
    for p, sale_price in suggestions:
        old = p.price
        p.price = sale_price
        print(f"  [OK] {p.name}: ${old:.2f} -> ${sale_price:.2f}")
    print(f"  [OK] {len(suggestions)} items now on sale!")


# ─── Profile Selection ──────────────────────────────────────────────

def get_profile_for_time_block(block_index):
    """Pick a shopper profile weighted by who is likely to shop at this time.

    Args:
        block_index: Index into TIME_BLOCKS (0=morning, 1=midday, 2=evening, 3=night).

    Returns:
        (profile_name, profile_dict) tuple.
    """
    profile_names = list(SHOPPER_PROFILES.keys())
    weights = [SHOPPER_PROFILES[name]["time_weights"][block_index] for name in profile_names]
    chosen = random.choices(profile_names, weights=weights, k=1)[0]
    return chosen, SHOPPER_PROFILES[chosen]


def pick_products_by_preference(products, profile, max_items):
    """Select products for a customer's cart based on profile preferences.

    Uses the profile's category_weights to bias product selection,
    basket_size to set cart limits, and price_threshold to penalise
    items that are too expensive for this customer type.

    Args:
        products:   List of all available Product objects.
        profile:    The shopper profile dict.
        max_items:  Fallback max if profile has no basket_size.

    Returns:
        A list of Product objects for the cart.
    """
    if not products:
        return []

    cat_weights = profile["category_weights"]
    price_cap = profile.get("price_threshold", 999)
    skip_chance = profile.get("skip_chance", 0.0)

    # Assign a weight to each product: category preference + price sensitivity
    weights = []
    for p in products:
        w = cat_weights.get(p.category, 3)
        # Reduce weight for items above the customer's price comfort zone
        if p.price > price_cap:
            if random.random() < skip_chance:
                w = 0              # Customer skips this item entirely
            else:
                w = max(1, w // 2) # Halve the weight -- less likely to pick
        weights.append(w)

    # If every weight is 0, fall back to uniform selection
    if all(w == 0 for w in weights):
        weights = [1] * len(products)

    # Cart size from profile basket_size, capped by time-block max_items
    basket_lo, basket_hi = profile.get("basket_size", (1, max_items))
    num_items = random.randint(basket_lo, min(basket_hi, max_items, len(products)))

    # Weighted sampling without replacement
    cart = []
    available = list(range(len(products)))
    available_weights = list(weights)

    for _ in range(num_items):
        if not available:
            break
        # Need at least one non-zero weight to sample
        if all(w == 0 for w in available_weights):
            break
        chosen_idx = random.choices(range(len(available)), weights=available_weights, k=1)[0]
        cart.append(products[available[chosen_idx]])
        available.pop(chosen_idx)
        available_weights.pop(chosen_idx)

    return cart


# ─── Weighted Purchase Amount ──────────────────────────────────────

def random_purchase_amount():
    """Return a weighted random quantity to simulate real buying patterns.

    Uses purchase_tiers from CONFIG to determine ranges and chances.
    """
    roll = random.randint(0, 99)
    cumulative = 0
    for tier in CONFIG["purchase_tiers"]:
        cumulative += tier["chance"]
        if roll < cumulative:
            return random.randint(tier["min"], tier["max"])
    # Fallback to last tier
    last = CONFIG["purchase_tiers"][-1]
    return random.randint(last["min"], last["max"])

# ─── Customer Demographics ──────────────────────────────────────────

class Customer:
    """Represents a randomly-generated shopper with demographic info.

    When a profile_name is provided, the customer's age is drawn from
    the profile's age range, and their shopper_type is set accordingly.
    """

    def __init__(self, profile_name=None, profile=None):
        self.first_name = random.choice(FIRST_NAMES)
        self.last_name = random.choice(LAST_NAMES)
        self.race = random.choice(RACES)

        if profile_name and profile:
            self.shopper_type = profile_name
            age_lo, age_hi = profile["age_range"]
            self.age = random.randint(age_lo, age_hi)
            # Pick a profession that maps to this profile
            matching = [p for p, t in PROFESSION_TO_PROFILE.items() if t == profile_name]
            self.profession = random.choice(matching) if matching else profile_name
        else:
            self.age = random.randint(18, 80)
            self.profession = random.choice(PROFESSIONS)
            self.shopper_type = PROFESSION_TO_PROFILE.get(self.profession, "Office Worker")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return (f"{self.full_name}, Age {self.age}, "
                f"{self.race}, {self.profession} [{self.shopper_type}]")


def simulate():
    """Run a full 7-day (Monday-Sunday) shopping simulation.

    Each day runs through all 4 time blocks with customer counts
    scaled by the day's traffic multiplier.  Delivery trucks arrive
    on Tuesday and Friday mornings before the store opens.  On Friday
    evening, high-inventory items are flagged for sale.
    """
    # ── Step 1: Load inventory ──────────────────────────────────────
    print("=" * 60)
    print("  Mini Meijer -- 7-Day Weekly Simulation")
    print("=" * 60)
    print("\n  Loading inventory...")
    seed_inventory()

    value_before = get_total_value()
    print(f"\n  Starting inventory value: ${value_before:,.2f}")
    print(f"  Simulating 7 days (Monday - Sunday)")
    print(f"  Deliveries scheduled: {', '.join(DELIVERY_DAYS)}\n")

    # ── Weekly tracking variables ───────────────────────────────────
    week_items_sold = 0
    week_revenue = 0.0
    week_failed = 0
    week_customers = 0
    sales_by_product = {}         # product name -> units sold (all week)
    low_stock_hits = set()        # products that hit low stock at any point
    sales_by_time_block = {}      # time label -> total revenue across all days
    sales_by_day = {}             # day name -> revenue
    customers_by_day = {}         # day name -> customer count
    deliveries_log = []           # list of (day, total_units) tuples
    sale_suggestions_applied = [] # products put on sale Friday
    customer_num = 0

    # ── Step 2: Loop through 7 days ─────────────────────────────────
    for day_index, day_name in enumerate(DAY_NAMES):
        traffic = DAY_TRAFFIC[day_name]
        day_revenue = 0.0
        day_customers = 0

        print("\n" + "#" * 60)
        print(f"  DAY {day_index + 1}: {day_name.upper()}")
        print(f"  Traffic multiplier: {traffic}x")
        print("#" * 60)

        # ── Delivery truck (Tuesday & Friday, before store opens) ──
        if day_name in DELIVERY_DAYS:
            process_delivery(day_name)
            delivered = sum(WAREHOUSE_STOCK.values())
            deliveries_log.append((day_name, delivered))

        # ── Friday: suggest sales for overstocked items (before shopping) ──
        if day_name == "Friday":
            suggestions = friday_sale_suggestions()
            if suggestions:
                print_sale_suggestions(suggestions)
                approve = input("\n  Apply these sale prices? (y/n): ").strip().lower()
                if approve == "y":
                    apply_sales(suggestions)
                    sale_suggestions_applied = suggestions
                else:
                    print("  [--] Sales not applied. Prices unchanged.")

        # ── Run each time block for this day ───────────────────────
        for block_index, block in enumerate(TIME_BLOCKS):
            block_label = block["label"]
            # Scale customer count by day traffic, minimum 1
            block_customers = max(1, int(block["customers"] * traffic))
            block_max_cart = block["max_cart"]
            block_revenue = 0.0

            print(f"\n  --- {day_name} | {block_label} "
                  f"({block_customers} customers) ---")

            for j in range(1, block_customers + 1):
                customer_num += 1
                day_customers += 1

                profile_name, profile = get_profile_for_time_block(block_index)
                customer = Customer(profile_name, profile)
                products = get_all_products()

                if not products:
                    print("  [!] No products left in stock!")
                    break

                cart = pick_products_by_preference(products, profile, block_max_cart)

                print(f"\n  Customer #{customer_num}: {customer}")

                customer_total = 0.0
                customer_items = 0

                for product in cart:
                    qty = random_purchase_amount()

                    if product.quantity >= qty:
                        purchase(product.id, qty)
                        item_cost = product.price * qty
                        week_items_sold += qty
                        week_revenue += item_cost
                        day_revenue += item_cost
                        block_revenue += item_cost
                        customer_total += item_cost
                        customer_items += qty
                        sales_by_product[product.name] = (
                            sales_by_product.get(product.name, 0) + qty
                        )
                        if product.quantity <= 10:
                            low_stock_hits.add(product.name)
                    else:
                        print(f"    [X] {customer.full_name} wanted {qty}x "
                              f"{product.name} but only {product.quantity} left")
                        week_failed += 1

                print(f"  >> {customer.first_name}'s total: "
                      f"{customer_items} items -- ${customer_total:,.2f}")

                time.sleep(DELAY_BETWEEN)

            # Accumulate time block revenue across the week
            sales_by_time_block[block_label] = (
                sales_by_time_block.get(block_label, 0) + block_revenue
            )

        # ── End of day summary ──────────────────────────────────────
        sales_by_day[day_name] = day_revenue
        customers_by_day[day_name] = day_customers
        week_customers += day_customers

        low = get_low_stock()
        print(f"\n  -- End of {day_name} --")
        print(f"     Revenue: ${day_revenue:,.2f}  |  "
              f"Customers: {day_customers}  |  "
              f"Low stock items: {len(low)}")

        # ── End-of-day restock: replenish low items overnight ───────
        if low:
            print(f"\n  [OVERNIGHT RESTOCK] {len(low)} low-stock items restocked to {RESTOCK_TARGET}:")
            for p in low:
                restock_amount = RESTOCK_TARGET - p.quantity
                if restock_amount > 0:
                    p.quantity += restock_amount
                    print(f"    [OK] +{restock_amount} {p.name} (now {p.quantity})")
        else:
            print("  [OK] All shelves stocked -- no overnight restock needed.")

    # ── Step 3: Weekly summary ──────────────────────────────────────
    value_after = get_total_value()

    print("\n" + "=" * 60)
    print("  WEEKLY SIMULATION SUMMARY (7 Days)")
    print("=" * 60)
    print(f"  Total customers served:  {week_customers}")
    print(f"  Total items sold:        {week_items_sold}")
    print(f"  Total revenue:           ${week_revenue:,.2f}")
    print(f"  Failed purchases:        {week_failed}")
    print(f"  Inventory value start:   ${value_before:,.2f}")
    print(f"  Inventory value end:     ${value_after:,.2f}")
    print(f"  Deliveries received:     {len(deliveries_log)}")

    # Revenue by day
    print(f"\n  [REVENUE BY DAY]")
    for day, rev in sales_by_day.items():
        pct = (rev / week_revenue * 100) if week_revenue else 0
        bar = "#" * int(pct / 2)
        custs = customers_by_day[day]
        print(f"     {day:<12} ${rev:>8,.2f}  ({pct:4.1f}%)  "
              f"{custs:>3} customers  {bar}")

    # Revenue by time block (aggregated across all 7 days)
    print(f"\n  [REVENUE BY TIME BLOCK (weekly total)]")
    for label, rev in sales_by_time_block.items():
        pct = (rev / week_revenue * 100) if week_revenue else 0
        bar = "#" * int(pct / 2)
        print(f"     {label:<25} ${rev:>8,.2f}  ({pct:4.1f}%)  {bar}")

    # Delivery log
    if deliveries_log:
        print(f"\n  [DELIVERIES]")
        for day, units in deliveries_log:
            print(f"     {day}: {units} units restocked from warehouse")

    # Low stock alerts
    low = get_low_stock()
    if low:
        print(f"\n  [!] Low Stock Products at End of Week ({len(low)} items):")
        for p in low:
            print(f"     {p.name:<20} -- {p.quantity} left")

    # ── Step 4: Post-simulation menu ────────────────────────────────
    report_data = {
        "total_revenue": week_revenue,
        "total_items_sold": week_items_sold,
        "total_customers": week_customers,
        "failed_purchases": week_failed,
        "value_before": value_before,
        "value_after": value_after,
        "sales_by_product": sales_by_product,
        "low_stock_hits": low_stock_hits,
        "sales_by_time_block": sales_by_time_block,
        "sales_by_day": sales_by_day,
        "customers_by_day": customers_by_day,
        "deliveries_log": deliveries_log,
        "sale_suggestions": sale_suggestions_applied,
    }
    post_simulation_menu(report_data)


def print_report(data):
    """Print a detailed weekly report with daily breakdown, deliveries, and sales."""
    print(f"\n{'=' * 60}")
    print("  Detailed Weekly Report")
    print("=" * 60)

    # Revenue breakdown
    print(f"\n  [REVENUE]")
    print(f"     Total revenue:          ${data['total_revenue']:,.2f}")
    print(f"     Total items sold:       {data['total_items_sold']}")
    print(f"     Failed purchases:       {data['failed_purchases']}")
    print(f"     Inventory value start:  ${data['value_before']:,.2f}")
    print(f"     Inventory value end:    ${data['value_after']:,.2f}")
    total_cust = data.get('total_customers', 1)
    avg = data['total_revenue'] / total_cust if total_cust else 0
    print(f"     Avg spend per customer: ${avg:,.2f}")

    # Revenue by day
    day_sales = data.get("sales_by_day", {})
    if day_sales:
        print(f"\n  [REVENUE BY DAY]")
        custs = data.get("customers_by_day", {})
        for day, rev in day_sales.items():
            pct = (rev / data['total_revenue'] * 100) if data['total_revenue'] else 0
            bar = "#" * int(pct / 2)
            c = custs.get(day, 0)
            print(f"     {day:<12} ${rev:>8,.2f}  ({pct:4.1f}%)  "
                  f"{c:>3} customers  {bar}")

    # Sales by time block
    time_sales = data.get("sales_by_time_block", {})
    if time_sales:
        print(f"\n  [REVENUE BY TIME BLOCK (weekly)]")
        for label, rev in time_sales.items():
            pct = (rev / data['total_revenue'] * 100) if data['total_revenue'] else 0
            bar = "#" * int(pct / 2)
            print(f"     {label:<25} ${rev:>8,.2f}  ({pct:4.1f}%)  {bar}")

    # Deliveries
    deliveries = data.get("deliveries_log", [])
    if deliveries:
        print(f"\n  [DELIVERIES]")
        for day, units in deliveries:
            print(f"     {day}: {units} units restocked from warehouse")

    # Sale suggestions applied
    sales_applied = data.get("sale_suggestions", [])
    if sales_applied:
        print(f"\n  [FRIDAY SALES APPLIED] ({len(sales_applied)} items discounted)")
        for p, sale_price in sales_applied:
            print(f"     {p.name:<20} sale price: ${sale_price:.2f}")

    # Most purchased items (top 5)
    sales = data["sales_by_product"]
    if sales:
        sorted_sales = sorted(sales.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  [TOP 5] Most Purchased Items")
        for rank, (name, qty) in enumerate(sorted_sales[:5], 1):
            bar = "\u2588" * qty
            print(f"     {rank}. {name:<20} -- {qty} sold  {bar}")

        print(f"\n  [BOTTOM 3] Least Purchased Items")
        for name, qty in sorted_sales[-3:]:
            print(f"     {name:<20} -- {qty} sold")

    # Products that hit low stock
    hits = data["low_stock_hits"]
    if hits:
        print(f"\n  [!] Items That Hit Low Stock ({len(hits)}):")
        for name in sorted(hits):
            print(f"     - {name}")
    else:
        print(f"\n  [OK] No items hit low stock during the week.")

    print(f"\n{'=' * 60}")


def post_simulation_menu(report_data):
    """Interactive menu after the simulation to view inventory and restock."""
    while True:
        print(f"\n{'=' * 60}")
        print("  Post-Simulation Options")
        print("=" * 60)
        print("  1. View Full Inventory")
        print("  2. View Low Stock Items")
        print("  3. Restock Low Items (auto)")
        print("  4. Restock a Specific Item")
        print("  5. View Total Inventory Value")
        print("  6. View Detailed Report")
        print("  0. Exit")

        choice = input("\n  Enter choice: ").strip()

        if choice == "1":
            print()
            print_inventory()

        elif choice == "2":
            low = get_low_stock()
            if low:
                print(f"\n  [!] Low Stock Products ({len(low)} items):")
                for p in low:
                    print(f"     {p.id} | {p.name:<20} -- {p.quantity} left")
            else:
                print("\n  [OK] All products are well stocked.")

        elif choice == "3":
            low = get_low_stock()
            if not low:
                print("\n  [OK] No items need restocking.")
            else:
                print(f"\n  Restocking {len(low)} low-stock items to {RESTOCK_TARGET} units...")
                for p in low:
                    restock_amount = RESTOCK_TARGET - p.quantity
                    if restock_amount > 0:
                        restock(p.id, restock_amount)
                print(f"  [OK] All low-stock items restocked to {RESTOCK_TARGET}.")

        elif choice == "4":
            pid = input("  Product ID: ").strip()
            amount = input("  Amount to restock: ").strip()
            try:
                amount = int(amount)
                restock(pid, amount)
            except ValueError:
                print("  [X] Invalid amount.")

        elif choice == "5":
            total = get_total_value()
            print(f"\n  Total inventory value: ${total:,.2f}")
        elif choice == "6":
            print_report(report_data)
        elif choice == "0":
            print("  Goodbye!")
            break

        else:
            print("  Invalid choice. Try again.")


if __name__ == "__main__":
    simulate()
