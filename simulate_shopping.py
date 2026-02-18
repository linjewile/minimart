"""
simulate_shopping.py
────────────────────
Simulates random customers shopping at Mini Meijer.
Each customer grabs 1-5 random products, buying 1-3 units of each.
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
# Each block: (label, hour range, number of customers, max cart size,
#              list of categories that sell more during this window)

TIME_BLOCKS = [
    {
        "label":      "Morning (7am - 9am)",
        "hours":      "7:00 - 9:00",
        "customers":  8,
        "max_cart":   4,
        "popular":    ["Dairy", "Bakery", "Beverages"],
    },
    {
        "label":      "Midday (11am - 1pm)",
        "hours":      "11:00 - 13:00",
        "customers":  5,
        "max_cart":   3,
        "popular":    ["Snacks", "Beverages", "Bakery"],
    },
    {
        "label":      "Evening (4pm - 7pm)",
        "hours":      "16:00 - 19:00",
        "customers":  12,
        "max_cart":   6,
        "popular":    ["Meat", "Produce", "Dairy", "Pantry", "Desserts"],
    },
    {
        "label":      "Night (8pm - 10pm)",
        "hours":      "20:00 - 22:00",
        "customers":  3,
        "max_cart":   3,
        "popular":    ["Snacks", "Desserts", "Beverages"],
    },
]


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
    "Emma", "Liam", "Olivia", "Noah", "Ava", "James", "Sophia", "Lucas",
    "Mia", "Ethan", "Isabella", "Mason", "Charlotte", "Logan", "Amelia",
    "Aiden", "Harper", "Elijah", "Ella", "Ben", "Grace", "Caleb",
    "Lily", "Jack", "Zoe", "Ryan", "Nora", "Leo", "Chloe", "Dylan",
    "Aaliyah", "Marcus", "Fatima", "Wei", "Priya", "Carlos", "Yuki",
    "Darnell", "Keiko", "Rashid", "Ingrid", "Tomás", "Mei-Ling", "Kofi",
    "Sasha", "Jamal", "Ananya", "Dante", "Luz", "Hiroshi", "Amara",
    "Devon", "Rosa", "Tariq", "Simone", "Andrei", "Jasmine", "Omar",
    "Elena", "Kwame", "Valentina", "Raj", "Aisha", "Jorge", "Bianca",
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
    "White", "Black", "Hispanic", "Asian", "Middle Eastern",
    "Native American", "Pacific Islander", "Multiracial"
]

PROFESSIONS = [
    "Teacher", "Nurse", "Software Engineer", "Electrician", "Accountant",
    "Chef", "Mechanic", "Pharmacist", "Graphic Designer", "Lawyer",
    "Cashier", "Construction Worker", "Dentist", "Firefighter", "Barber",
    "Social Worker", "Truck Driver", "Plumber", "Retail Manager", "Student",
    "Retired", "Freelancer", "Doctor", "Salesperson", "Warehouse Associate"
]


class Customer:
    """Represents a randomly-generated shopper with demographic info."""

    def __init__(self):
        self.first_name = random.choice(FIRST_NAMES)
        self.last_name = random.choice(LAST_NAMES)
        self.age = random.randint(18, 80)
        self.race = random.choice(RACES)
        self.profession = random.choice(PROFESSIONS)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return (f"{self.full_name}, Age {self.age}, "
                f"{self.race}, {self.profession}")


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
    for block in TIME_BLOCKS:
        block_label = block["label"]
        block_customers = block["customers"]
        block_max_cart = block["max_cart"]
        popular_categories = block["popular"]
        block_revenue = 0.0

        print("\n" + "=" * 60)
        print(f"  TIME BLOCK: {block_label}")
        print(f"  Hours: {block['hours']}  |  Expected customers: {block_customers}")
        print("=" * 60)

        for j in range(1, block_customers + 1):
            customer_num += 1
            customer = Customer()
            products = get_all_products()

            if not products:
                print("  [!] No products left in stock!")
                break

            # Bias product selection toward popular categories for this time block
            popular_products = [p for p in products if p.category in popular_categories]
            other_products = [p for p in products if p.category not in popular_categories]

            # 70% of cart from popular categories, 30% from others
            num_items = random.randint(1, min(block_max_cart, len(products)))
            num_popular = max(1, int(num_items * 0.7))
            num_other = num_items - num_popular

            cart = []
            if popular_products:
                cart += random.sample(popular_products, min(num_popular, len(popular_products)))
            if other_products and num_other > 0:
                cart += random.sample(other_products, min(num_other, len(other_products)))

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
