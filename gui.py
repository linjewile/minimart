"""
gui.py
──────
Tkinter GUI for Mini Meijer grocery store simulation.
Provides a windowed interface with tabs for:
  - Inventory  (full product table with search/filter)
  - Simulation Log  (scrollable feed of every transaction)
  - Warehouse  (stock per category + daily reports)
  - Customer Activity  (real-time shopper panel)
  - Low Stock  (products that need restocking)
  - Report     (detailed sales breakdown)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
import time
import threading

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (render to image)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from config import CONFIG
from inventory import (
    seed_inventory, inventory, purchase, restock,
    get_low_stock, get_total_value, get_all_products
)
from simulate_shopping import (
    TIME_BLOCKS, SHOPPER_PROFILES, Customer,
    get_profile_for_time_block, pick_products_by_preference,
    random_purchase_amount, DAY_NAMES, DAY_TRAFFIC,
    DELIVERY_DAYS, WAREHOUSE_STOCK,
    friday_sale_suggestions, apply_sales,
    HIGH_STOCK_THRESHOLD, SALE_DISCOUNT,
    RESTOCK_TARGET, DELIVERY_RESTOCK_MAX,
    ALCOHOL_SURGE_RATES, HIGH_TRAFFIC_BLOCKS
)


# ─── Color Palette (Light Pastel) ────────────────────────────────────

BG          = "#f5f0e6"      # Warm cream background
BG_CARD     = "#ffffff"      # White card/panel
FG          = "#1a1a1a"      # Dark text
FG_DIM      = "#7a7a7a"      # Dimmed text
ACCENT      = "#2d6a4f"      # Deep sage green accent
GREEN       = "#52b788"      # Fresh green / success
RED         = "#d45d5d"      # Soft red / error
YELLOW      = "#e8b931"      # Warm gold / warning
PURPLE      = "#7b68a8"      # Soft purple
TEAL        = "#3d9e8f"      # Teal secondary
HEADER_BG   = "#eae5d9"      # Table header bg
ROW_ALT     = "#f9f6f0"      # Alternating row bg
SIDEBAR_BG  = "#1a1a2e"      # Dark sidebar
PEACH       = "#f0c9a6"      # Soft peach accent
MINT        = "#c8e6c0"      # Mint green accent
CREAM_CARD  = "#fdf8ef"      # Cream card variant
BORDER      = "#e0dbd0"      # Subtle card border

FONT        = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_HEADER = ("Courier New", 15, "bold")
FONT_TITLE  = ("Courier New", 20, "bold")
FONT_MONO   = ("Cascadia Mono", 10)
FONT_SMALL  = ("Segoe UI", 9)


# ─── Main Application ──────────────────────────────────────────────

class MiniMeijerApp:
    """Main GUI application for Mini Meijer."""

    def __init__(self, root):
        self.root = root
        self.root.title("Mini Meijer - Grocery Store Simulator")
        self.root.geometry("1100x750")
        self.root.configure(bg=BG)
        self.root.minsize(900, 600)

        # Simulation data storage
        self.sim_log = []            # List of log strings
        self.report_data = None      # Dict of report stats
        self.sim_running = False
        self.sim_speed = tk.IntVar(value=10)  # Speed level 1-20 (10 = default)

        # Style configuration
        self._setup_styles()

        # Header bar
        self._build_header()

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 0))

        # Build each tab
        self._build_blueprint_tab()
        self._build_inventory_tab()
        self._build_simulation_tab()
        self._build_warehouse_tab()
        self._build_activity_tab()
        self._build_low_stock_tab()
        self._build_report_tab()

        # Bottom inventory status bar
        self._build_bottom_bar()

    # ─── Styles ─────────────────────────────────────────────────────

    def _setup_styles(self):
        """Configure ttk styles for a light pastel theme."""
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook
        style.configure("Dark.TNotebook", background=BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                         background=BG_CARD, foreground=FG_DIM,
                         padding=[16, 8], font=FONT_BOLD)
        style.map("Dark.TNotebook.Tab",
                   background=[("selected", MINT)],
                   foreground=[("selected", ACCENT)])

        # Frames
        style.configure("Dark.TFrame", background=BG)
        style.configure("Card.TFrame", background=BG_CARD)

        # Labels
        style.configure("Dark.TLabel", background=BG, foreground=FG, font=FONT)
        style.configure("Card.TLabel", background=BG_CARD, foreground=FG, font=FONT)
        style.configure("Header.TLabel", background=BG, foreground=ACCENT, font=FONT_HEADER)

        # Buttons
        style.configure("Accent.TButton",
                         background=ACCENT, foreground="#ffffff",
                         font=FONT_BOLD, padding=[12, 6])
        style.map("Accent.TButton",
                   background=[("active", TEAL)])

        style.configure("Green.TButton",
                         background=GREEN, foreground="#ffffff",
                         font=FONT_BOLD, padding=[12, 6])
        style.map("Green.TButton",
                   background=[("active", TEAL)])

        style.configure("Red.TButton",
                         background=RED, foreground="#ffffff",
                         font=FONT_BOLD, padding=[12, 6])

        # Treeview (tables)
        style.configure("Dark.Treeview",
                         background=BG_CARD, foreground=FG,
                         fieldbackground=BG_CARD, font=FONT,
                         rowheight=28, borderwidth=0)
        style.configure("Dark.Treeview.Heading",
                         background=HEADER_BG, foreground=ACCENT,
                         font=FONT_BOLD, borderwidth=0)
        style.map("Dark.Treeview",
                   background=[("selected", MINT)],
                   foreground=[("selected", ACCENT)])

        # Entry
        style.configure("Dark.TEntry",
                         fieldbackground=BG_CARD, foreground=FG,
                         insertcolor=FG, font=FONT)

        # Progressbar
        style.configure("BP.Horizontal.TProgressbar",
                         troughcolor=HEADER_BG, background=GREEN)

        # Scrollbar
        style.configure("TScrollbar",
                         background=HEADER_BG, troughcolor=BG,
                         arrowcolor=FG_DIM)

    # ─── Header ─────────────────────────────────────────────────────

    def _build_header(self):
        """Build the title bar at the top."""
        header = tk.Frame(self.root, bg=SIDEBAR_BG, height=60)
        header.pack(fill=tk.X, padx=0, pady=(0, 0))

        tk.Label(header, text="  🛒  Mini Meijer", font=FONT_TITLE,
                 bg=SIDEBAR_BG, fg="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(header, text="Grocery Store Simulator", font=FONT,
                 bg=SIDEBAR_BG, fg="#8888aa").pack(side=tk.LEFT, padx=(10, 0), pady=(6, 0))

        # Run Simulation button (right side)
        self.run_btn = tk.Button(
            header, text="▶  Run Simulation", font=FONT_BOLD,
            bg=GREEN, fg="#ffffff", activebackground=TEAL, activeforeground="#ffffff",
            relief=tk.FLAT, padx=16, pady=6,
            command=self._start_simulation
        )
        self.run_btn.pack(side=tk.RIGHT, padx=(0, 12))

        # Load Inventory button
        self.load_btn = tk.Button(
            header, text="📦  Load Inventory", font=FONT_BOLD,
            bg=ACCENT, fg="#ffffff", activebackground=TEAL, activeforeground="#ffffff",
            relief=tk.FLAT, padx=16, pady=6,
            command=self._load_inventory
        )
        self.load_btn.pack(side=tk.RIGHT, padx=(0, 10))

        # Speed control slider
        speed_frame = tk.Frame(header, bg=SIDEBAR_BG)
        speed_frame.pack(side=tk.RIGHT, padx=(0, 20))

        tk.Label(speed_frame, text="Speed:", font=FONT_SMALL,
                 bg=SIDEBAR_BG, fg="#8888aa").pack(side=tk.LEFT)

        self.speed_label = tk.Label(speed_frame, text="10x", font=FONT_BOLD,
                                    bg=SIDEBAR_BG, fg=MINT, width=4)
        self.speed_label.pack(side=tk.RIGHT, padx=(4, 0))

        self.speed_slider = tk.Scale(
            speed_frame, from_=1, to=20, orient=tk.HORIZONTAL,
            variable=self.sim_speed, showvalue=False,
            bg=SIDEBAR_BG, fg="#ffffff", troughcolor="#2a2a4e", highlightthickness=0,
            activebackground=MINT, sliderrelief=tk.FLAT, length=120,
            command=lambda v: self.speed_label.config(text=f"{v}x")
        )
        self.speed_slider.pack(side=tk.LEFT, padx=(4, 0))

    # ─── Tab 1: Store Blueprint ─────────────────────────────────────

    # Blueprint colour constants (light pastel)
    BP_BG       = "#f5f0e6"
    BP_GRID     = "#ebe6dc"
    BP_BORDER   = "#2d6a4f"
    BP_SECTION  = "#ffffff"
    BP_TEXT     = "#1a1a1a"
    BP_DIM      = "#7a7a7a"
    BP_ENTRANCE = "#eae5d9"
    BP_AISLE    = "#e0dbd0"
    BP_WALL     = "#d5d0c4"

    def _build_blueprint_tab(self):
        """Build the store blueprint floor plan tab."""
        frame = tk.Frame(self.notebook, bg=self.BP_BG)
        self.notebook.add(frame, text="  Store Map  ")

        self.bp_canvas = tk.Canvas(frame, bg=self.BP_BG, highlightthickness=0)
        self.bp_canvas.pack(fill=tk.BOTH, expand=True)

        # Redraw on resize
        self.bp_canvas.bind("<Configure>", lambda e: self._refresh_blueprint())

    def _get_category_stock(self, category):
        """Return (total_qty, num_products) for a category."""
        prods = [e.value for e in inventory.all_entries()
                 if e.value.category == category]
        return sum(p.quantity for p in prods), len(prods)

    def _stock_color(self, total_qty):
        """Return (fill_colour, text_colour) based on stock level."""
        if total_qty == 0:
            return "#fde8e8", RED
        elif total_qty < 30:
            return "#fef3e0", RED
        elif total_qty < 100:
            return "#fef9e7", YELLOW
        else:
            return self.BP_SECTION, GREEN

    def _draw_section(self, canvas, x, y, w, h, category, vertical_text=False):
        """Draw a single store section box with live stock data."""
        total_qty, num_items = self._get_category_stock(category)
        fill, qty_color = self._stock_color(total_qty)

        canvas.create_rectangle(x, y, x + w, y + h,
                                fill=fill, outline=self.BP_BORDER, width=1.5)

        cx, cy = x + w / 2, y + h / 2

        if vertical_text and h > w * 1.5:
            # Vertical layout for tall narrow sections
            canvas.create_text(cx, cy - h * 0.25,
                               text=category.upper(),
                               fill=self.BP_TEXT,
                               font=("Cascadia Mono", 8, "bold"))
            canvas.create_text(cx, cy,
                               text=str(total_qty),
                               fill=qty_color,
                               font=("Cascadia Mono", 16, "bold"))
            canvas.create_text(cx, cy + h * 0.20,
                               text=f"{num_items}p",
                               fill=self.BP_DIM,
                               font=("Cascadia Mono", 7))
        else:
            # Horizontal layout
            name_size = 8 if len(category) > 10 else 9
            canvas.create_text(cx, cy - h * 0.28,
                               text=category.upper(),
                               fill=self.BP_TEXT,
                               font=("Cascadia Mono", name_size, "bold"))
            qty_size = 14 if w < 120 else 18
            canvas.create_text(cx, cy + h * 0.02,
                               text=str(total_qty),
                               fill=qty_color,
                               font=("Cascadia Mono", qty_size, "bold"))
            canvas.create_text(cx, cy + h * 0.30,
                               text=f"{num_items} products",
                               fill=self.BP_DIM,
                               font=("Cascadia Mono", 7))

    def _refresh_blueprint(self):
        """Redraw a realistic grocery store floor plan."""
        canvas = self.bp_canvas
        canvas.delete("all")

        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W < 400 or H < 350:
            return

        # ── Blueprint grid ─────────────────────────────────────────
        for gx in range(0, W, 25):
            canvas.create_line(gx, 0, gx, H, fill=self.BP_GRID)
        for gy in range(0, H, 25):
            canvas.create_line(0, gy, W, gy, fill=self.BP_GRID)

        # ── Geometry ───────────────────────────────────────────────
        M = 25                            # margin
        title_h = 36
        legend_h = 24
        sx, sy = M, M + title_h          # store top-left
        sw = W - 2 * M                   # store width
        sh = H - 2 * M - title_h - legend_h  # store height

        # Proportions
        wall_d = sh * 0.14               # perimeter dept depth
        ck_h   = sh * 0.12               # checkout zone height
        aisle_gap = 8                     # gap between aisle shelves
        entrance_w = sw * 0.25           # entrance door width

        # Inner shopping area
        inner_x = sx + wall_d
        inner_y = sy + wall_d
        inner_w = sw - 2 * wall_d
        inner_h = sh - wall_d - ck_h

        # ── Title ──────────────────────────────────────────────────
        canvas.create_text(W / 2, M + title_h / 2,
                           text="MINI MEIJER \u2014 STORE FLOOR PLAN",
                           fill=self.BP_TEXT,
                           font=("Cascadia Mono", 13, "bold"))

        # ── Store outer walls ──────────────────────────────────────
        canvas.create_rectangle(sx, sy, sx + sw, sy + sh,
                                outline=self.BP_BORDER, width=3)

        # ══════════════════════════════════════════════════════════
        #  PERIMETER DEPARTMENTS (wall sections)
        # ══════════════════════════════════════════════════════════

        # --- TOP WALL (left to right): Produce | Bakery | Deli/Meat ---
        tw = sw / 3
        self._draw_section(canvas, sx, sy, tw, wall_d, "Produce")
        self._draw_section(canvas, sx + tw, sy, tw, wall_d, "Bakery")
        self._draw_section(canvas, sx + 2 * tw, sy, sw - 2 * tw, wall_d, "Meat")

        # Wall label
        canvas.create_text(sx + sw / 2, sy - 8,
                           text="\u2500\u2500 BACK WALL (fresh departments) \u2500\u2500",
                           fill=self.BP_DIM, font=("Cascadia Mono", 7))

        # --- LEFT WALL: Dairy (full height of inner area) ---
        self._draw_section(canvas, sx, sy + wall_d,
                           wall_d, inner_h, "Dairy", vertical_text=True)

        # --- RIGHT WALL: Alcohol (full height of inner area) ---
        self._draw_section(canvas, sx + sw - wall_d, sy + wall_d,
                           wall_d, inner_h, "Alcohol", vertical_text=True)

        # Side labels
        canvas.create_text(sx - 8, sy + wall_d + inner_h / 2,
                           text="DAIRY WALL", fill=self.BP_DIM,
                           font=("Cascadia Mono", 7), angle=90)
        canvas.create_text(sx + sw + 8, sy + wall_d + inner_h / 2,
                           text="ALCOHOL WALL", fill=self.BP_DIM,
                           font=("Cascadia Mono", 7), angle=90)

        # ══════════════════════════════════════════════════════════
        #  CENTER AISLES
        # ══════════════════════════════════════════════════════════

        # 3 aisles in the center, each with a category on each side
        # Aisle 1: Beverages | Pantry
        # Aisle 2: Snacks    | Frozen
        # Aisle 3: Household | Kitchen Appliances + Desserts
        aisle_count = 3
        aisle_total_w = inner_w
        aisle_unit = aisle_total_w / aisle_count
        shelf_w = (aisle_unit - aisle_gap) / 2
        aisle_h = inner_h - 6  # slight padding

        aisle_defs = [
            ("Beverages",  "Pantry"),
            ("Snacks",     "Frozen"),
            ("Household",  "Desserts"),
        ]

        for i, (left_cat, right_cat) in enumerate(aisle_defs):
            ax = inner_x + i * aisle_unit
            ay = inner_y + 3

            # Left shelf
            self._draw_section(canvas, ax, ay, shelf_w, aisle_h, left_cat)

            # Aisle lane (walkway between shelves)
            lane_x = ax + shelf_w
            canvas.create_rectangle(lane_x, ay, lane_x + aisle_gap, ay + aisle_h,
                                    fill=self.BP_AISLE, outline="")
            # Aisle number label (rotated-style centered)
            canvas.create_text(lane_x + aisle_gap / 2, ay + aisle_h / 2,
                               text=f"AISLE {i + 1}",
                               fill=self.BP_DIM,
                               font=("Cascadia Mono", 6, "bold"), angle=90)
            # Arrow indicators
            canvas.create_text(lane_x + aisle_gap / 2, ay + 10,
                               text="\u25BC", fill=self.BP_DIM,
                               font=("Cascadia Mono", 8))
            canvas.create_text(lane_x + aisle_gap / 2, ay + aisle_h - 10,
                               text="\u25B2", fill=self.BP_DIM,
                               font=("Cascadia Mono", 8))

            # Right shelf
            self._draw_section(canvas, lane_x + aisle_gap, ay,
                               shelf_w, aisle_h, right_cat)

        # ── Kitchen Appliances (special endcap between aisle 3 and right wall)
        # Use the space on the right side near Alcohol wall
        endcap_w = inner_w * 0.18
        endcap_h = inner_h * 0.35
        endcap_x = sx + sw - wall_d - endcap_w - 4
        endcap_y = inner_y + inner_h - endcap_h - 2
        self._draw_section(canvas, endcap_x, endcap_y,
                           endcap_w, endcap_h, "Kitchen Appliances")
        # Endcap label
        canvas.create_text(endcap_x + endcap_w / 2, endcap_y - 7,
                           text="\u25C6 ENDCAP",
                           fill=YELLOW, font=("Cascadia Mono", 6, "bold"))

        # ══════════════════════════════════════════════════════════
        #  CHECKOUT ZONE (bottom of store)
        # ══════════════════════════════════════════════════════════

        ck_y = sy + sh - ck_h
        canvas.create_rectangle(sx + 1, ck_y, sx + sw - 1, sy + sh - 1,
                                fill=self.BP_ENTRANCE, outline=self.BP_BORDER,
                                width=1.5)
        canvas.create_text(sx + sw * 0.12, ck_y + ck_h / 2,
                           text="CHECKOUT",
                           fill=self.BP_TEXT,
                           font=("Cascadia Mono", 10, "bold"))

        # Checkout lanes
        lane_count = 6
        lanes_x0 = sx + sw * 0.22
        lanes_x1 = sx + sw * 0.78
        lane_sp = (lanes_x1 - lanes_x0) / lane_count
        for i in range(lane_count):
            lx = lanes_x0 + i * lane_sp + lane_sp * 0.15
            lw = lane_sp * 0.7
            canvas.create_rectangle(lx, ck_y + 6, lx + lw, ck_y + ck_h - 6,
                                    fill=self.BP_SECTION, outline=self.BP_BORDER,
                                    width=1, dash=(4, 3))
            canvas.create_text(lx + lw / 2, ck_y + ck_h / 2,
                               text=str(i + 1),
                               fill=self.BP_DIM,
                               font=("Cascadia Mono", 9, "bold"))

        # Customer service desk
        cs_x = sx + sw * 0.82
        canvas.create_rectangle(cs_x, ck_y + 4, sx + sw - 4, ck_y + ck_h - 4,
                                fill=self.BP_WALL, outline=self.BP_BORDER,
                                width=1)
        canvas.create_text((cs_x + sx + sw - 4) / 2, ck_y + ck_h / 2,
                           text="SERVICE\nDESK",
                           fill=self.BP_TEXT, font=("Cascadia Mono", 7, "bold"),
                           justify=tk.CENTER)

        # ── Entrance door (bottom wall, centered) ──────────────────
        door_x = sx + (sw - entrance_w) / 2
        door_y = sy + sh
        canvas.create_rectangle(door_x, door_y - 4, door_x + entrance_w, door_y + 4,
                                fill=GREEN, outline="")
        canvas.create_text(door_x + entrance_w / 2, door_y + 14,
                           text="\u25B2  ENTRANCE / EXIT  \u25B2",
                           fill=self.BP_TEXT,
                           font=("Cascadia Mono", 10, "bold"))

        # ── Legend ─────────────────────────────────────────────────
        lg_y = sy + sh + 26
        for i, (color, label) in enumerate([
            (GREEN,  "Well Stocked (100+)"),
            (YELLOW, "Getting Low (30-99)"),
            (RED,    "Critical (<30)"),
        ]):
            bx = M + i * 210
            canvas.create_rectangle(bx, lg_y, bx + 12, lg_y + 12,
                                    fill=color, outline="")
            canvas.create_text(bx + 18, lg_y + 6, text=label,
                               fill=self.BP_DIM,
                               font=("Cascadia Mono", 8), anchor=tk.W)

    # ─── Tab 3: Inventory ───────────────────────────────────────────

    def _build_inventory_tab(self):
        """Build the inventory table tab with search."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Inventory  ")

        # Search bar
        search_frame = tk.Frame(frame, bg=BG)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(search_frame, text="Search:", font=FONT_BOLD,
                 bg=BG, fg=FG).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_inventory_table())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                font=FONT, bg=BG_CARD, fg=FG,
                                insertbackground=FG, relief=tk.SOLID,
                                highlightthickness=1, highlightcolor=ACCENT,
                                highlightbackground=BORDER, bd=1, width=30)
        search_entry.pack(side=tk.LEFT, padx=(8, 0))

        # Refresh button
        tk.Button(search_frame, text="↻  Refresh", font=FONT_BOLD,
                  bg=ACCENT, fg="#ffffff", relief=tk.FLAT, padx=10,
                  command=self._refresh_inventory_table
                  ).pack(side=tk.RIGHT)

        # Treeview table
        cols = ("id", "name", "price", "qty", "category")
        self.inv_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                      style="Dark.Treeview", height=22)
        self.inv_tree.heading("id",       text="Product ID")
        self.inv_tree.heading("name",     text="Name")
        self.inv_tree.heading("price",    text="Price")
        self.inv_tree.heading("qty",      text="Quantity")
        self.inv_tree.heading("category", text="Category")

        self.inv_tree.column("id",       width=110, anchor=tk.W)
        self.inv_tree.column("name",     width=200, anchor=tk.W)
        self.inv_tree.column("price",    width=90,  anchor=tk.E)
        self.inv_tree.column("qty",      width=90,  anchor=tk.E)
        self.inv_tree.column("category", width=120, anchor=tk.W)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=scrollbar.set)

        self.inv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10), padx=(0, 10))

    # ─── Tab 3: Simulation Log ──────────────────────────────────────

    def _build_simulation_tab(self):
        """Build the simulation log tab with scrollable text."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Simulation Log  ")

        self.sim_text = scrolledtext.ScrolledText(
            frame, font=FONT_MONO, bg=BG_CARD, fg=FG,
            insertbackground=FG, relief=tk.FLAT,
            wrap=tk.WORD, state=tk.DISABLED
        )
        self.sim_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure text tags for colored output
        self.sim_text.tag_config("header",  foreground=ACCENT,  font=("Cascadia Mono", 11, "bold"))
        self.sim_text.tag_config("success", foreground=GREEN)
        self.sim_text.tag_config("error",   foreground=RED)
        self.sim_text.tag_config("warning", foreground=YELLOW)
        self.sim_text.tag_config("info",    foreground=PURPLE)
        self.sim_text.tag_config("dim",     foreground=FG_DIM)
        self.sim_text.tag_config("customer", foreground=TEAL, font=("Cascadia Mono", 10, "bold"))

    # ─── Tab 4: Warehouse ────────────────────────────────────────

    # Category icons for warehouse boxes
    WH_ICONS = {
        "Dairy":              "\U0001F95B",  # milk
        "Produce":            "\U0001F34E",  # apple
        "Meat":               "\U0001F969",  # steak
        "Bakery":             "\U0001F35E",  # bread
        "Beverages":          "\U0001F964",  # cup with straw
        "Pantry":             "\U0001F3FA",  # amphora
        "Snacks":             "\U0001F36A",  # cookie
        "Desserts":           "\U0001F370",  # cake
        "Frozen":             "\u2744\uFE0F",   # snowflake
        "Household":          "\U0001F9F9",  # broom
        "Kitchen Appliances": "\U0001F373",  # cooking
        "Alcohol":            "\U0001F37A",  # beer
    }

    def _build_warehouse_tab(self):
        """Build the warehouse tab with a grid of box-icon category cards."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Warehouse  ")

        # Header row
        top = tk.Frame(frame, bg=BG)
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="\U0001F4E6  Warehouse Inventory",
                 font=FONT_HEADER, bg=BG, fg=ACCENT).pack(side=tk.LEFT)

        tk.Button(top, text="↻  Refresh", font=FONT_BOLD,
                  bg=ACCENT, fg="#ffffff", relief=tk.FLAT, padx=10,
                  command=self._refresh_warehouse
                  ).pack(side=tk.RIGHT)

        # Info bar
        info = tk.Frame(frame, bg=BG_CARD, padx=15, pady=10)
        info.pack(fill=tk.X, padx=10, pady=(0, 8))

        tk.Label(info, text="\U0001F69A  Delivery Schedule:", font=FONT_BOLD,
                 bg=BG_CARD, fg=FG).pack(side=tk.LEFT)
        tk.Label(info, text=f"  {', '.join(DELIVERY_DAYS)}  (before store opens)",
                 font=FONT, bg=BG_CARD, fg=ACCENT).pack(side=tk.LEFT)

        self.wh_total_label = tk.Label(info, text="Total per delivery: --",
                                        font=FONT, bg=BG_CARD, fg=FG_DIM)
        self.wh_total_label.pack(side=tk.RIGHT)

        # Grid container (scrollable)
        grid_outer = tk.Frame(frame, bg=BG)
        grid_outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        self.wh_grid_canvas = tk.Canvas(grid_outer, bg=BG, highlightthickness=0)
        self.wh_grid_scroll = ttk.Scrollbar(grid_outer, orient=tk.VERTICAL,
                                             command=self.wh_grid_canvas.yview)
        self.wh_grid_inner = tk.Frame(self.wh_grid_canvas, bg=BG)

        self.wh_grid_inner.bind(
            "<Configure>",
            lambda e: self.wh_grid_canvas.configure(
                scrollregion=self.wh_grid_canvas.bbox("all"))
        )
        self.wh_grid_win = self.wh_grid_canvas.create_window(
            (0, 0), window=self.wh_grid_inner, anchor=tk.NW
        )
        self.wh_grid_canvas.configure(yscrollcommand=self.wh_grid_scroll.set)
        self.wh_grid_canvas.bind(
            "<Configure>",
            lambda e: self.wh_grid_canvas.itemconfig(self.wh_grid_win, width=e.width)
        )

        self.wh_grid_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.wh_grid_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Daily reports section
        dr_header = tk.Frame(frame, bg=BG)
        dr_header.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(dr_header, text="\U0001F4CB  Daily Reports",
                 font=FONT_HEADER, bg=BG, fg=ACCENT
                 ).pack(side=tk.LEFT)

        self.dr_view_mode = tk.StringVar(value="chart")
        self.dr_toggle_btn = tk.Button(
            dr_header, text="\U0001F4C4 Text View", font=FONT_BOLD,
            bg=ACCENT, fg="#ffffff", relief=tk.FLAT, padx=10,
            command=self._toggle_daily_report_view
        )
        self.dr_toggle_btn.pack(side=tk.RIGHT)

        # Container that holds both views (only one visible at a time)
        self.dr_container = tk.Frame(frame, bg=BG)
        self.dr_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Chart view
        self.dr_chart_frame = tk.Frame(self.dr_container, bg=BG)
        self.dr_chart_frame.pack(fill=tk.BOTH, expand=True)

        # Text view
        self.dr_text_frame = tk.Frame(self.dr_container, bg=BG)

        self.delivery_text = scrolledtext.ScrolledText(
            self.dr_text_frame, font=FONT_MONO, bg=BG_CARD, fg=FG,
            insertbackground=FG, relief=tk.FLAT,
            wrap=tk.WORD, state=tk.DISABLED, height=12
        )
        self.delivery_text.pack(fill=tk.BOTH, expand=True)
        self.delivery_text.tag_config("header", foreground=ACCENT, font=("Cascadia Mono", 10, "bold"))
        self.delivery_text.tag_config("success", foreground=GREEN)
        self.delivery_text.tag_config("warning", foreground=YELLOW)
        self.delivery_text.tag_config("error", foreground=RED)
        self.delivery_text.tag_config("dim", foreground=FG_DIM)
        self.delivery_text.tag_config("info", foreground=ACCENT)

        # Initial populate
        self._refresh_warehouse()
        self._draw_daily_report_chart()

    def _refresh_warehouse(self):
        """Refresh the warehouse grid with box-icon category cards."""
        # Clear old cards
        for widget in self.wh_grid_inner.winfo_children():
            widget.destroy()

        total_units = 0
        categories = list(WAREHOUSE_STOCK.items())
        cols = 4  # 4 columns in the grid

        for i, (category, units) in enumerate(categories):
            row, col = divmod(i, cols)

            products_in_cat = [
                e.value for e in inventory.all_entries()
                if e.value.category == category
            ]
            num_products = len(products_in_cat)
            per_product = units // num_products if num_products > 0 else 0
            total_units += units

            icon = self.WH_ICONS.get(category, "\U0001F4E6")

            # Stock level color
            store_qty = sum(p.quantity for p in products_in_cat)
            if store_qty == 0:
                level_color = RED
                level_text = "OUT"
            elif store_qty < 30:
                level_color = RED
                level_text = "LOW"
            elif store_qty < 100:
                level_color = YELLOW
                level_text = "OK"
            else:
                level_color = GREEN
                level_text = "FULL"

            # Build card
            card = tk.Frame(self.wh_grid_inner, bg=BG_CARD,
                            padx=12, pady=10, relief=tk.FLAT,
                            highlightbackground=BORDER,
                            highlightthickness=1)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

            # Icon + category name
            tk.Label(card, text=icon, font=("Segoe UI Emoji", 26),
                     bg=BG_CARD, fg=FG).pack(pady=(2, 4))
            tk.Label(card, text=category.upper(), font=("Segoe UI", 9, "bold"),
                     bg=BG_CARD, fg=ACCENT).pack()

            # Divider
            tk.Frame(card, bg=HEADER_BG, height=1).pack(fill=tk.X, pady=6)

            # Stats in the box
            stats_frame = tk.Frame(card, bg=BG_CARD)
            stats_frame.pack(fill=tk.X)

            # Left column: delivery info
            left = tk.Frame(stats_frame, bg=BG_CARD)
            left.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(left, text=f"{units} units", font=FONT_BOLD,
                     bg=BG_CARD, fg=FG).pack(anchor=tk.W)
            tk.Label(left, text=f"{num_products} products", font=FONT_SMALL,
                     bg=BG_CARD, fg=FG_DIM).pack(anchor=tk.W)
            tk.Label(left, text=f"{per_product} ea.", font=FONT_SMALL,
                     bg=BG_CARD, fg=FG_DIM).pack(anchor=tk.W)

            # Right column: stock status badge
            right = tk.Frame(stats_frame, bg=BG_CARD)
            right.pack(side=tk.RIGHT)
            badge = tk.Frame(right, bg=level_color, padx=8, pady=3)
            badge.pack(padx=(0, 4), pady=4)
            tk.Label(badge, text=level_text, font=("Segoe UI", 8, "bold"),
                     bg=level_color, fg="#ffffff").pack()
            tk.Label(right, text=f"{store_qty} in store",
                     font=("Segoe UI", 8), bg=BG_CARD, fg=FG_DIM).pack()

        # Configure grid columns to expand evenly
        for c in range(cols):
            self.wh_grid_inner.columnconfigure(c, weight=1)

        self.wh_total_label.config(text=f"Total per delivery: {total_units} units")

    def _refresh_delivery_history(self):
        """Update the daily reports section with per-day summaries."""
        dt = self.delivery_text
        dt.configure(state=tk.NORMAL)
        dt.delete("1.0", tk.END)

        if not self.report_data or not self.report_data.get("daily_reports"):
            dt.insert(tk.END, "  No daily reports yet. Run a simulation to see results.", "dim")
            dt.configure(state=tk.DISABLED)
            return

        reports = self.report_data["daily_reports"]
        week_rev = 0
        week_cust = 0
        week_items = 0
        week_delivered = 0
        week_restocked = 0

        for rpt in reports:
            day = rpt["day"]
            rev = rpt["revenue"]
            cust = rpt["customers"]
            items = rpt["items_sold"]
            failed = rpt["failed"]
            delivered = rpt["delivered"]
            restocked = rpt["restocked"]
            inv_val = rpt["inv_value"]
            low_count = rpt["low_stock_count"]

            week_rev += rev
            week_cust += cust
            week_items += items
            week_delivered += delivered
            week_restocked += restocked

            dt.insert(tk.END, f"  {'=' * 52}\n", "dim")
            dt.insert(tk.END, f"  {day.upper()} -- End-of-Day Report\n", "header")
            dt.insert(tk.END, f"  {'=' * 52}\n", "dim")
            dt.insert(tk.END, f"  Customers:      {cust}\n", "info")
            dt.insert(tk.END, f"  Items Sold:     {items}\n", "info")
            dt.insert(tk.END, f"  Revenue:        ${rev:,.2f}\n", "success")
            if failed > 0:
                dt.insert(tk.END, f"  Failed Buys:    {failed}\n", "error")
            if delivered > 0:
                dt.insert(tk.END, f"  Delivery:       +{delivered} units\n", "warning")
            if restocked > 0:
                dt.insert(tk.END, f"  Overnight Restock: +{restocked} units\n", "warning")
            dt.insert(tk.END, f"  Inventory Value: ${inv_val:,.2f}\n", "dim")
            if low_count > 0:
                dt.insert(tk.END, f"  Low Stock Items: {low_count}\n", "error")
            dt.insert(tk.END, "\n")

        # Weekly totals
        dt.insert(tk.END, f"  {'#' * 52}\n", "header")
        dt.insert(tk.END, f"  WEEKLY TOTALS\n", "header")
        dt.insert(tk.END, f"  {'#' * 52}\n", "header")
        dt.insert(tk.END, f"  Total Customers:   {week_cust}\n", "info")
        dt.insert(tk.END, f"  Total Items Sold:  {week_items}\n", "info")
        dt.insert(tk.END, f"  Total Revenue:     ${week_rev:,.2f}\n", "success")
        dt.insert(tk.END, f"  Total Delivered:   {week_delivered} units\n", "warning")
        dt.insert(tk.END, f"  Total Restocked:   {week_restocked} units\n", "warning")

        dt.configure(state=tk.DISABLED)

        # Also refresh chart if in chart mode
        if self.dr_view_mode.get() == "chart":
            self._draw_daily_report_chart()

    def _toggle_daily_report_view(self):
        """Toggle between chart and text view for daily reports."""
        if self.dr_view_mode.get() == "chart":
            # Switch to text view
            self.dr_view_mode.set("text")
            self.dr_toggle_btn.config(text="\U0001F4CA Chart View")
            self.dr_chart_frame.pack_forget()
            self.dr_text_frame.pack(fill=tk.BOTH, expand=True)
        else:
            # Switch to chart view
            self.dr_view_mode.set("chart")
            self.dr_toggle_btn.config(text="\U0001F4C4 Text View")
            self.dr_text_frame.pack_forget()
            self.dr_chart_frame.pack(fill=tk.BOTH, expand=True)
            self._draw_daily_report_chart()

    def _draw_daily_report_chart(self):
        """Draw a grouped bar chart of daily metrics in the warehouse tab."""
        # Clear old chart
        for w in self.dr_chart_frame.winfo_children():
            w.destroy()

        if not self.report_data or not self.report_data.get("daily_reports"):
            tk.Label(self.dr_chart_frame,
                     text="No daily reports yet. Run a simulation to see charts.",
                     font=FONT, bg=BG, fg=FG_DIM).pack(pady=30)
            return

        reports = self.report_data["daily_reports"]
        days = [r["day"][:3] for r in reports]
        revenue = [r["revenue"] for r in reports]
        customers = [r["customers"] for r in reports]
        items = [r["items_sold"] for r in reports]

        import numpy as np
        x = np.arange(len(days))
        width = 0.28

        fig = Figure(figsize=(10, 4.5), dpi=100)
        fig.patch.set_facecolor(BG)

        # ── Top chart: Revenue bar + Customer line overlay ──
        ax1 = fig.add_subplot(211)
        ax1.set_facecolor(BG_CARD)

        bars = ax1.bar(x, revenue, width=0.5, color=ACCENT, alpha=0.9,
                       label="Revenue ($)", zorder=2)
        ax1.set_ylabel("Revenue ($)", color=FG_DIM, fontsize=8)
        ax1.set_xticks(x)
        ax1.set_xticklabels(days)
        ax1.tick_params(colors=FG_DIM, labelsize=8)
        for spine in ax1.spines.values():
            spine.set_color(FG_DIM)
            spine.set_linewidth(0.5)

        # Add revenue labels on bars
        for bar, val in zip(bars, revenue):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(revenue) * 0.02,
                     f"${val:,.0f}", ha="center", va="bottom", color=FG, fontsize=7)

        # Overlay customer line on secondary axis
        ax2 = ax1.twinx()
        ax2.plot(x, customers, color=TEAL, marker="o", linewidth=2,
                 markersize=5, label="Customers", zorder=3)
        ax2.set_ylabel("Customers", color=TEAL, fontsize=8)
        ax2.tick_params(axis="y", colors=TEAL, labelsize=8)
        ax2.spines["right"].set_color(TEAL)
        ax2.spines["right"].set_linewidth(0.5)
        for side in ["top", "left", "bottom"]:
            ax2.spines[side].set_visible(False)

        ax1.set_title("Revenue & Customers by Day", color=FG, fontsize=10, pad=8)

        # Combined legend
        bars_legend = ax1.get_legend_handles_labels()
        line_legend = ax2.get_legend_handles_labels()
        ax1.legend(bars_legend[0] + line_legend[0],
                   bars_legend[1] + line_legend[1],
                   loc="upper left", fontsize=7,
                   facecolor=BG_CARD, edgecolor=FG_DIM,
                   labelcolor=FG_DIM)

        # ── Bottom chart: Items sold + delivered/restocked stacked ──
        ax3 = fig.add_subplot(212)
        ax3.set_facecolor(BG_CARD)

        delivered = [r["delivered"] for r in reports]
        restocked = [r["restocked"] for r in reports]

        ax3.bar(x - width, items, width, color=GREEN, alpha=0.9, label="Items Sold", zorder=2)
        ax3.bar(x, delivered, width, color=YELLOW, alpha=0.9, label="Delivered", zorder=2)
        ax3.bar(x + width, restocked, width, color=PURPLE, alpha=0.9, label="Restocked", zorder=2)

        ax3.set_ylabel("Units", color=FG_DIM, fontsize=8)
        ax3.set_xticks(x)
        ax3.set_xticklabels(days)
        ax3.tick_params(colors=FG_DIM, labelsize=8)
        for spine in ax3.spines.values():
            spine.set_color(FG_DIM)
            spine.set_linewidth(0.5)
        ax3.set_title("Items Sold / Deliveries / Restocks", color=FG, fontsize=10, pad=8)
        ax3.legend(loc="upper left", fontsize=7,
                   facecolor=BG_CARD, edgecolor=FG_DIM,
                   labelcolor=FG_DIM)

        fig.tight_layout(pad=1.5)
        self._embed_chart(self.dr_chart_frame, fig, height=350)

    # ─── Tab 5: Customer Activity ─────────────────────────────────

    def _build_activity_tab(self):
        """Build the real-time customer activity panel with history log."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Customer Activity  ")

        # PanedWindow: live panel (top) + history log (bottom)
        pane = tk.PanedWindow(frame, orient=tk.VERTICAL, bg=BG,
                              sashwidth=6, sashrelief=tk.FLAT)
        pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ════════════════════════════════════════════════════════════
        # TOP HALF: Live customer card + cart
        # ════════════════════════════════════════════════════════════
        live_frame = tk.Frame(pane, bg=BG)
        pane.add(live_frame, minsize=200)

        # Top info bar
        top = tk.Frame(live_frame, bg=BG)
        top.pack(fill=tk.X)

        tk.Label(top, text="Live Customer Activity",
                 font=FONT_HEADER, bg=BG, fg=TEAL).pack(side=tk.LEFT)

        self.activity_status = tk.Label(
            top, text="  Waiting for simulation...",
            font=FONT, bg=BG, fg=FG_DIM
        )
        self.activity_status.pack(side=tk.RIGHT)

        # Current customer card
        card = tk.Frame(live_frame, bg=BG_CARD, padx=15, pady=12)
        card.pack(fill=tk.X, pady=(8, 6))

        # Row 1: name + profession
        row1 = tk.Frame(card, bg=BG_CARD)
        row1.pack(fill=tk.X)

        tk.Label(row1, text="Customer:", font=FONT_BOLD,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_name = tk.Label(row1, text="--", font=FONT_BOLD,
                                 bg=BG_CARD, fg=ACCENT)
        self.act_name.pack(side=tk.LEFT, padx=(6, 20))

        tk.Label(row1, text="Profession:", font=FONT_BOLD,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_profession = tk.Label(row1, text="--", font=FONT_BOLD,
                                       bg=BG_CARD, fg=PURPLE)
        self.act_profession.pack(side=tk.LEFT, padx=(6, 0))

        # Row 2: profile + age + race
        row2 = tk.Frame(card, bg=BG_CARD)
        row2.pack(fill=tk.X, pady=(6, 0))

        tk.Label(row2, text="Profile:", font=FONT,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_profile = tk.Label(row2, text="--", font=FONT,
                                    bg=BG_CARD, fg=TEAL)
        self.act_profile.pack(side=tk.LEFT, padx=(6, 20))

        tk.Label(row2, text="Age:", font=FONT,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_age = tk.Label(row2, text="--", font=FONT,
                                bg=BG_CARD, fg=FG)
        self.act_age.pack(side=tk.LEFT, padx=(6, 20))

        tk.Label(row2, text="Race:", font=FONT,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_race = tk.Label(row2, text="--", font=FONT,
                                 bg=BG_CARD, fg=FG)
        self.act_race.pack(side=tk.LEFT, padx=(6, 0))

        # Row 3: running total
        row3 = tk.Frame(card, bg=BG_CARD)
        row3.pack(fill=tk.X, pady=(6, 0))

        tk.Label(row3, text="Cart Total:", font=FONT_BOLD,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_total = tk.Label(row3, text="$0.00", font=FONT_BOLD,
                                  bg=BG_CARD, fg=GREEN)
        self.act_total.pack(side=tk.LEFT, padx=(6, 20))

        tk.Label(row3, text="Items:", font=FONT_BOLD,
                 bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.act_items_count = tk.Label(row3, text="0", font=FONT_BOLD,
                                        bg=BG_CARD, fg=GREEN)
        self.act_items_count.pack(side=tk.LEFT, padx=(6, 0))

        # Cart items table
        cart_cols = ("item", "qty", "price", "subtotal", "status")
        self.act_tree = ttk.Treeview(live_frame, columns=cart_cols,
                                     show="headings",
                                     style="Dark.Treeview", height=6)
        self.act_tree.heading("item",     text="Product")
        self.act_tree.heading("qty",      text="Qty")
        self.act_tree.heading("price",    text="Unit Price")
        self.act_tree.heading("subtotal", text="Subtotal")
        self.act_tree.heading("status",   text="Status")

        self.act_tree.column("item",     width=200, anchor=tk.W)
        self.act_tree.column("qty",      width=60,  anchor=tk.E)
        self.act_tree.column("price",    width=100, anchor=tk.E)
        self.act_tree.column("subtotal", width=100, anchor=tk.E)
        self.act_tree.column("status",   width=120, anchor=tk.CENTER)

        self.act_tree.tag_configure("bought", foreground=GREEN)
        self.act_tree.tag_configure("failed", foreground=RED)

        self.act_tree.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # ════════════════════════════════════════════════════════════
        # BOTTOM HALF: Customer history log (expandable by day)
        # ════════════════════════════════════════════════════════════
        history_frame = tk.Frame(pane, bg=BG)
        pane.add(history_frame, minsize=180)

        tk.Label(history_frame, text="Customer History",
                 font=FONT_HEADER, bg=BG, fg=ACCENT).pack(anchor=tk.W)

        # History treeview: Day > Customer (with items as children)
        hist_cols = ("detail", "spent", "items")
        self.hist_tree = ttk.Treeview(history_frame, columns=hist_cols,
                                      style="Dark.Treeview", height=12)
        self.hist_tree.heading("#0",     text="Customer / Item")
        self.hist_tree.heading("detail", text="Info")
        self.hist_tree.heading("spent",  text="Spent")
        self.hist_tree.heading("items",  text="Items")

        self.hist_tree.column("#0",     width=280, anchor=tk.W)
        self.hist_tree.column("detail", width=280, anchor=tk.W)
        self.hist_tree.column("spent",  width=100, anchor=tk.E)
        self.hist_tree.column("items",  width=60,  anchor=tk.E)

        self.hist_tree.tag_configure("day_node",   foreground=ACCENT,
                                     font=("Cascadia Mono", 10, "bold"))
        self.hist_tree.tag_configure("high_roller", foreground=YELLOW,
                                     font=("Cascadia Mono", 10, "bold"))
        self.hist_tree.tag_configure("customer",   foreground=FG)
        self.hist_tree.tag_configure("item_ok",    foreground=GREEN)
        self.hist_tree.tag_configure("item_fail",  foreground=RED)

        hist_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL,
                                    command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=hist_scroll.set)

        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                            pady=(6, 0))
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(6, 0))

        # Storage for per-day customer records built during simulation
        self._day_customers_log = []  # list of dicts per customer
        self._hist_day_nodes = {}     # day_name -> treeview node id

    def _update_activity_customer(self, customer, profile_name, customer_num, day_name, block_label):
        """Update the activity panel with a new customer (called on main thread)."""
        self.act_name.config(text=f"#{customer_num}  {customer.first_name} {customer.last_name}")
        self.act_profession.config(text=customer.profession)
        self.act_profile.config(text=profile_name)
        self.act_age.config(text=str(customer.age))
        self.act_race.config(text=customer.race)
        self.act_total.config(text="$0.00")
        self.act_items_count.config(text="0")
        self.act_tree.delete(*self.act_tree.get_children())
        self.activity_status.config(
            text=f"{day_name} | {block_label}", fg=ACCENT
        )

    def _update_activity_item(self, product_name, qty, unit_price, subtotal, success):
        """Add an item row to the activity cart table (called on main thread)."""
        tag = "bought" if success else "failed"
        status = "Purchased" if success else "Out of Stock"
        self.act_tree.insert("", tk.END, values=(
            product_name, qty, f"${unit_price:.2f}",
            f"${subtotal:.2f}" if success else "--", status
        ), tags=(tag,))
        # Auto-scroll to bottom
        children = self.act_tree.get_children()
        if children:
            self.act_tree.see(children[-1])

    def _update_activity_totals(self, total, items):
        """Update the running cart total and item count (called on main thread)."""
        self.act_total.config(text=f"${total:,.2f}")
        self.act_items_count.config(text=str(items))

    def _add_history_day(self, day_name, day_index, customer_records):
        """Populate the history tree with a full day of customers.

        Called on main thread at the end of each sim day.
        customer_records: list of dicts with keys:
            num, name, profession, profile, age, race, total, items_count, cart
        cart: list of (product_name, qty, unit_price, subtotal, success)
        """
        # Find the high roller for this day
        high_roller_idx = -1
        high_roller_total = -1
        for i, rec in enumerate(customer_records):
            if rec["total"] > high_roller_total:
                high_roller_total = rec["total"]
                high_roller_idx = i

        # Reorder so the high roller appears first
        if high_roller_idx > 0:
            hr = customer_records.pop(high_roller_idx)
            customer_records.insert(0, hr)
            high_roller_idx = 0

        # Day node
        day_count = len(customer_records)
        day_total = sum(r["total"] for r in customer_records)
        day_id = self.hist_tree.insert(
            "", tk.END,
            text=f"\U0001F4C5  {day_name} ({day_count} customers)",
            values=(f"Day {day_index + 1}",
                    f"${day_total:,.2f}",
                    sum(r["items_count"] for r in customer_records)),
            open=False, tags=("day_node",)
        )
        self._hist_day_nodes[day_name] = day_id

        # Customer nodes under the day
        for i, rec in enumerate(customer_records):
            is_high_roller = (i == high_roller_idx)
            tag = "high_roller" if is_high_roller else "customer"
            prefix = "\U0001F451 " if is_high_roller else ""
            suffix = "  \u2605 HIGH ROLLER" if is_high_roller else ""

            cust_id = self.hist_tree.insert(
                day_id, tk.END,
                text=f"{prefix}#{rec['num']}  {rec['name']}{suffix}",
                values=(
                    f"{rec['profession']} | {rec['profile']} | Age {rec['age']}",
                    f"${rec['total']:,.2f}",
                    rec["items_count"]
                ),
                open=False, tags=(tag,)
            )

            # Item children under each customer
            for item_name, qty, price, subtotal, success in rec["cart"]:
                itag = "item_ok" if success else "item_fail"
                status = "Purchased" if success else "Out of Stock"
                self.hist_tree.insert(
                    cust_id, tk.END,
                    text=f"    {item_name}",
                    values=(
                        status,
                        f"${subtotal:.2f}" if success else "--",
                        qty
                    ),
                    tags=(itag,)
                )

        # Auto-scroll to latest day
        self.hist_tree.see(day_id)

    # ─── Tab 6: Low Stock ─────────────────────────────────────────

    def _build_low_stock_tab(self):
        """Build the low stock alerts tab."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Low Stock  ")

        # Top bar with auto-restock button
        top = tk.Frame(frame, bg=BG)
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="Products at or below 10 units",
                 font=FONT_HEADER, bg=BG, fg=YELLOW).pack(side=tk.LEFT)

        tk.Button(top, text=f"↻  Auto-Restock All to {RESTOCK_TARGET}", font=FONT_BOLD,
                  bg=GREEN, fg="#ffffff", relief=tk.FLAT, padx=12,
                  command=self._auto_restock
                  ).pack(side=tk.RIGHT)

        # Table
        cols = ("id", "name", "qty", "category")
        self.low_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                      style="Dark.Treeview", height=15)
        self.low_tree.heading("id",       text="Product ID")
        self.low_tree.heading("name",     text="Name")
        self.low_tree.heading("qty",      text="Quantity")
        self.low_tree.heading("category", text="Category")

        self.low_tree.column("id",       width=110, anchor=tk.W)
        self.low_tree.column("name",     width=220, anchor=tk.W)
        self.low_tree.column("qty",      width=100, anchor=tk.E)
        self.low_tree.column("category", width=140, anchor=tk.W)

        self.low_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # ─── Tab 7: Report ──────────────────────────────────────────────

    def _build_report_tab(self):
        """Build the report tab with a scrollable canvas for charts."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Report  ")

        # Scrollable container
        self.report_canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        self.report_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                                               command=self.report_canvas.yview)
        self.report_inner = tk.Frame(self.report_canvas, bg=BG)

        self.report_inner.bind(
            "<Configure>",
            lambda e: self.report_canvas.configure(
                scrollregion=self.report_canvas.bbox("all"))
        )
        self.report_canvas_window = self.report_canvas.create_window(
            (0, 0), window=self.report_inner, anchor=tk.NW
        )
        self.report_canvas.configure(yscrollcommand=self.report_scrollbar.set)

        # Make inner frame stretch to canvas width
        self.report_canvas.bind("<Configure>", self._on_report_canvas_resize)

        self.report_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.report_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))

        # Mouse-wheel scrolling
        self.report_canvas.bind_all("<MouseWheel>",
            lambda e: self.report_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Placeholder
        self.report_placeholder = tk.Label(
            self.report_inner,
            text="Run a simulation to see the weekly report.",
            font=FONT, bg=BG, fg=FG_DIM
        )
        self.report_placeholder.pack(pady=40)

        # Keep references to chart canvases so they aren't garbage-collected
        self._chart_widgets = []

    def _on_report_canvas_resize(self, event):
        """Stretch the inner frame to match the canvas width."""
        self.report_canvas.itemconfig(self.report_canvas_window, width=event.width)

    # ─── Bottom Status Bar ──────────────────────────────────────────

    def _build_bottom_bar(self):
        """Build the persistent bottom status bar showing inventory totals."""
        self.bottom_bar = tk.Frame(self.root, bg=SIDEBAR_BG, height=38)
        self.bottom_bar.pack(fill=tk.X, padx=0, pady=(2, 0))
        self.bottom_bar.pack_propagate(False)

        # Total Products
        tk.Label(self.bottom_bar, text="Products:", font=FONT_SMALL,
                 bg=SIDEBAR_BG, fg="#8888aa").pack(side=tk.LEFT, padx=(15, 3))
        self.bb_products = tk.Label(self.bottom_bar, text="0", font=FONT_BOLD,
                                    bg=SIDEBAR_BG, fg=PEACH)
        self.bb_products.pack(side=tk.LEFT, padx=(0, 18))

        # Total Units
        tk.Label(self.bottom_bar, text="Units:", font=FONT_SMALL,
                 bg=SIDEBAR_BG, fg="#8888aa").pack(side=tk.LEFT, padx=(0, 3))
        self.bb_units = tk.Label(self.bottom_bar, text="0", font=FONT_BOLD,
                                  bg=SIDEBAR_BG, fg=MINT)
        self.bb_units.pack(side=tk.LEFT, padx=(0, 18))

        # Total Value
        tk.Label(self.bottom_bar, text="Value:", font=FONT_SMALL,
                 bg=SIDEBAR_BG, fg="#8888aa").pack(side=tk.LEFT, padx=(0, 3))
        self.bb_value = tk.Label(self.bottom_bar, text="$0.00", font=FONT_BOLD,
                                  bg=SIDEBAR_BG, fg="#ffffff")
        self.bb_value.pack(side=tk.LEFT, padx=(0, 18))

        # Low Stock Count
        tk.Label(self.bottom_bar, text="Low Stock:", font=FONT_SMALL,
                 bg=SIDEBAR_BG, fg="#8888aa").pack(side=tk.LEFT, padx=(0, 3))
        self.bb_low = tk.Label(self.bottom_bar, text="0", font=FONT_BOLD,
                                bg=SIDEBAR_BG, fg=MINT)
        self.bb_low.pack(side=tk.LEFT)

        # Playback progress bar
        self.bb_progress = ttk.Progressbar(
            self.bottom_bar, length=160, mode="determinate",
            maximum=28, style="BP.Horizontal.TProgressbar"
        )
        self.bb_progress.pack(side=tk.RIGHT, padx=(0, 15))

        # Status / playback label (right side)
        self.bb_status = tk.Label(self.bottom_bar, text="Ready", font=FONT_SMALL,
                                   bg=SIDEBAR_BG, fg="#8888aa")
        self.bb_status.pack(side=tk.RIGHT, padx=(0, 8))

    def _refresh_bottom_bar(self):
        """Update the bottom bar with current inventory totals."""
        products = [e.value for e in inventory.all_entries()]
        total_products = len(products)
        total_units = sum(p.quantity for p in products)
        total_value = sum(p.price * p.quantity for p in products)
        low_count = len([p for p in products if p.quantity <= 10])

        self.bb_products.config(text=str(total_products))
        self.bb_units.config(text=f"{total_units:,}")
        self.bb_value.config(text=f"${total_value:,.2f}")
        self.bb_low.config(text=str(low_count),
                           fg=RED if low_count > 0 else GREEN)

    # ─── Actions ────────────────────────────────────────────────────

    def _load_inventory(self):
        """Seed the inventory and refresh the table."""
        # Clear existing inventory first
        for entry in list(inventory.all_entries()):
            inventory.delete(entry.key)
        inventory.count = 0

        # Redirect print to capture log
        seed_inventory()
        self._refresh_inventory_table()
        self._refresh_low_stock()
        self._refresh_blueprint()
        self._refresh_bottom_bar()
        self.load_btn.configure(text="Inventory Loaded", bg=FG_DIM, state=tk.DISABLED)
        self._log("Inventory loaded with seed data.\n", "success")

    def _start_simulation(self):
        """Run the simulation in a background thread."""
        if self.sim_running:
            return
        if inventory.count == 0:
            messagebox.showwarning("No Inventory", "Please load inventory first.")
            return

        self.sim_running = True
        self.run_btn.configure(text="Running...", bg=FG_DIM, state=tk.DISABLED)

        # Clear previous log
        self.sim_text.configure(state=tk.NORMAL)
        self.sim_text.delete("1.0", tk.END)
        self.sim_text.configure(state=tk.DISABLED)

        thread = threading.Thread(target=self._run_simulation, daemon=True)
        thread.start()

    def _run_simulation(self):
        """Run the full 7-day weekly simulation on a background thread."""
        value_before = get_total_value()

        # Reset playback progress
        self.root.after(0, lambda: self.bb_progress.configure(value=0))
        self.root.after(0, lambda: self.bb_status.config(
            text="Simulation Running...", fg=YELLOW))

        self._log("=" * 58 + "\n", "header")
        self._log("  Mini Meijer -- 7-Day Weekly Simulation\n", "header")
        self._log("=" * 58 + "\n\n", "header")
        self._log(f"  Starting inventory value: ${value_before:,.2f}\n", "info")
        self._log(f"  Deliveries scheduled: {', '.join(DELIVERY_DAYS)}\n\n", "dim")

        week_items_sold = 0
        week_revenue = 0.0
        week_failed = 0
        week_customers = 0
        sales_by_product = {}
        low_stock_hits = set()
        sales_by_time_block = {}
        sales_by_day = {}
        customers_by_day = {}
        deliveries_log = []
        sale_suggestions_applied = []
        customer_num = 0
        profile_counts = {}

        daily_reports = []

        # Clear customer history from any previous run
        self.root.after(0, lambda: self.hist_tree.delete(*self.hist_tree.get_children()))
        self._hist_day_nodes = {}

        for day_index, day_name in enumerate(DAY_NAMES):
            traffic = DAY_TRAFFIC[day_name]
            day_revenue = 0.0
            day_customers = 0
            day_items_sold = 0
            day_failed = 0
            day_delivered = 0
            day_customer_records = []  # for history log

            self._log("\n" + "#" * 58 + "\n", "header")
            self._log(f"  DAY {day_index + 1}: {day_name.upper()}  "
                      f"(traffic: {traffic}x)\n", "header")
            self._log("#" * 58 + "\n", "header")

            # ── Delivery truck ──────────────────────────────────────
            if day_name in DELIVERY_DAYS:
                self._log(f"\n  DELIVERY TRUCK -- {day_name} Morning\n", "warning")
                self._log(f"  (Only restocking items with {DELIVERY_RESTOCK_MAX} or fewer units)\n", "dim")
                total_delivered = 0
                for category, units in WAREHOUSE_STOCK.items():
                    products_in_cat = [
                        e.value for e in inventory.all_entries()
                        if e.value.category == category
                            and e.value.quantity <= DELIVERY_RESTOCK_MAX
                    ]
                    if not products_in_cat:
                        continue
                    per_product = units // len(products_in_cat)
                    remainder = units % len(products_in_cat)
                    for i, p in enumerate(products_in_cat):
                        amount = per_product + (1 if i < remainder else 0)
                        if amount > 0:
                            p.quantity += amount
                            total_delivered += amount
                            self._log(f"    [OK] +{amount} {p.name} "
                                      f"(now {p.quantity})\n", "success")
                day_delivered = total_delivered
                deliveries_log.append((day_name, total_delivered))
                self._log(f"  [OK] Delivery complete: {total_delivered} units\n", "info")

            # ── Friday sale suggestions (popup in GUI) ──────────────
            if day_name == "Friday":
                suggestions = friday_sale_suggestions()
                if suggestions:
                    self._log(f"\n  FRIDAY SALE -- TOP {len(suggestions)} "
                              f"OVERSTOCKED ITEMS\n", "warning")
                    for p, sale_price in suggestions:
                        self._log(f"    {p.name:<20} Qty: {p.quantity:>4}  "
                                  f"${p.price:.2f} -> ${sale_price:.2f}\n", "warning")

                    # Ask user via popup on the main thread
                    self._sale_suggestions = suggestions
                    self._sale_approved = None
                    self.root.after(0, self._show_sale_popup)
                    # Wait for user response
                    while self._sale_approved is None:
                        time.sleep(0.1)

                    if self._sale_approved:
                        apply_sales(suggestions)
                        sale_suggestions_applied = suggestions
                        self._log("  [OK] Sale prices applied!\n", "success")
                    else:
                        self._log("  [--] Sales not applied.\n", "dim")

            # ── Alcohol price surge (Fri / Sat / Sun) ───────────────
            alcohol_originals = {}  # product_id -> original_price
            surge_rate = ALCOHOL_SURGE_RATES.get(day_name)
            if surge_rate:
                # Build list of alcohol items and their surge prices
                alcohol_items = []
                for entry in inventory.all_entries():
                    p = entry.value
                    if p.category == "Alcohol":
                        new_price = round(p.price * (1 + surge_rate), 2)
                        alcohol_items.append((p, new_price))

                if alcohol_items:
                    self._log(f"\n  [ALCOHOL SURGE] Proposing +{int(surge_rate * 100)}% "
                              f"alcohol markup for {day_name}...\n", "warning")
                    for p, new_price in alcohol_items:
                        self._log(f"    {p.name:<24} ${p.price:.2f} -> ${new_price:.2f}\n", "warning")

                    # Ask user via popup on the main thread
                    self._alcohol_surge_items = alcohol_items
                    self._alcohol_surge_rate = surge_rate
                    self._alcohol_surge_day = day_name
                    self._alcohol_surge_approved = None
                    self.root.after(0, self._show_alcohol_surge_popup)
                    while self._alcohol_surge_approved is None:
                        time.sleep(0.1)

                    if self._alcohol_surge_approved:
                        for p, new_price in alcohol_items:
                            alcohol_originals[p.id] = p.price
                            p.price = new_price
                        self._log(f"  [OK] {day_name} alcohol surge applied!\n", "success")
                    else:
                        self._log(f"  [--] {day_name} surge declined. Prices unchanged.\n", "dim")

            # ── Time blocks for this day ────────────────────────────
            high_blocks = HIGH_TRAFFIC_BLOCKS.get(day_name)
            for block_index, block in enumerate(TIME_BLOCKS):
                block_label = block["label"]
                # High-traffic days (Fri/Sat/Sun) use fixed counts
                if high_blocks:
                    block_customers = high_blocks[block_index]["customers"]
                    block_max_cart  = high_blocks[block_index]["max_cart"]
                else:
                    block_customers = max(1, int(block["customers"] * traffic))
                    block_max_cart  = block["max_cart"]
                block_revenue = 0.0

                self._log(f"\n  --- {day_name} | {block_label} "
                          f"({block_customers} customers) ---\n", "dim")

                # Update playback status + progress
                progress = day_index * 4 + block_index + 1
                self.root.after(0, lambda d=day_name, b=block_label:
                                self.bb_status.config(
                                    text=f"Day {d} | {b}", fg=ACCENT))
                self.root.after(0, lambda p=progress:
                                self.bb_progress.configure(value=p))

                for j in range(1, block_customers + 1):
                    customer_num += 1
                    day_customers += 1

                    profile_name, profile = get_profile_for_time_block(block_index)
                    customer = Customer(profile_name, profile)
                    products = get_all_products()

                    profile_counts[profile_name] = profile_counts.get(profile_name, 0) + 1

                    if not products:
                        self._log("  [!] No products left in stock!\n", "error")
                        break

                    cart = pick_products_by_preference(products, profile, block_max_cart, customer.age)

                    self._log(f"\n  #{customer_num}: ", "customer")
                    self._log(f"{customer}\n", "info")

                    # Update activity panel with new customer
                    self.root.after(0, self._update_activity_customer,
                                   customer, profile_name, customer_num,
                                   day_name, block_label)

                    customer_total = 0.0
                    customer_items = 0
                    customer_cart_log = []  # (name, qty, price, subtotal, success)

                    for product in cart:
                        qty = random_purchase_amount()

                        if product.quantity >= qty:
                            purchase(product.id, qty)
                            item_cost = product.price * qty
                            week_items_sold += qty
                            day_items_sold += qty
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

                            self._log(f"    [OK] {qty}x {product.name} "
                                      f"(${item_cost:.2f})\n", "success")
                            customer_cart_log.append(
                                (product.name, qty, product.price, item_cost, True))
                            self.root.after(0, self._update_activity_item,
                                           product.name, qty, product.price,
                                           item_cost, True)
                            self.root.after(0, self._update_activity_totals,
                                           customer_total, customer_items)
                        else:
                            self._log(f"    [X] Wanted {qty}x {product.name} "
                                      f"but only {product.quantity} left\n", "error")
                            customer_cart_log.append(
                                (product.name, qty, product.price, 0, False))
                            self.root.after(0, self._update_activity_item,
                                           product.name, qty, product.price,
                                           0, False)
                            week_failed += 1
                            day_failed += 1

                    self._log(f"  >> {customer.first_name}: "
                              f"{customer_items} items -- ${customer_total:,.2f}\n", "dim")

                    day_customer_records.append({
                        "num":         customer_num,
                        "name":        customer.full_name,
                        "profession":  customer.profession,
                        "profile":     profile_name,
                        "age":         customer.age,
                        "race":        customer.race,
                        "total":       customer_total,
                        "items_count": customer_items,
                        "cart":        customer_cart_log,
                    })

                    # Live-update blueprint + bottom bar
                    self.root.after(0, self._refresh_blueprint)
                    self.root.after(0, self._refresh_bottom_bar)

                    time.sleep(0.5 / max(1, self.sim_speed.get()))

                sales_by_time_block[block_label] = (
                    sales_by_time_block.get(block_label, 0) + block_revenue
                )

            # ── End of day ──────────────────────────────────────────
            # Revert weekend alcohol prices
            if alcohol_originals:
                for entry in inventory.all_entries():
                    p = entry.value
                    if p.id in alcohol_originals:
                        p.price = alcohol_originals[p.id]

            sales_by_day[day_name] = day_revenue
            customers_by_day[day_name] = day_customers
            week_customers += day_customers

            # Overnight restock
            day_restocked = 0
            low = get_low_stock()
            if low:
                self._log(f"\n  [OVERNIGHT RESTOCK] {len(low)} items restocked to {RESTOCK_TARGET}:\n", "warning")
                for p in low:
                    restock_amount = RESTOCK_TARGET - p.quantity
                    if restock_amount > 0:
                        p.quantity += restock_amount
                        day_restocked += restock_amount
                        self._log(f"    [OK] +{restock_amount} {p.name} "
                                  f"(now {p.quantity})\n", "success")

            self._log(f"\n  -- End of {day_name}: ${day_revenue:,.2f} revenue, "
                      f"{day_customers} customers --\n", "info")

            # Push this day's customers into the history log
            records = list(day_customer_records)  # snapshot
            idx = day_index
            self.root.after(0, self._add_history_day, day_name, idx, records)

            # Build daily report for warehouse tab
            low_stock_count = len(get_low_stock())
            daily_reports.append({
                "day":             day_name,
                "revenue":         day_revenue,
                "customers":       day_customers,
                "items_sold":      day_items_sold,
                "failed":          day_failed,
                "delivered":       day_delivered,
                "restocked":       day_restocked,
                "inv_value":       get_total_value(),
                "low_stock_count": low_stock_count,
            })

        # ── Week complete ───────────────────────────────────────────
        value_after = get_total_value()

        self._log("\n" + "=" * 58 + "\n", "header")
        self._log("  Weekly Simulation Complete!\n", "header")
        self._log("=" * 58 + "\n", "header")

        self.report_data = {
            "total_revenue":       week_revenue,
            "total_items_sold":    week_items_sold,
            "total_customers":     week_customers,
            "failed_purchases":    week_failed,
            "value_before":        value_before,
            "value_after":         value_after,
            "sales_by_product":    sales_by_product,
            "low_stock_hits":      low_stock_hits,
            "sales_by_time_block": sales_by_time_block,
            "sales_by_day":        sales_by_day,
            "customers_by_day":    customers_by_day,
            "deliveries_log":      deliveries_log,
            "daily_reports":       daily_reports,
            "sale_suggestions":    sale_suggestions_applied,
            "profile_counts":      profile_counts,
        }

        self.root.after(0, self._update_after_simulation)

    def _show_sale_popup(self):
        """Show a popup asking user to approve Friday sale prices."""
        suggestions = self._sale_suggestions
        msg = f"Top {len(suggestions)} most overstocked items to put on sale:\n\n"
        for i, (p, sale_price) in enumerate(suggestions, 1):
            savings = p.price - sale_price
            msg += f"  {i}. {p.name}: {p.quantity} units -- "
            msg += f"${p.price:.2f} -> ${sale_price:.2f} (-${savings:.2f})\n"
        msg += "\nApply these sale prices?"

        result = messagebox.askyesno("Friday Sale -- Top 5", msg)
        self._sale_approved = result

    def _show_alcohol_surge_popup(self):
        """Show a popup asking user to approve alcohol price surge."""
        items = self._alcohol_surge_items
        rate = self._alcohol_surge_rate
        day = self._alcohol_surge_day
        pct = int(rate * 100)
        msg = f"{day} Alcohol Surge (+{pct}%)\n"
        msg += f"{len(items)} alcohol products will be marked up:\n\n"
        for i, (p, new_price) in enumerate(items, 1):
            increase = new_price - p.price
            msg += f"  {i}. {p.name}: ${p.price:.2f} -> ${new_price:.2f} (+${increase:.2f})\n"
        msg += f"\nApply the +{pct}% {day} surge?"

        result = messagebox.askyesno(f"{day} Alcohol Surge", msg)
        self._alcohol_surge_approved = result

    def _update_after_simulation(self):
        """Update all GUI elements after the simulation completes."""
        data = self.report_data
        if not data:
            return

        # Refresh tables
        self._refresh_inventory_table()
        self._refresh_low_stock()
        self._refresh_warehouse()
        self._refresh_delivery_history()
        self._refresh_blueprint()
        self._refresh_bottom_bar()

        # Playback complete
        self.bb_status.config(text="Simulation Complete", fg=GREEN)
        self.bb_progress.configure(value=28)

        # Build report
        self._build_report_text(data)

        # Re-enable buttons
        self.sim_running = False
        self.run_btn.configure(text="Run Again", bg=GREEN, state=tk.NORMAL)
        self.load_btn.configure(text="Reload Inventory", bg=ACCENT, state=tk.NORMAL)

    def _refresh_inventory_table(self):
        """Reload the inventory treeview with current data."""
        self.inv_tree.delete(*self.inv_tree.get_children())

        search = self.search_var.get().lower().strip()
        products = [e.value for e in inventory.all_entries()]

        # Sort by category then name
        products.sort(key=lambda p: (p.category, p.name))

        for i, p in enumerate(products):
            if search and search not in p.name.lower() and search not in p.category.lower():
                continue

            tag = "low" if p.quantity <= 10 else ("alt" if i % 2 else "")
            self.inv_tree.insert("", tk.END, values=(
                p.id, p.name, f"${p.price:.2f}", p.quantity, p.category
            ), tags=(tag,))

        self.inv_tree.tag_configure("low", foreground=RED)
        self.inv_tree.tag_configure("alt", background=ROW_ALT)

    def _refresh_low_stock(self):
        """Reload the low stock treeview."""
        self.low_tree.delete(*self.low_tree.get_children())
        low = get_low_stock()
        for p in low:
            color_tag = "critical" if p.quantity == 0 else "warn"
            self.low_tree.insert("", tk.END, values=(
                p.id, p.name, p.quantity, p.category
            ), tags=(color_tag,))

        self.low_tree.tag_configure("critical", foreground=RED)
        self.low_tree.tag_configure("warn", foreground=YELLOW)

    def _auto_restock(self):
        """Restock all low items to RESTOCK_TARGET units."""
        low = get_low_stock()
        if not low:
            messagebox.showinfo("All Good", "No items need restocking.")
            return

        count = 0
        for p in low:
            amount = RESTOCK_TARGET - p.quantity
            if amount > 0:
                restock(p.id, amount)
                count += 1

        self._refresh_inventory_table()
        self._refresh_low_stock()

        messagebox.showinfo("Restocked", f"Restocked {count} items to {RESTOCK_TARGET} units each.")

    def _log(self, text, tag=None):
        """Append text to the simulation log (thread-safe)."""
        def _append():
            self.sim_text.configure(state=tk.NORMAL)
            if tag:
                self.sim_text.insert(tk.END, text, tag)
            else:
                self.sim_text.insert(tk.END, text)
            self.sim_text.see(tk.END)
            self.sim_text.configure(state=tk.DISABLED)
        self.root.after(0, _append)

    # ─── Chart Helpers ──────────────────────────────────────────────

    def _make_chart_colors(self):
        """Return a list of colors for charts."""
        return [ACCENT, GREEN, YELLOW, TEAL, PURPLE, RED,
                PEACH, "#5fa8d3", "#9b5de5", "#52b788",
                "#3d9e8f", "#d45d5d"]

    def _style_figure(self, fig):
        """Apply the light theme to a matplotlib figure."""
        fig.patch.set_facecolor(BG)
        for ax in fig.axes:
            ax.set_facecolor(BG_CARD)
            ax.tick_params(colors=FG_DIM, labelsize=8)
            ax.xaxis.label.set_color(FG_DIM)
            ax.yaxis.label.set_color(FG_DIM)
            ax.title.set_color(FG)
            for spine in ax.spines.values():
                spine.set_color(BORDER)
                spine.set_linewidth(0.5)

    def _embed_chart(self, parent, fig, height=320):
        """Embed a matplotlib figure into a tkinter parent frame."""
        canvas = FigureCanvasTkAgg(fig, master=parent)
        widget = canvas.get_tk_widget()
        widget.configure(height=height, bg=BG)
        widget.pack(fill=tk.X, padx=15, pady=(0, 10))
        canvas.draw()
        self._chart_widgets.append(canvas)
        return canvas

    def _add_section_label(self, parent, text):
        """Add a styled section header label."""
        tk.Label(parent, text=text, font=FONT_HEADER,
                 bg=BG, fg=ACCENT).pack(anchor=tk.W, padx=15, pady=(18, 4))
        tk.Frame(parent, bg=FG_DIM, height=1).pack(fill=tk.X, padx=15, pady=(0, 8))

    def _add_stat_row(self, parent, items):
        """Add a row of stat cards. items = [(label, value, color), ...]"""
        row = tk.Frame(parent, bg=BG)
        row.pack(fill=tk.X, padx=15, pady=6)
        for label, value, color in items:
            card = tk.Frame(row, bg=BG_CARD, padx=18, pady=10)
            card.pack(side=tk.LEFT, padx=4, fill=tk.BOTH, expand=True)
            tk.Label(card, text=str(value), font=("Segoe UI", 18, "bold"),
                     bg=BG_CARD, fg=color).pack()
            tk.Label(card, text=label, font=FONT_SMALL,
                     bg=BG_CARD, fg=FG_DIM).pack()

    def _add_text_card(self, parent, title, lines, title_color=PURPLE):
        """Add a card with a title and list of text lines."""
        card = tk.Frame(parent, bg=BG_CARD, padx=15, pady=12)
        card.pack(fill=tk.X, padx=15, pady=(0, 10))
        tk.Label(card, text=title, font=FONT_BOLD,
                 bg=BG_CARD, fg=title_color).pack(anchor=tk.W)
        for line in lines:
            tk.Label(card, text=line, font=FONT_MONO,
                     bg=BG_CARD, fg=FG, anchor=tk.W,
                     justify=tk.LEFT).pack(anchor=tk.W, pady=1)

    def _build_report_text(self, data):
        """Build the full report tab with matplotlib charts and stat cards."""
        # Clear previous content
        for widget in self.report_inner.winfo_children():
            widget.destroy()
        for chart in self._chart_widgets:
            plt.close(chart.figure)
        self._chart_widgets = []

        colors = self._make_chart_colors()

        # ══════════════════════════════════════════════════════════
        # 1. REVENUE SUMMARY  (stat cards)
        # ══════════════════════════════════════════════════════════
        self._add_section_label(self.report_inner, "Revenue Summary")

        total_rev = data["total_revenue"]
        total_cust = data["total_customers"]
        avg = total_rev / total_cust if total_cust else 0

        self._add_stat_row(self.report_inner, [
            ("Total Revenue",    f"${total_rev:,.2f}",              GREEN),
            ("Items Sold",       str(data["total_items_sold"]),      ACCENT),
            ("Customers",        str(total_cust),                   TEAL),
            ("Failed Purchases", str(data["failed_purchases"]),      RED),
        ])
        self._add_stat_row(self.report_inner, [
            ("Avg / Customer",   f"${avg:,.2f}",                    PURPLE),
            ("Inventory Before", f"${data['value_before']:,.2f}",   FG),
            ("Inventory After",  f"${data['value_after']:,.2f}",    FG),
            ("Deliveries",       str(len(data.get('deliveries_log', []))), YELLOW),
        ])

        # ══════════════════════════════════════════════════════════
        # 2. REVENUE BY DAY  (bar chart + line overlay for customers)
        # ══════════════════════════════════════════════════════════
        day_sales = data.get("sales_by_day", {})
        day_custs = data.get("customers_by_day", {})
        if day_sales:
            self._add_section_label(self.report_inner, "Revenue & Customers by Day")

            fig, ax1 = plt.subplots(figsize=(8, 3.2))
            days = list(day_sales.keys())
            revs = list(day_sales.values())
            custs = [day_custs.get(d, 0) for d in days]

            bars = ax1.bar(days, revs, color=colors[:len(days)], edgecolor="none",
                           width=0.55, zorder=3)
            ax1.set_ylabel("Revenue ($)", fontsize=9)
            ax1.set_title("Daily Revenue & Customer Count", fontsize=11, fontweight="bold")
            ax1.grid(axis="y", color=FG_DIM, alpha=0.15, zorder=0)

            # Value labels on bars
            for bar, rev in zip(bars, revs):
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(revs) * 0.02,
                         f"${rev:,.0f}", ha="center", va="bottom",
                         fontsize=7, color=FG, fontweight="bold")

            # Customer count line on secondary axis
            ax2 = ax1.twinx()
            ax2.plot(days, custs, color=YELLOW, marker="o", linewidth=2.5,
                     markersize=7, zorder=5)
            ax2.set_ylabel("Customers", fontsize=9, color=YELLOW)
            ax2.tick_params(axis="y", colors=YELLOW, labelsize=8)
            for spine in ax2.spines.values():
                spine.set_visible(False)

            self._style_figure(fig)
            fig.tight_layout()
            self._embed_chart(self.report_inner, fig, height=280)

        # ══════════════════════════════════════════════════════════
        # 3. REVENUE BY TIME BLOCK  (horizontal bar chart)
        # ══════════════════════════════════════════════════════════
        time_sales = data.get("sales_by_time_block", {})
        if time_sales:
            self._add_section_label(self.report_inner, "Revenue by Time Block")

            fig, ax = plt.subplots(figsize=(8, 2.4))
            labels = list(time_sales.keys())
            values = list(time_sales.values())
            bar_colors = [ACCENT, PURPLE, GREEN, YELLOW]

            bars = ax.barh(labels[::-1], values[::-1],
                           color=bar_colors[:len(labels)][::-1],
                           edgecolor="none", height=0.55)
            ax.set_xlabel("Revenue ($)", fontsize=9)
            ax.set_title("Weekly Revenue by Time Block", fontsize=11, fontweight="bold")
            ax.grid(axis="x", color=FG_DIM, alpha=0.15)

            for bar, val in zip(bars, values[::-1]):
                ax.text(bar.get_width() + max(values) * 0.02,
                        bar.get_y() + bar.get_height() / 2,
                        f"${val:,.0f}", va="center", fontsize=8, color=FG)

            self._style_figure(fig)
            fig.tight_layout()
            self._embed_chart(self.report_inner, fig, height=220)

        # ══════════════════════════════════════════════════════════
        # 4. SHOPPER PROFILE DISTRIBUTION  (pie chart)
        # ══════════════════════════════════════════════════════════
        profile_counts = data.get("profile_counts", {})
        if profile_counts:
            self._add_section_label(self.report_inner, "Shopper Profile Distribution")

            fig, ax = plt.subplots(figsize=(6, 3.5))
            names = list(profile_counts.keys())
            counts = list(profile_counts.values())
            pie_colors = colors[:len(names)]

            wedges, texts, autotexts = ax.pie(
                counts, labels=names, colors=pie_colors,
                autopct="%1.0f%%", startangle=140,
                textprops={"fontsize": 8, "color": FG},
                pctdistance=0.78, labeldistance=1.12
            )
            for at in autotexts:
                at.set_color(BG)
                at.set_fontweight("bold")
                at.set_fontsize(7)
            ax.set_title("Customer Profile Breakdown", fontsize=11,
                         fontweight="bold", color=FG)

            self._style_figure(fig)
            fig.tight_layout()
            self._embed_chart(self.report_inner, fig, height=300)

        # ══════════════════════════════════════════════════════════
        # 5. TOP 10 MOST PURCHASED  (horizontal bar chart)
        # ══════════════════════════════════════════════════════════
        sales = data.get("sales_by_product", {})
        if sales:
            self._add_section_label(self.report_inner, "Top 10 Most Purchased Items")

            sorted_sales = sorted(sales.items(), key=lambda x: -x[1])
            top = sorted_sales[:10]
            top_names = [s[0] for s in top][::-1]
            top_qtys  = [s[1] for s in top][::-1]

            fig, ax = plt.subplots(figsize=(8, 3.5))
            gradient = [GREEN] * len(top_names)
            bars = ax.barh(top_names, top_qtys, color=gradient,
                           edgecolor="none", height=0.6)
            ax.set_xlabel("Units Sold", fontsize=9)
            ax.set_title("Top 10 Best-Selling Products", fontsize=11, fontweight="bold")
            ax.grid(axis="x", color=FG_DIM, alpha=0.15)

            for bar, val in zip(bars, top_qtys):
                ax.text(bar.get_width() + max(top_qtys) * 0.02,
                        bar.get_y() + bar.get_height() / 2,
                        str(val), va="center", fontsize=8,
                        color=FG, fontweight="bold")

            self._style_figure(fig)
            fig.tight_layout()
            self._embed_chart(self.report_inner, fig, height=300)

            # Bottom 3 as text card
            bottom = sorted_sales[-3:]
            bottom_lines = [f"{name:<22} {qty} sold" for name, qty in bottom]
            self._add_text_card(self.report_inner, "Bottom 3 Least Purchased",
                                bottom_lines, title_color=YELLOW)

        # ══════════════════════════════════════════════════════════
        # 6. TEXT CARDS  (low stock, deliveries, Friday sales)
        # ══════════════════════════════════════════════════════════
        hits = data.get("low_stock_hits", set())
        if hits:
            self._add_section_label(self.report_inner, f"Items That Hit Low Stock ({len(hits)})")
            hit_lines = [f"  \u2022  {name}" for name in sorted(hits)]
            self._add_text_card(self.report_inner, "Low Stock Alerts",
                                hit_lines, title_color=RED)

        deliveries = data.get("deliveries_log", [])
        if deliveries:
            self._add_section_label(self.report_inner, "Deliveries")
            del_lines = [f"{day}: {units} units from warehouse"
                         for day, units in deliveries]
            self._add_text_card(self.report_inner, "Warehouse Deliveries",
                                del_lines, title_color=TEAL)

        sale_items = data.get("sale_suggestions", [])
        if sale_items:
            self._add_section_label(self.report_inner, "Friday Sales Applied")
            sale_lines = [f"{p.name:<20}  sale: ${sp:.2f}" for p, sp in sale_items]
            self._add_text_card(self.report_inner, f"{len(sale_items)} Items Discounted",
                                sale_lines, title_color=GREEN)

        # Scroll to top
        self.report_canvas.yview_moveto(0)


# ─── Launch ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = MiniMeijerApp(root)
    root.mainloop()
