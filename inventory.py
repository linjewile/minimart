import random
import string
from config import CONFIG


# Each entry holds a product ID (key) and the Product object (value).
class Entry:
    """A single key-value pair stored inside a hash map bucket."""

    def __init__(self, key, value):
        """Create a new entry.

        Args:
            key:   The lookup key (e.g. a product ID string).
            value: The stored value (e.g. a Product object).
        """
        self.key = key
        self.value = value


# Custom hash map using separate chaining for collision handling.
# Buckets is an array of lists — each list holds entries that hash to the same index.
class HashMap:
    """A hash map (dictionary) built from scratch using separate chaining.

    Each bucket is a list of Entry objects. When two keys hash to the
    same index, their entries are appended to the same list (chain).
    Automatically resizes when load factor exceeds the threshold.
    """

    LOAD_FACTOR_THRESHOLD = 0.75  # Resize when count/size exceeds this

    def __init__(self, size=97):
        """Initialise the hash map with a fixed number of buckets.

        Args:
            size: Number of buckets. A prime number is recommended
                  to help distribute keys evenly.
        """
        self.size = size          # Number of buckets in the array
        self.count = 0            # Total number of entries stored
        self.buckets = [[] for _ in range(size)]  # Initialize empty chains

    @property
    def load_factor(self):
        """Return the current load factor (count / size)."""
        return self.count / self.size

    @staticmethod
    def _next_prime(n):
        """Find the next prime number greater than or equal to n.

        Used when resizing to keep bucket count prime for better distribution.
        """
        if n <= 2:
            return 2
        candidate = n if n % 2 != 0 else n + 1
        while True:
            is_prime = True
            for i in range(3, int(candidate ** 0.5) + 1, 2):
                if candidate % i == 0:
                    is_prime = False
                    break
            if is_prime:
                return candidate
            candidate += 2

    def _resize(self):
        """Double the number of buckets and rehash all existing entries.

        Called automatically when load factor exceeds the threshold.
        This reduces chain length and keeps lookups fast.
        """
        old_buckets = self.buckets
        new_size = self._next_prime(self.size * 2)
        self.size = new_size
        self.count = 0
        self.buckets = [[] for _ in range(new_size)]

        # Rehash every entry into the new, larger bucket array
        for bucket in old_buckets:
            for entry in bucket:
                self.set(entry.key, entry.value)

    def collision_stats(self):
        """Return a dict with stats about how evenly keys are distributed.

        Useful for diagnosing whether the hash function is spreading
        keys across buckets or piling them into a few chains.
        """
        chain_lengths = [len(b) for b in self.buckets]
        non_empty = [l for l in chain_lengths if l > 0]
        collisions = sum(1 for l in chain_lengths if l > 1)
        return {
            "total_buckets":    self.size,
            "used_buckets":     len(non_empty),
            "empty_buckets":    self.size - len(non_empty),
            "load_factor":      round(self.load_factor, 3),
            "max_chain_length": max(chain_lengths) if chain_lengths else 0,
            "avg_chain_length": round(sum(non_empty) / len(non_empty), 2) if non_empty else 0,
            "buckets_with_collisions": collisions,
        }

    def _hash(self, key):
        """Convert a string key into a bucket index using a polynomial hash.

        Args:
            key: The string key to hash.

        Returns:
            An integer index in the range [0, self.size).
        """
        total = 0
        for c in key:
            total = total * 31 + ord(c)
        return total % self.size

    def set(self, key, value):
        """Insert a new key-value pair, or update the value if the key exists.

        Automatically resizes the map if the load factor exceeds the
        threshold after insertion, keeping chain lengths short.

        Args:
            key:   The key to store.
            value: The value to associate with the key.
        """
        index = self._hash(key)
        bucket = self.buckets[index]
        for entry in bucket:
            if entry.key == key:
                entry.value = value    # Key exists -- update value
                return
        bucket.append(Entry(key, value))  # Key is new -- add to chain
        self.count += 1

        # Check if we need to resize
        if self.load_factor > self.LOAD_FACTOR_THRESHOLD:
            self._resize()

    def get(self, key):
        """Look up a value by its key.

        Args:
            key: The key to search for.

        Returns:
            The value associated with the key, or None if not found.
        """
        index = self._hash(key)
        bucket = self.buckets[index]
        for entry in bucket:
            if entry.key == key:
                return entry.value
        return None

    def delete(self, key):
        """Remove a key-value pair from the map.

        Args:
            key: The key to remove.

        Returns:
            True if the key was found and removed, False otherwise.
        """
        index = self._hash(key)
        bucket = self.buckets[index]
        for entry in bucket:
            if entry.key == key:
                bucket.remove(entry)   # Remove entry from the chain
                self.count -= 1
                return True
        return False

    def all_entries(self):
        """Yield every Entry in the map by walking all buckets.

        Yields:
            Entry objects, one at a time, across all buckets.
        """
        for bucket in self.buckets:
            for entry in bucket:
                yield entry


# ─── Product ────────────────────────────────────────────────────────

class Product:
    """Represents a single grocery product in the store."""

    def __init__(self, product_id, name, price, quantity, category):
        """Create a new Product.

        Args:
            product_id: Unique ID (e.g. 'MM-K4R2W9').
            name:       Display name of the product.
            price:      Unit price in dollars.
            quantity:   Number of units currently in stock.
            category:   Category label (e.g. 'Dairy', 'Produce').
        """
        self.id = product_id
        self.name = name
        self.price = price
        self.quantity = quantity
        self.category = category

    def __str__(self):
        """Return a formatted string for display in inventory tables."""
        return (f"{self.id:<10} | {self.name:<20} | "
                f"${self.price:<8.2f} | Qty: {self.quantity:<5} | {self.category}")


# ─── ID Generator ──────────────────────────────────────────────────

def generate_id():
    """Generate a random product ID like MM-A3X7K2."""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"MM-{suffix}"


# ─── Inventory Manager ─────────────────────────────────────────────

LOW_STOCK_THRESHOLD = CONFIG["low_stock_threshold"]

inventory = HashMap(CONFIG["inventory_map_size"])
categories = HashMap(CONFIG["categories_map_size"])


# ─── Helper Functions ───────────────────────────────────────────────

def _find_product(product_id):
    """Look up a product by ID, printing an error if not found.

    Args:
        product_id: The product ID to look up.

    Returns:
        The Product object, or None if not found.
    """
    product = inventory.get(product_id)
    if product is None:
        print(f"  [X] Product '{product_id}' not found.")
    return product


def _validate_positive(value, label="Amount"):
    """Check that a value is positive, printing an error if not.

    Args:
        value: The number to validate.
        label: Name shown in the error message.

    Returns:
        True if valid, False otherwise.
    """
    if value <= 0:
        print(f"  [X] {label} must be positive.")
        return False
    return True


def get_all_products():
    """Return a list of every Product currently in the inventory."""
    return [e.value for e in inventory.all_entries()]


def _print_product_list(products, empty_msg="  No products found."):
    """Print a list of products, or a fallback message if empty.

    Args:
        products:  List of Product objects.
        empty_msg: Message to print when the list is empty.
    """
    if products:
        for p in products:
            print(f"  {p}")
    else:
        print(empty_msg)


# ─── CRUD Operations ───────────────────────────────────────────────

def add_product(name, price, quantity, category):
    """Add a new product to the inventory.

    A unique MM-XXXXXX ID is auto-generated. The product is stored in
    the inventory map and its ID is registered under its category.

    Args:
        name:     Product name.
        price:    Unit price (must be >= 0).
        quantity: Starting stock count (must be >= 0).
        category: Category label.

    Returns:
        The generated product ID, or None if validation fails.
    """
    product_id = generate_id()
    if price < 0 or quantity < 0:
        print("  [X] Price and quantity must be non-negative.")
        return None
    product = Product(product_id, name, price, quantity, category)
    inventory.set(product_id, product)
    if categories.get(category) is None:
        categories.set(category, [])
    categories.get(category).append(product_id)
    print(f"  [OK] Added '{name}' with ID: {product_id}")
    return product_id


def purchase(product_id, amount):
    """Reduce stock for a product to simulate a customer purchase.

    Prints a low-stock warning if quantity drops to the threshold.

    Args:
        product_id: The ID of the product to purchase.
        amount:     Number of units to buy (must be > 0).
    """
    product = _find_product(product_id)
    if product is None or not _validate_positive(amount):
        return
    if product.quantity < amount:
        print(f"  [X] Insufficient stock. Available: {product.quantity}")
        return
    product.quantity -= amount
    print(f"  [OK] Purchased {amount}x {product.name}. Remaining: {product.quantity}")
    if product.quantity <= LOW_STOCK_THRESHOLD:
        print(f"  [!] Low stock alert: {product.name} ({product.quantity} left)")


def restock(product_id, amount):
    """Increase stock for a product.

    Args:
        product_id: The ID of the product to restock.
        amount:     Number of units to add (must be > 0).
    """
    product = _find_product(product_id)
    if product is None or not _validate_positive(amount):
        return
    product.quantity += amount
    print(f"  [OK] Restocked {product.name}. New quantity: {product.quantity}")


def remove_product(product_id):
    """Remove a product from the inventory and its category listing.

    Args:
        product_id: The ID of the product to remove.
    """
    product = _find_product(product_id)
    if product is None:
        return
    cat_list = categories.get(product.category)
    if cat_list and product_id in cat_list:
        cat_list.remove(product_id)
    inventory.delete(product_id)
    print(f"  [OK] Removed '{product.name}'")


def update_price(product_id, new_price):
    """Change the unit price of a product.

    Args:
        product_id: The ID of the product.
        new_price:  The new price (must be >= 0).
    """
    product = _find_product(product_id)
    if product is None:
        return
    if new_price < 0:
        print("  [X] Price must be non-negative.")
        return
    old_price = product.price
    product.price = new_price
    print(f"  [OK] Updated {product.name}: ${old_price:.2f} -> ${new_price:.2f}")


def get_products_by_category(category):
    """Return a list of Product objects that belong to the given category.

    Args:
        category: The category label to filter by.

    Returns:
        A list of Product objects, or an empty list if none found.
    """
    product_ids = categories.get(category)
    if not product_ids:
        return []
    return [p for pid in product_ids if (p := inventory.get(pid)) is not None]


def search_by_name(name):
    """Search for products whose name contains the given substring (case-insensitive).

    Args:
        name: The search term.

    Returns:
        A list of matching Product objects.
    """
    term = name.lower()
    return [e.value for e in inventory.all_entries() if term in e.value.name.lower()]


def get_low_stock():
    """Return all products whose quantity is at or below LOW_STOCK_THRESHOLD."""
    return [e.value for e in inventory.all_entries()
            if e.value.quantity <= LOW_STOCK_THRESHOLD]


def get_total_value():
    """Calculate the total dollar value of all products in the inventory."""
    return sum(e.value.price * e.value.quantity for e in inventory.all_entries())


def get_total_quantity():
    """Return the total number of units across all products in the inventory."""
    return sum(e.value.quantity for e in inventory.all_entries())


def print_inventory():
    """Print a formatted table of every product currently in the inventory."""
    if inventory.count == 0:
        print("  (inventory is empty)")
        return
    print(f"  {'ID':<10} | {'Name':<20} | {'Price':<9} | {'Qty':<9} | Category")
    print("  " + "-" * 70)
    for entry in inventory.all_entries():
        print(f"  {entry.value}")
    print("  " + "-" * 70)
    print(f"  Total Products: {inventory.count}")
    print(f"  Total Units:    {get_total_quantity()}")
    print(f"  Total Value:    ${get_total_value():,.2f}")


# ─── Seed Inventory ────────────────────────────────────────────────

def seed_inventory():
    """Manually add starting products to the inventory."""
    # Dairy
    add_product("Whole Milk",         3.00, 120, "Dairy")
    add_product("Cheddar Cheese",     2.50,  45, "Dairy")
    add_product("Greek Yogurt",       2.50,  80, "Dairy")
    add_product("Butter",             1.75,  60, "Dairy")
    # Produce
    add_product("Bananas",            0.50, 200, "Produce")
    add_product("Avocados",           2.50,  60, "Produce")
    add_product("Baby Oranges",       4.00,  35, "Produce")
    add_product("Strawberries",       3.00,  40, "Produce")
    add_product("Broccoli",           2.00,  50, "Produce")
    add_product("Russett Potatoes",   0.79, 130, "Produce")
    # Meat
    add_product("Chicken Breast",     6.00,  50, "Meat")
    add_product("Ground Beef",        6.00,  40, "Meat")
    add_product("Salmon Fillet",      7.50,  25, "Meat")
    add_product("Glizzy",             4.00,  30, "Meat")
    add_product("Steak",             10.00,  35, "Meat")
    # Bakery
    add_product("Sourdough Bread",    4.00,  30, "Bakery")
    add_product("Croissants",         4.00,  25, "Bakery")
    add_product("Bagels",             4.00,  50, "Bakery")
    # Beverages
    add_product("Orange Juice",       4.00,  55, "Beverages")
    add_product("Water Case",         4.00,  15, "Beverages")
    add_product("Sparkling Water",    2.00, 150, "Beverages")
    add_product("Apple Juice",        4.00,  40, "Beverages")
    # Pantry
    add_product("Pasta",              2.00,  90, "Pantry")
    add_product("Olive Oil",          8.00,  20, "Pantry")
    add_product("Rice",               4.00,  70, "Pantry")
    add_product("Canned Beans",       2.00,  85, "Pantry")
    # Snacks
    add_product("Granola Bars",       4.00,  30, "Snacks")
    add_product("Potato Chips",       4.00,  55, "Snacks")
    add_product("Trail Mix",          6.00,  30, "Snacks")
    add_product("Gushers",            1.00,  40, "Snacks")
    # Desserts
    add_product("Chocolate Cake",     6.00,  15, "Desserts")
    add_product("Ice Cream",          4.00,  40, "Desserts")
    add_product("MY Style Strawberry Cheesecake", 7.00, 12, "Desserts")
    add_product("Brownies",           4.00,  20, "Desserts")
    add_product("Cookies",            1.50,  30, "Desserts")
    # Frozen
    add_product("Frozen Pizza",       5.00,  25, "Frozen")
    add_product("Frozen Vegetables",  3.00,  60, "Frozen")
    add_product("TV Dinner",          3.00,  40, "Frozen")
    add_product("Orange Chicken",     4.00,  30, "Frozen")
    # Household
    add_product("Paper Towels",       5.00,  20, "Household")
    add_product("Toilet Paper",       5.00,  25, "Household")
    add_product("Laundry Detergent",  6.50,  15, "Household")
    add_product("Dish Soap",          3.00,  30, "Household")
    add_product("Trash Bags",         5.00,  20, "Household")
    add_product("Aluminum Foil",      2.00,  50, "Household")


def _print_map_stats(label, hash_map):
    """Print collision stats for a single hash map.

    Args:
        label:    Display name for the map (e.g. 'INVENTORY MAP').
        hash_map: The HashMap instance to report on.
    """
    print(f"\n  [{label}]")
    for key, val in hash_map.collision_stats().items():
        print(f"     {key:<28} {val}")


def print_collision_stats():
    """Print hash map diagnostic info for inventory and categories maps."""
    _print_map_stats("INVENTORY MAP", inventory)
    _print_map_stats("CATEGORIES MAP", categories)


# ─── Menu Loop ──────────────────────────────────────────────────────

def menu():
    """Run the interactive menu loop for the Mini Meijer inventory system."""
    seed_inventory()
    print("\n" + "=" * 50)
    print("   Grocery Store Inventory Manager")
    print("=" * 50)

    while True:
        print("\n  1. View Inventory")
        print("  2. Add Product")
        print("  3. Purchase (reduce stock)")
        print("  4. Restock")
        print("  5. Update Price")
        print("  6. Remove Product")
        print("  7. Search by Name")
        print("  8. View by Category")
        print("  9. Low Stock Report")
        print("  10. Total Inventory Value")
        print("  11. Hash Map Stats")
        print("  0. Exit")

        choice = input("\n  Enter choice: ").strip()

        if choice == "1":
            print()
            print_inventory()

        elif choice == "2":
            name     = input("  Name: ").strip()
            price    = float(input("  Price: "))
            quantity = int(input("  Quantity: "))
            category = input("  Category: ").strip()
            add_product(name, price, quantity, category)

        elif choice == "3":
            pid    = input("  Product ID: ").strip()
            amount = int(input("  Amount to purchase: "))
            purchase(pid, amount)

        elif choice == "4":
            pid    = input("  Product ID: ").strip()
            amount = int(input("  Amount to restock: "))
            restock(pid, amount)

        elif choice == "5":
            pid   = input("  Product ID: ").strip()
            price = float(input("  New price: "))
            update_price(pid, price)

        elif choice == "6":
            pid = input("  Product ID: ").strip()
            remove_product(pid)

        elif choice == "7":
            name = input("  Search name: ").strip()
            _print_product_list(search_by_name(name), "  No matches found.")

        elif choice == "8":
            cat = input("  Category: ").strip()
            _print_product_list(get_products_by_category(cat),
                                "  No products in that category.")

        elif choice == "9":
            low = get_low_stock()
            if low:
                print(f"  Products at or below {LOW_STOCK_THRESHOLD} units:")
                for p in low:
                    print(f"  [!] {p}")
            else:
                print("  All products are well stocked.")

        elif choice == "10":
            total = get_total_value()
            print(f"  Total inventory value: ${total:,.2f}")

        elif choice == "11":
            print_collision_stats()

        elif choice == "0":
            print("  Goodbye!")
            break

        else:
            print("  Invalid choice. Try again.")


if __name__ == "__main__":
    menu()
