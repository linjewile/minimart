"""
simulate_shopping.py
────────────────────
Simulates random customers shopping at Mini Meijer.
Customers are generated with demographic profiles (profession, age)
that determine WHEN they shop (time-of-day weights) and WHAT they buy
(category preference weights).
After the simulation, a summary report is printed.
"""

import random
import time
from inventory import (
    seed_inventory, inventory, purchase, restock,
    print_inventory, get_low_stock, get_total_value
)

# ─── Configuration ──────────────────────────────────────────────────

DELAY_BETWEEN = 0.3         # Seconds between customers (for readability)

# ─── Time-of-Day Schedule ──────────────────────────────────────────
# Each block has a label, hours, total customers, and max cart size.
# The demographic mix is now driven by SHOPPER_PROFILES below.

TIME_BLOCKS = [
    {
        "label":      "Morning (7am - 9am)",
        "hours":      "7:00 - 9:00",
        "customers":  8,
        "max_cart":   4,
    },
    {
        "label":      "Midday (11am - 1pm)",
        "hours":      "11:00 - 13:00",
        "customers":  5,
        "max_cart":   3,
    },
    {
        "label":      "Evening (4pm - 7pm)",
        "hours":      "16:00 - 19:00",
        "customers":  12,
        "max_cart":   6,
    },
    {
        "label":      "Night (8pm - 10pm)",
        "hours":      "20:00 - 22:00",
        "customers":  3,
        "max_cart":   3,
    },
]


# ─── Demographic Shopper Profiles ──────────────────────────────────
# Each profile defines:
#   - who shops (profession, age range)
#   - when they prefer to shop (time block weights: morning, midday, evening, night)
#   - what they buy (category weights -- higher = more likely to pick from that category)
#
# Time weights are probability weights for which time block this type
# of shopper appears in. E.g. a Student has weight 1 for morning,
# 2 for midday, 8 for evening, 5 for night -- so they mostly show up
# in the evening.

SHOPPER_PROFILES = {
    # ── Stay-at-home parents: morning shoppers, family staples ──
    "Stay-at-Home Parent": {
        "age_range":    (25, 45),
        "time_weights":  [8, 3, 1, 0],   # morning heavy
        "category_weights": {
            "Dairy": 8, "Bakery": 7, "Produce": 7, "Beverages": 5,
            "Meat": 6, "Pantry": 8, "Snacks": 5, "Desserts": 4,
        },
    },
    # ── Retired: midday shoppers, healthy + staples ──
    "Retired": {
        "age_range":    (60, 80),
        "time_weights":  [3, 8, 2, 0],   # midday heavy
        "category_weights": {
            "Dairy": 7, "Bakery": 8, "Produce": 9, "Beverages": 6,
            "Meat": 5, "Pantry": 7, "Snacks": 3, "Desserts": 4,
        },
    },
    # ── Students: evening/night, cheap + snacks ──
    "Student": {
        "age_range":    (18, 25),
        "time_weights":  [1, 2, 8, 5],   # evening + night
        "category_weights": {
            "Dairy": 4, "Bakery": 5, "Produce": 2, "Beverages": 8,
            "Meat": 3, "Pantry": 7, "Snacks": 9, "Desserts": 7,
        },
    },
    # ── Office workers (9-5 jobs): evening rush ──
    "Office Worker": {
        "age_range":    (25, 55),
        "time_weights":  [1, 1, 9, 2],   # evening heavy
        "category_weights": {
            "Dairy": 6, "Bakery": 4, "Produce": 7, "Beverages": 5,
            "Meat": 8, "Pantry": 7, "Snacks": 4, "Desserts": 5,
        },
    },
    # ── Trade workers (early shift): morning + evening ──
    "Trade Worker": {
        "age_range":    (22, 55),
        "time_weights":  [5, 1, 7, 1],   # morning + evening
        "category_weights": {
            "Dairy": 5, "Bakery": 6, "Produce": 4, "Beverages": 7,
            "Meat": 8, "Pantry": 6, "Snacks": 6, "Desserts": 3,
        },
    },
    # ── Night shift workers: night + morning ──
    "Night Shift": {
        "age_range":    (20, 50),
        "time_weights":  [4, 0, 1, 8],   # night heavy
        "category_weights": {
            "Dairy": 5, "Bakery": 4, "Produce": 3, "Beverages": 8,
            "Meat": 4, "Pantry": 5, "Snacks": 8, "Desserts": 6,
        },
    },
}

# Map old profession names to shopper profile types
PROFESSION_TO_PROFILE = {
    "Teacher":              "Office Worker",
    "Nurse":                "Night Shift",
    "Software Engineer":    "Office Worker",
    "Electrician":          "Trade Worker",
    "Accountant":           "Office Worker",
    "Chef":                 "Night Shift",
    "Mechanic":             "Trade Worker",
    "Pharmacist":           "Office Worker",
    "Graphic Designer":     "Office Worker",
    "Lawyer":               "Office Worker",
    "Cashier":              "Trade Worker",
    "Construction Worker":  "Trade Worker",
    "Dentist":              "Office Worker",
    "Firefighter":          "Night Shift",
    "Barber":               "Trade Worker",
    "Social Worker":        "Office Worker",
    "Truck Driver":         "Night Shift",
    "Plumber":              "Trade Worker",
    "Retail Manager":       "Trade Worker",
    "Student":              "Student",
    "Retired":              "Retired",
    "Freelancer":           "Office Worker",
    "Doctor":               "Office Worker",
    "Salesperson":          "Office Worker",
    "Warehouse Associate":  "Night Shift",
    "Stay-at-Home Parent":  "Stay-at-Home Parent",
}


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
    """Select products for a customer's cart based on their category preferences.

    Uses the profile's category_weights to bias product selection toward
    categories the customer is more likely to buy from.

    Args:
        products:   List of all available Product objects.
        profile:    The shopper profile dict with category_weights.
        max_items:  Maximum number of items in the cart.

    Returns:
        A list of Product objects for the cart.
    """
    if not products:
        return []

    cat_weights = profile["category_weights"]

    # Assign a weight to each product based on its category
    weights = []
    for p in products:
        w = cat_weights.get(p.category, 3)  # default weight 3 for unknown categories
        weights.append(w)

    # Pick items using weighted sampling (no duplicates)
    num_items = random.randint(1, min(max_items, len(products)))
    cart = []
    available = list(range(len(products)))
    available_weights = list(weights)

    for _ in range(num_items):
        if not available:
            break
        chosen_idx = random.choices(range(len(available)), weights=available_weights, k=1)[0]
        cart.append(products[available[chosen_idx]])
        available.pop(chosen_idx)
        available_weights.pop(chosen_idx)

    return cart


# ─── Weighted Purchase Amount ──────────────────────────────────────

def random_purchase_amount():
    """Return a weighted random quantity to simulate real buying patterns.

    60% chance: 1-3 units  (normal purchase)
    30% chance: 4-6 units  (occasional bulk buyer)
    10% chance: 7-12 units (rare large purchase)
    """
    roll = random.randint(0, 99)
    if roll < 60:
        return random.randint(1, 3)
    elif roll < 90:
        return random.randint(4, 6)
    else:
        return random.randint(7, 12)

# ─── Customer Demographics ──────────────────────────────────────────

FIRST_NAMES = [
    "Chloe", "Temi", "Jazlyn", "Noah", "Jacque", "James", "Daniela", "Omar",
    "Diana", "Carolina", "Isabella", "Mason", "Charlotte", "Logan", "Amelia",
    "Aiden", "Harper", "Elijah", "Angel", "Ben", "Grace", "Caleb",
    "Lily", "Jack", "Zoe", "Ryan", "Nora", "Leo", "Amora", "Dylan",
    "Aaliyah", "Marcus", "Fatima", "Li", "Priya", "Carlos", "Yuki",
    "Darnell", "Keiko", "Rashid", "Ingrid", "Benito", "Jason", "Kofi",
    "Princess", "Jamal", "Ananya", "Dante", "Manuel", "Hiroshi", "Amara",
    "Toure", "Rosa", "Tariq", "Simone", "Andrei", "Jasmine", "Digna",
    "Elena", "Noel", "Valentina", "Raj", "Aisha", "Jorge", "Bianca",
    "Hassan", "Monique", "Jin", "Camila", "Tyrone", "Leila"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Martinez", "Lopez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Lee", "Kim", "Nguyen", "Patel", "Chen", "Wang", "Jackson", "White",
    "Harris", "Clark", "Robinson", "Walker", "Hall", "Young", "King",
    "Wright", "Torres", "Rivera", "Evans", "Okafor", "Yamamoto", "Singh",
    "Johansson", "Petrov", "Alvarado", "Mensah"
]

RACES = [
    "White", "Black", "Hispanic", "Asian", "Arab",
    "Native American", "Pacific Islander", "Multiracial"
]

PROFESSIONS = [
    "Teacher", "Nurse", "Software Engineer", "Electrician", "Accountant",
    "Chef", "Mechanic", "Pharmacist", "Graphic Designer", "Lawyer",
    "Cashier", "Construction Worker", "Dentist", "Firefighter", "Barber",
    "Social Worker", "Truck Driver", "Plumber", "Retail Manager", "Student",
    "Retired", "Freelancer", "Doctor", "Salesperson", "Warehouse Associate",
    "Stay-at-Home Parent", "Administrator" ,"Security Guard", "Small Business Owner", "Artist", "Musician", "Scientist", "Athlete",
]


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


def get_all_products():
    """Collect every product currently in the inventory into a list."""
    return [entry.value for entry in inventory.all_entries()]


def simulate():
    """Run the full shopping simulation across time-of-day blocks."""
    # ── Step 1: Load inventory ──────────────────────────────────────
    print("=" * 60)
    print("  Mini Meijer -- Shopping Simulation")
    print("=" * 60)
    print("\n  Loading inventory...")
    seed_inventory()

    # ── Step 2: Snapshot before ──────────────────────────────────────
    value_before = get_total_value()
    total_customers = sum(block["customers"] for block in TIME_BLOCKS)
    print(f"\n  Starting inventory value: ${value_before:,.2f}")
    print(f"  Simulating {total_customers} customers across {len(TIME_BLOCKS)} time blocks...\n")

    total_items_sold = 0
    total_revenue = 0.0
    failed_purchases = 0
    sales_by_product = {}       # Track units sold per product name
    low_stock_hits = set()      # Track products that hit low stock during simulation
    sales_by_time_block = {}    # Track revenue per time block
    customer_num = 0

    # ── Step 3: Simulate each time block ────────────────────────────
    for block_index, block in enumerate(TIME_BLOCKS):
        block_label = block["label"]
        block_customers = block["customers"]
        block_max_cart = block["max_cart"]
        block_revenue = 0.0

        print("\n" + "=" * 60)
        print(f"  TIME BLOCK: {block_label}")
        print(f"  Hours: {block['hours']}  |  Expected customers: {block_customers}")
        print("=" * 60)

        for j in range(1, block_customers + 1):
            customer_num += 1

            # Pick a shopper profile weighted by time of day
            profile_name, profile = get_profile_for_time_block(block_index)
            customer = Customer(profile_name, profile)
            products = get_all_products()

            if not products:
                print("  [!] No products left in stock!")
                break

            # Build cart using the customer's category preferences
            cart = pick_products_by_preference(products, profile, block_max_cart)

            print(f"\n  Customer #{customer_num}: {customer}")

            customer_total = 0.0
            customer_items = 0

            for product in cart:
                qty = random_purchase_amount()

                # Check if purchase will succeed before buying
                if product.quantity >= qty:
                    purchase(product.id, qty)
                    item_cost = product.price * qty
                    total_items_sold += qty
                    total_revenue += item_cost
                    block_revenue += item_cost
                    customer_total += item_cost
                    customer_items += qty
                    # Track sales per product
                    sales_by_product[product.name] = sales_by_product.get(product.name, 0) + qty
                    # Track if product hit low stock
                    if product.quantity <= 10:
                        low_stock_hits.add(product.name)
                else:
                    print(f"    [X] {customer.full_name} wanted {qty}x {product.name} but only {product.quantity} left")
                    failed_purchases += 1

            print(f"  >> {customer.first_name}'s total: {customer_items} items -- ${customer_total:,.2f}")

            time.sleep(DELAY_BETWEEN)

        sales_by_time_block[block_label] = block_revenue
        print(f"\n  -- {block_label} revenue: ${block_revenue:,.2f} --")

    # ── Step 4: Summary report ──────────────────────────────────────
    value_after = get_total_value()

    print("\n" + "=" * 60)
    print("  Simulation Summary")
    print("=" * 60)
    print(f"  Customers served:       {total_customers}")
    print(f"  Total items sold:       {total_items_sold}")
    print(f"  Total revenue:          ${total_revenue:,.2f}")
    print(f"  Failed purchases:       {failed_purchases}")
    print(f"  Inventory value before: ${value_before:,.2f}")
    print(f"  Inventory value after:  ${value_after:,.2f}")
    print(f"  Value decrease:         ${value_before - value_after:,.2f}")

    # Revenue by time block
    print(f"\n  [SALES BY TIME BLOCK]")
    for label, rev in sales_by_time_block.items():
        pct = (rev / total_revenue * 100) if total_revenue else 0
        bar = "#" * int(pct / 2)
        print(f"     {label:<25} ${rev:>8,.2f}  ({pct:4.1f}%)  {bar}")

    # ── Step 5: Low stock alerts ────────────────────────────────────
    low = get_low_stock()
    if low:
        print(f"\n  [!] Low Stock Products ({len(low)} items):")
        for p in low:
            print(f"     {p.name:<20} -- {p.quantity} left")

    # ── Step 6: Post-simulation options ─────────────────────────────
    report_data = {
        "total_revenue": total_revenue,
        "total_items_sold": total_items_sold,
        "total_customers": total_customers,
        "failed_purchases": failed_purchases,
        "value_before": value_before,
        "value_after": value_after,
        "sales_by_product": sales_by_product,
        "low_stock_hits": low_stock_hits,
        "sales_by_time_block": sales_by_time_block,
    }
    post_simulation_menu(report_data)


def print_report(data):
    """Print a detailed report: revenue, most purchased item, and low stock hits."""
    print(f"\n{'=' * 60}")
    print("  Detailed Simulation Report")
    print("=" * 60)

    # Revenue breakdown
    print(f"\n  [REVENUE]")
    print(f"     Total revenue:          ${data['total_revenue']:,.2f}")
    print(f"     Total items sold:       {data['total_items_sold']}")
    print(f"     Failed purchases:       {data['failed_purchases']}")
    print(f"     Inventory value before: ${data['value_before']:,.2f}")
    print(f"     Inventory value after:  ${data['value_after']:,.2f}")
    total_cust = data.get('total_customers', 1)
    avg = data['total_revenue'] / total_cust if total_cust else 0
    print(f"     Avg spend per customer: ${avg:,.2f}")

    # Sales by time block
    time_sales = data.get("sales_by_time_block", {})
    if time_sales:
        print(f"\n  [SALES BY TIME BLOCK]")
        for label, rev in time_sales.items():
            pct = (rev / data['total_revenue'] * 100) if data['total_revenue'] else 0
            bar = "#" * int(pct / 2)
            print(f"     {label:<25} ${rev:>8,.2f}  ({pct:4.1f}%)  {bar}")

    # Most purchased items (top 5)
    sales = data["sales_by_product"]
    if sales:
        sorted_sales = sorted(sales.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  [TOP 5] Most Purchased Items")
        for rank, (name, qty) in enumerate(sorted_sales[:5], 1):
            bar = "\u2588" * qty
            print(f"     {rank}. {name:<20} — {qty} sold  {bar}")

        # Least purchased
        print(f"\n  [BOTTOM] Least Purchased Items")
        for name, qty in sorted_sales[-3:]:
            print(f"     {name:<20} — {qty} sold")

    # Products that hit low stock
    hits = data["low_stock_hits"]
    if hits:
        print(f"\n  [!] Items That Hit Low Stock During Simulation ({len(hits)}):")
        for name in sorted(hits):
            final_qty = sales.get(name, 0)
            print(f"     - {name}")
    else:
        print(f"\n  [OK] No items hit low stock during the simulation.")

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
                print(f"\n  Restocking {len(low)} low-stock items to 50 units...")
                for p in low:
                    restock_amount = 50 - p.quantity
                    if restock_amount > 0:
                        restock(p.id, restock_amount)
                print("  [OK] All low-stock items restocked to 50.")

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
