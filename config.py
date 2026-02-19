"""
config.py
─────────
Central configuration for the Mini Meijer inventory system.
All tuneable thresholds, schedules, demographic data, and warehouse
settings live here so every module pulls from one source of truth.
"""

CONFIG = {

    # ─── Inventory Thresholds ───────────────────────────────────────
    "low_stock_threshold":   10,   # Products at or below this trigger alerts
    "restock_target":        50,   # Overnight restock fills items up to this
    "delivery_restock_max":  25,   # Only deliver to items at or below this qty
    "high_stock_threshold":  50,   # Items above this on Friday get sale flagged
    "sale_discount":         0.50, # Fraction off (0.50 = 50% off)

    # ─── HashMap Sizing ────────────────────────────────────────────
    "inventory_map_size":    97,   # Initial bucket count for inventory map
    "categories_map_size":   31,   # Initial bucket count for categories map

    # ─── Simulation Timing ─────────────────────────────────────────
    "delay_between":         0.15, # Seconds between customers (terminal sim)
    "gui_delay":             0.05, # Seconds between customers (GUI sim)

    # ─── Week Schedule ─────────────────────────────────────────────
    "day_names": [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ],

    "day_traffic": {
        "Monday":    0.8,
        "Tuesday":   0.9,
        "Wednesday": 0.85,
        "Thursday":  0.95,
        "Friday":    1.1,
        "Saturday":  1.4,
        "Sunday":    1.2,
    },

    "delivery_days": ["Monday", "Thursday"],

    # ─── Warehouse Stock (units per delivery per category) ─────────
    "warehouse_stock": {
        "Dairy":      60,
        "Produce":    80,
        "Meat":       40,
        "Bakery":     50,
        "Beverages":  70,
        "Pantry":     60,
        "Snacks":     40,
        "Desserts":   30,
    },

    # ─── Time-of-Day Blocks ────────────────────────────────────────
    "time_blocks": [
        {"label": "Morning (7am - 9am)",   "hours": "7:00 - 9:00",   "customers": 8,  "max_cart": 4},
        {"label": "Midday (11am - 1pm)",   "hours": "11:00 - 13:00", "customers": 5,  "max_cart": 3},
        {"label": "Evening (4pm - 7pm)",   "hours": "16:00 - 19:00", "customers": 12, "max_cart": 6},
        {"label": "Night (8pm - 10pm)",    "hours": "20:00 - 22:00", "customers": 3,  "max_cart": 3},
    ],

    # ─── Purchase Amount Weights ───────────────────────────────────
    "purchase_tiers": [
        {"chance": 60, "min": 1,  "max": 3},   # Normal purchase
        {"chance": 30, "min": 4,  "max": 6},   # Occasional bulk
        {"chance": 10, "min": 7,  "max": 12},  # Rare large purchase
    ],

    # ─── Shopper Profiles ──────────────────────────────────────────
    "shopper_profiles": {
        "Stay-at-Home Parent": {
            "age_range":    (25, 45),
            "time_weights":  [8, 3, 1, 0],
            "basket_size":   (3, 6),          # Family shopper -- bigger carts
            "price_threshold": 6.00,           # Budget-conscious, avoids pricey items
            "skip_chance":   0.60,             # 60% chance to skip items above threshold
            "category_weights": {
                "Dairy": 8, "Bakery": 7, "Produce": 7, "Beverages": 5,
                "Meat": 6, "Pantry": 8, "Snacks": 5, "Desserts": 4, "Household": 3,
            },
        },
        "Retired": {
            "age_range":    (60, 80),
            "time_weights":  [3, 8, 2, 0],
            "basket_size":   (2, 4),          # Smaller, frequent trips
            "price_threshold": 5.00,           # Fixed income, price-sensitive
            "skip_chance":   0.70,             # 70% chance to skip expensive items
            "category_weights": {
                "Dairy": 7, "Bakery": 8, "Produce": 9, "Beverages": 6,
                "Meat": 5, "Pantry": 7, "Snacks": 3, "Desserts": 4, "Household": 2,
            },
        },
        "Student": {
            "age_range":    (18, 25),
            "time_weights":  [1, 2, 8, 5],
            "basket_size":   (1, 5),          # Tight budget, small trips
            "price_threshold": 6.00,           # Very price-sensitive
            "skip_chance":   0.80,             # 80% chance to skip pricey items
            "category_weights": {
                "Dairy": 4, "Bakery": 5, "Produce": 2, "Beverages": 8,
                "Meat": 3, "Pantry": 7, "Snacks": 9, "Desserts": 7, "Household": 1,
            },
        },
        "Office Worker": {
            "age_range":    (25, 55),
            "time_weights":  [1, 1, 9, 2],
            "basket_size":   (2, 10),          # Moderate cart, after-work run
            "price_threshold": 10.00,           # Comfortable income
            "skip_chance":   0.30,             # 30% chance to skip premium items
            "category_weights": {
                "Dairy": 6, "Bakery": 4, "Produce": 7, "Beverages": 5,
                "Meat": 8, "Pantry": 7, "Snacks": 4, "Desserts": 5, "Household": 3,
            },
        },
        "Trade Worker": {
            "age_range":    (22, 55),
            "time_weights":  [5, 1, 7, 1],
            "basket_size":   (2, 9),          # Moderate, quick grab-and-go
            "price_threshold": 8.00,           # Decent income, somewhat price-aware
            "skip_chance":   0.40,             # 40% chance to skip expensive items
            "category_weights": {
                "Dairy": 5, "Bakery": 2, "Produce": 4, "Beverages": 10,
                "Meat": 8, "Pantry": 6, "Snacks": 6, "Desserts": 3, "Household": 1,
            },
        },
        "Night Shift": {
            "age_range":    (20, 50),
            "time_weights":  [4, 0, 1, 8],
            "basket_size":   (1, 4),          # Quick late-night stops
            "price_threshold": 5.00,           # Moderate income, watches prices
            "skip_chance":   0.50,             # 50% chance to skip pricey items
            "category_weights": {
                "Dairy": 5, "Bakery": 3, "Produce": 3, "Beverages": 8,
                "Meat": 4, "Pantry": 5, "Snacks": 8, "Desserts": 1, "Household": 2,
            },
        },
    },

    # ─── Profession → Profile Mapping ──────────────────────────────
    "profession_to_profile": {
        # Office Worker ─────────────────────────────────────────────
        "Teacher":              "Office Worker",
        "Software Engineer":    "Office Worker",
        "Accountant":           "Office Worker",
        "Pharmacist":           "Office Worker",
        "Graphic Designer":     "Office Worker",
        "Data Analyst":         "Office Worker",
        "Lawyer":               "Office Worker",
        "Dentist":              "Office Worker",
        "Social Worker":        "Office Worker",
        "Doctor":               "Office Worker",
        "Salesperson":          "Office Worker",
        "Freelancer":           "Office Worker",
        "Administrator":        "Office Worker",
        "Researcher":           "Office Worker",
        "Veterinarian":         "Office Worker",
        "Journalist":           "Office Worker",
        "Author":               "Office Worker",
        "Scientist":            "Office Worker",
        "Small Business Owner": "Office Worker",
        # Trade Worker ──────────────────────────────────────────────
        "Electrician":          "Trade Worker",
        "Mechanic":             "Trade Worker",
        "Plumber":              "Trade Worker",
        "Construction Worker":  "Trade Worker",
        "Barber":               "Trade Worker",
        "Braider":              "Trade Worker",
        "Cashier":              "Trade Worker",
        "Retail Manager":       "Trade Worker",
        "Postman":              "Trade Worker",
        "Receptionist":         "Trade Worker",
        "Landscape Worker":     "Trade Worker",
        "Coach":                "Trade Worker",
        "Athlete":              "Trade Worker",
        # Night Shift ──────────────────────────────────────────────
        "Nurse":                "Night Shift",
        "Chef":                 "Night Shift",
        "Firefighter":          "Night Shift",
        "Truck Driver":         "Night Shift",
        "Warehouse Associate":  "Night Shift",
        "Security Guard":       "Night Shift",
        "Police Officer":       "Night Shift",
        "Flight Attendant":     "Night Shift",
        "Pilot":                "Night Shift",
        # Student ──────────────────────────────────────────────────
        "Student":              "Student",
        "Podcaster":            "Student",
        "Artist":               "Student",
        "Musician":             "Student",
        # Retired ──────────────────────────────────────────────────
        "Retired":              "Retired",
        # Stay-at-Home Parent ──────────────────────────────────────
        "Stay-at-Home Parent":  "Stay-at-Home Parent",
    },

    # ─── Profession List (for random customer generation) ──────────
    "professions": [
        "Teacher", "Nurse", "Software Engineer", "Electrician", "Accountant",
        "Chef", "Mechanic", "Pharmacist", "Graphic Designer", "Data Analyst", "Retail Manager","Postman", "Receptionist", 
        "Cashier", "Construction Worker", "Dentist", "Firefighter", "Barber", "Braider",
        "Social Worker", "Truck Driver", "Plumber", "Retail Manager", "Student", "Researcher",
        "Retired", "Freelancer", "Doctor", "Salesperson", "Warehouse Associate","Podcaster",
        "Stay-at-Home Parent", "Administrator", "Security Guard", "Police Officer","Lawyer",
        "Small Business Owner", "Artist", "Musician", "Scientist", "Athlete", "Coach", "Landscape Worker", "Veterinarian", "Flight Attendant", "Pilot", "Journalist", "Author",
    ],

    # ─── Customer Name Pools ───────────────────────────────────────
    "first_names": [
        "Chloe", "Temi", "Jazlyn", "Noah", "Jacque", "James", "Daniela", "Omar",
        "Diana", "Carolina", "Isabella", "Malhar", "Arafat", "Logan", "Jenicka",
        "Aiden", "Harper", "Elijah", "Angel", "Ben", "Grace", "Caleb",
        "Lily", "Sayna", "Deni", "Ryan", "Safa", "Leo", "Amora", "Dylan",
        "Aaliyah", "Marcus", "Yvonne", "Li", "Priya", "Ariel", "Paul",
        "Darnell", "Keiko", "Rachel", "Ingrid", "Benito", "Jeison", "Kofi",
        "Princess", "Hesler", "Brittney", "Dante", "Manuel", "Ashley", "Jake",
        "Toure", "Rosa", "Tariq", "Simone", "Andrei", "Elisa", "Digna",
        "Elena", "Noel", "Valentina", "Raj", "Asia", "Jorge", "Bianca",
        "Mohammed", "Monique", "Jin", "Camila", "Charlie", "Leila","Markelis"
    ],

    "last_names": [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Martinez", "Lopez", "Wilson", "Anderson", "Thomas", "Tepic",
        "Lee", "Kim", "Toliver", "Patel", "Figueroa", "Wang", "Jackson", "Matthews",
        "Harris", "Howard", "Robinson", "Walker", "Hall", "Young", "King","Modi","Blackburn",
        "Wright", "Torres", "Rivera", "Evans", "Okafor", "Yamamoto", "Singh","Terry","Kirk", "Santiago",
        "Johansson", "Moore", "Alvarado", "Linjewile","McKnight", "Black","Craig"
    ],

    "races": [
        "White", "Black", "Hispanic", "Asian", "Arab",
        "Native American", "Pacific Islander", "Multiracial",
    ],
}
