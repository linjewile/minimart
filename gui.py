"""
gui.py
──────
Tkinter GUI for Mini Meijer grocery store simulation.
Provides a windowed interface with tabs for:
  - Dashboard  (summary stats + time block chart)
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

from config import CONFIG
from inventory import (
    seed_inventory, inventory, purchase, restock,
    print_inventory, get_low_stock, get_total_value,
    get_products_by_category, search_by_name, add_product,
    get_all_products
)
from simulate_shopping import (
    TIME_BLOCKS, SHOPPER_PROFILES, Customer,
    get_profile_for_time_block, pick_products_by_preference,
    random_purchase_amount, PROFESSION_TO_PROFILE,
    DAY_NAMES, DAY_TRAFFIC, DELIVERY_DAYS, WAREHOUSE_STOCK,
    process_delivery, friday_sale_suggestions, apply_sales,
    HIGH_STOCK_THRESHOLD, SALE_DISCOUNT,
    RESTOCK_TARGET, DELIVERY_RESTOCK_MAX,
    WEEKEND_ALCOHOL_MARKUP
)


# ─── Color Palette ──────────────────────────────────────────────────

BG          = "#1e1e2e"      # Dark background
BG_CARD     = "#2a2a3d"      # Card/panel background
FG          = "#cdd6f4"      # Main text
FG_DIM      = "#6c7086"      # Dimmed text
ACCENT      = "#89b4fa"      # Blue accent
GREEN       = "#a6e3a1"      # Success / positive
RED         = "#f38ba8"      # Error / negative
YELLOW      = "#f9e2af"      # Warning
PURPLE      = "#cba6f7"      # Highlights
TEAL        = "#94e2d5"      # Secondary accent
HEADER_BG   = "#313244"      # Table header bg
ROW_ALT     = "#252537"      # Alternating row bg

FONT        = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_HEADER = ("Segoe UI", 14, "bold")
FONT_TITLE  = ("Segoe UI", 18, "bold")
FONT_MONO   = ("Consolas", 10)
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

        # Style configuration
        self._setup_styles()

        # Header bar
        self._build_header()

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Build each tab
        self._build_dashboard_tab()
        self._build_inventory_tab()
        self._build_simulation_tab()
        self._build_warehouse_tab()
        self._build_activity_tab()
        self._build_low_stock_tab()
        self._build_report_tab()

    # ─── Styles ─────────────────────────────────────────────────────

    def _setup_styles(self):
        """Configure ttk styles for a dark theme."""
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook
        style.configure("Dark.TNotebook", background=BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                         background=BG_CARD, foreground=FG,
                         padding=[16, 8], font=FONT_BOLD)
        style.map("Dark.TNotebook.Tab",
                   background=[("selected", ACCENT)],
                   foreground=[("selected", BG)])

        # Frames
        style.configure("Dark.TFrame", background=BG)
        style.configure("Card.TFrame", background=BG_CARD)

        # Labels
        style.configure("Dark.TLabel", background=BG, foreground=FG, font=FONT)
        style.configure("Card.TLabel", background=BG_CARD, foreground=FG, font=FONT)
        style.configure("Header.TLabel", background=BG, foreground=ACCENT, font=FONT_HEADER)
        style.configure("Stat.TLabel", background=BG_CARD, foreground=GREEN, font=("Segoe UI", 20, "bold"))
        style.configure("StatLabel.TLabel", background=BG_CARD, foreground=FG_DIM, font=FONT_SMALL)

        # Buttons
        style.configure("Accent.TButton",
                         background=ACCENT, foreground=BG,
                         font=FONT_BOLD, padding=[12, 6])
        style.map("Accent.TButton",
                   background=[("active", PURPLE)])

        style.configure("Green.TButton",
                         background=GREEN, foreground=BG,
                         font=FONT_BOLD, padding=[12, 6])
        style.map("Green.TButton",
                   background=[("active", TEAL)])

        style.configure("Red.TButton",
                         background=RED, foreground=BG,
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
                   background=[("selected", ACCENT)],
                   foreground=[("selected", BG)])

        # Entry
        style.configure("Dark.TEntry",
                         fieldbackground=BG_CARD, foreground=FG,
                         insertcolor=FG, font=FONT)

    # ─── Header ─────────────────────────────────────────────────────

    def _build_header(self):
        """Build the title bar at the top."""
        header = tk.Frame(self.root, bg=BG, height=60)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(header, text="Mini Meijer", font=FONT_TITLE,
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT)

        tk.Label(header, text="Grocery Store Simulator", font=FONT,
                 bg=BG, fg=FG_DIM).pack(side=tk.LEFT, padx=(10, 0), pady=(6, 0))

        # Run Simulation button (right side)
        self.run_btn = tk.Button(
            header, text="Run Simulation", font=FONT_BOLD,
            bg=GREEN, fg=BG, activebackground=TEAL, activeforeground=BG,
            relief=tk.FLAT, padx=16, pady=6,
            command=self._start_simulation
        )
        self.run_btn.pack(side=tk.RIGHT)

        # Load Inventory button
        self.load_btn = tk.Button(
            header, text="Load Inventory", font=FONT_BOLD,
            bg=ACCENT, fg=BG, activebackground=PURPLE, activeforeground=BG,
            relief=tk.FLAT, padx=16, pady=6,
            command=self._load_inventory
        )
        self.load_btn.pack(side=tk.RIGHT, padx=(0, 10))

    # ─── Tab 1: Dashboard ───────────────────────────────────────────

    def _build_dashboard_tab(self):
        """Build the dashboard tab with summary stat cards."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Dashboard  ")

        # Welcome message (shown before simulation)
        self.dash_welcome = tk.Label(
            frame, text="Load inventory and run a simulation to see results here.",
            font=FONT, bg=BG, fg=FG_DIM
        )
        self.dash_welcome.pack(pady=40)

        # Stats row (hidden until simulation runs)
        self.dash_stats_frame = tk.Frame(frame, bg=BG)

        self.stat_cards = {}
        stats_config = [
            ("customers",  "Customers Served", "0"),
            ("items_sold", "Items Sold",       "0"),
            ("revenue",    "Week Revenue",     "$0.00"),
            ("failed",     "Failed Purchases", "0"),
            ("inv_value",  "Inventory Value",  "$0.00"),
            ("deliveries", "Deliveries",       "0"),
        ]
        for key, label, default in stats_config:
            card = tk.Frame(self.dash_stats_frame, bg=BG_CARD, padx=20, pady=15)
            card.pack(side=tk.LEFT, padx=8, pady=10, fill=tk.BOTH, expand=True)

            val_lbl = tk.Label(card, text=default, font=("Segoe UI", 20, "bold"),
                               bg=BG_CARD, fg=GREEN)
            val_lbl.pack()
            tk.Label(card, text=label, font=FONT_SMALL,
                     bg=BG_CARD, fg=FG_DIM).pack()
            self.stat_cards[key] = val_lbl

        # Time block breakdown
        self.dash_time_frame = tk.Frame(frame, bg=BG)

        tk.Label(self.dash_time_frame, text="Revenue by Time Block",
                 font=FONT_HEADER, bg=BG, fg=ACCENT).pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.time_block_canvas = tk.Canvas(self.dash_time_frame, bg=BG,
                                            highlightthickness=0, height=180)
        self.time_block_canvas.pack(fill=tk.X, padx=10, pady=5)

        # Daily revenue chart
        tk.Label(self.dash_time_frame, text="Revenue by Day",
                 font=FONT_HEADER, bg=BG, fg=ACCENT).pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.day_canvas = tk.Canvas(self.dash_time_frame, bg=BG,
                                    highlightthickness=0, height=300)
        self.day_canvas.pack(fill=tk.X, padx=10, pady=5)

    # ─── Tab 2: Inventory ───────────────────────────────────────────

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
                                insertbackground=FG, relief=tk.FLAT, width=30)
        search_entry.pack(side=tk.LEFT, padx=(8, 0))

        # Refresh button
        tk.Button(search_frame, text="Refresh", font=FONT_BOLD,
                  bg=ACCENT, fg=BG, relief=tk.FLAT, padx=10,
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
        self.sim_text.tag_config("header",  foreground=ACCENT,  font=("Consolas", 11, "bold"))
        self.sim_text.tag_config("success", foreground=GREEN)
        self.sim_text.tag_config("error",   foreground=RED)
        self.sim_text.tag_config("warning", foreground=YELLOW)
        self.sim_text.tag_config("info",    foreground=PURPLE)
        self.sim_text.tag_config("dim",     foreground=FG_DIM)
        self.sim_text.tag_config("customer", foreground=TEAL, font=("Consolas", 10, "bold"))

    # ─── Tab 4: Warehouse ────────────────────────────────────────

    def _build_warehouse_tab(self):
        """Build the warehouse inventory tab showing stock per category."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Warehouse  ")

        # Header
        top = tk.Frame(frame, bg=BG)
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="Warehouse Inventory",
                 font=FONT_HEADER, bg=BG, fg=TEAL).pack(side=tk.LEFT)

        tk.Button(top, text="Refresh", font=FONT_BOLD,
                  bg=ACCENT, fg=BG, relief=tk.FLAT, padx=10,
                  command=self._refresh_warehouse
                  ).pack(side=tk.RIGHT)

        # Info bar
        info = tk.Frame(frame, bg=BG_CARD, padx=15, pady=10)
        info.pack(fill=tk.X, padx=10, pady=(0, 5))

        tk.Label(info, text="Delivery Schedule:", font=FONT_BOLD,
                 bg=BG_CARD, fg=FG).pack(side=tk.LEFT)
        tk.Label(info, text=f"  {', '.join(DELIVERY_DAYS)}  (before store opens)",
                 font=FONT, bg=BG_CARD, fg=TEAL).pack(side=tk.LEFT)

        self.wh_total_label = tk.Label(info, text="Total per delivery: --",
                                        font=FONT, bg=BG_CARD, fg=FG_DIM)
        self.wh_total_label.pack(side=tk.RIGHT)

        # Warehouse stock table
        cols = ("category", "per_delivery", "products", "per_product")
        self.wh_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                     style="Dark.Treeview", height=10)
        self.wh_tree.heading("category",     text="Category")
        self.wh_tree.heading("per_delivery", text="Units / Delivery")
        self.wh_tree.heading("products",     text="Products in Category")
        self.wh_tree.heading("per_product",  text="Units / Product")

        self.wh_tree.column("category",     width=160, anchor=tk.W)
        self.wh_tree.column("per_delivery", width=140, anchor=tk.E)
        self.wh_tree.column("products",     width=160, anchor=tk.E)
        self.wh_tree.column("per_product",  width=140, anchor=tk.E)

        self.wh_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # Daily reports section
        tk.Label(frame, text="Daily Reports",
                 font=FONT_HEADER, bg=BG, fg=TEAL
                 ).pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.delivery_text = scrolledtext.ScrolledText(
            frame, font=FONT_MONO, bg=BG_CARD, fg=FG,
            insertbackground=FG, relief=tk.FLAT,
            wrap=tk.WORD, state=tk.DISABLED, height=12
        )
        self.delivery_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.delivery_text.tag_config("header", foreground=ACCENT, font=("Consolas", 10, "bold"))
        self.delivery_text.tag_config("success", foreground=GREEN)
        self.delivery_text.tag_config("warning", foreground=YELLOW)
        self.delivery_text.tag_config("error", foreground=RED)
        self.delivery_text.tag_config("dim", foreground=FG_DIM)
        self.delivery_text.tag_config("info", foreground=TEAL)

        # Initial populate
        self._refresh_warehouse()

    def _refresh_warehouse(self):
        """Refresh the warehouse stock table with current data."""
        self.wh_tree.delete(*self.wh_tree.get_children())

        total_units = 0
        for i, (category, units) in enumerate(WAREHOUSE_STOCK.items()):
            # Count products in this category currently in inventory
            products_in_cat = [
                e.value for e in inventory.all_entries()
                if e.value.category == category
            ]
            num_products = len(products_in_cat)
            per_product = units // num_products if num_products > 0 else 0
            total_units += units

            tag = "alt" if i % 2 else ""
            self.wh_tree.insert("", tk.END, values=(
                category, units, num_products,
                per_product if num_products > 0 else "N/A"
            ), tags=(tag,))

        self.wh_tree.tag_configure("alt", background=ROW_ALT)
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
                                     font=("Consolas", 10, "bold"))
        self.hist_tree.tag_configure("high_roller", foreground=YELLOW,
                                     font=("Consolas", 10, "bold"))
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

        tk.Button(top, text=f"Auto-Restock All to {RESTOCK_TARGET}", font=FONT_BOLD,
                  bg=GREEN, fg=BG, relief=tk.FLAT, padx=12,
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
        """Build the detailed report tab."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Report  ")

        self.report_text = scrolledtext.ScrolledText(
            frame, font=FONT_MONO, bg=BG_CARD, fg=FG,
            insertbackground=FG, relief=tk.FLAT,
            wrap=tk.WORD, state=tk.DISABLED
        )
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.report_text.tag_config("header",  foreground=ACCENT, font=("Consolas", 12, "bold"))
        self.report_text.tag_config("success", foreground=GREEN)
        self.report_text.tag_config("warning", foreground=YELLOW)
        self.report_text.tag_config("info",    foreground=PURPLE)
        self.report_text.tag_config("dim",     foreground=FG_DIM)

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

            # ── Weekend alcohol price surge (Sat & Sun) ─────────────
            alcohol_originals = {}  # product_id -> original_price
            if day_name in ("Saturday", "Sunday"):
                for entry in inventory.all_entries():
                    p = entry.value
                    if p.category == "Alcohol":
                        alcohol_originals[p.id] = p.price
                        p.price = round(p.price * (1 + WEEKEND_ALCOHOL_MARKUP), 2)
                self._log(f"\n  [WEEKEND SURGE] Alcohol prices "
                          f"+{int(WEEKEND_ALCOHOL_MARKUP * 100)}% today\n", "warning")

            # ── Time blocks for this day ────────────────────────────
            for block_index, block in enumerate(TIME_BLOCKS):
                block_label = block["label"]
                block_customers = max(1, int(block["customers"] * traffic))
                block_max_cart = block["max_cart"]
                block_revenue = 0.0

                self._log(f"\n  --- {day_name} | {block_label} "
                          f"({block_customers} customers) ---\n", "dim")

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

                    time.sleep(CONFIG["gui_delay"])

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

    def _update_after_simulation(self):
        """Update all GUI elements after the simulation completes."""
        data = self.report_data
        if not data:
            return

        # Dashboard stat cards
        self.dash_welcome.pack_forget()
        self.dash_stats_frame.pack(fill=tk.X, padx=10)
        self.dash_time_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        self.stat_cards["customers"].config(text=str(data["total_customers"]))
        self.stat_cards["items_sold"].config(text=str(data["total_items_sold"]))
        self.stat_cards["revenue"].config(text=f"${data['total_revenue']:,.2f}")
        self.stat_cards["failed"].config(
            text=str(data["failed_purchases"]),
            fg=RED if data["failed_purchases"] > 0 else GREEN
        )
        self.stat_cards["inv_value"].config(text=f"${data['value_after']:,.2f}")
        self.stat_cards["deliveries"].config(
            text=str(len(data.get("deliveries_log", []))),
            fg=TEAL
        )

        # Draw time block bars
        self._draw_time_blocks(data["sales_by_time_block"], data["total_revenue"])

        # Draw daily revenue bars
        self._draw_daily_revenue(data.get("sales_by_day", {}),
                                 data.get("customers_by_day", {}),
                                 data["total_revenue"])

        # Refresh tables
        self._refresh_inventory_table()
        self._refresh_low_stock()
        self._refresh_warehouse()
        self._refresh_delivery_history()

        # Build report
        self._build_report_text(data)

        # Re-enable buttons
        self.sim_running = False
        self.run_btn.configure(text="Run Again", bg=GREEN, state=tk.NORMAL)
        self.load_btn.configure(text="Reload Inventory", bg=ACCENT, state=tk.NORMAL)

    def _draw_time_blocks(self, time_sales, total_revenue):
        """Draw horizontal bar chart for revenue by time block."""
        canvas = self.time_block_canvas
        canvas.delete("all")

        if not time_sales or total_revenue == 0:
            return

        canvas_width = canvas.winfo_width() or 900
        bar_height = 32
        y = 10
        max_rev = max(time_sales.values()) if time_sales else 1
        bar_colors = [ACCENT, PURPLE, GREEN, YELLOW]

        for i, (label, rev) in enumerate(time_sales.items()):
            pct = (rev / total_revenue * 100) if total_revenue else 0
            bar_width = int((rev / max_rev) * (canvas_width - 350))

            color = bar_colors[i % len(bar_colors)]

            # Label
            canvas.create_text(10, y + bar_height // 2, text=label,
                               anchor=tk.W, fill=FG, font=FONT_SMALL)

            # Bar
            x_start = 200
            canvas.create_rectangle(x_start, y + 4, x_start + bar_width, y + bar_height - 4,
                                     fill=color, outline="")

            # Value label
            canvas.create_text(x_start + bar_width + 8, y + bar_height // 2,
                               text=f"${rev:,.2f} ({pct:.1f}%)",
                               anchor=tk.W, fill=FG_DIM, font=FONT_SMALL)

            y += bar_height + 8

    def _draw_daily_revenue(self, day_sales, day_customers, total_revenue):
        """Draw horizontal bar chart for revenue by day of week."""
        canvas = self.day_canvas
        canvas.delete("all")

        if not day_sales or total_revenue == 0:
            return

        canvas_width = canvas.winfo_width() or 900
        bar_height = 30
        y = 10
        max_rev = max(day_sales.values()) if day_sales else 1
        day_colors = [ACCENT, TEAL, PURPLE, FG_DIM, YELLOW, GREEN, RED]

        for i, (day, rev) in enumerate(day_sales.items()):
            pct = (rev / total_revenue * 100) if total_revenue else 0
            bar_width = int((rev / max_rev) * (canvas_width - 400))
            custs = day_customers.get(day, 0)
            color = day_colors[i % len(day_colors)]

            # Day label
            canvas.create_text(10, y + bar_height // 2, text=day,
                               anchor=tk.W, fill=FG, font=FONT_SMALL)

            # Bar
            x_start = 100
            canvas.create_rectangle(x_start, y + 3, x_start + bar_width, y + bar_height - 3,
                                     fill=color, outline="")

            # Value + customer count
            canvas.create_text(x_start + bar_width + 8, y + bar_height // 2,
                               text=f"${rev:,.2f} ({pct:.1f}%)  --  {custs} customers",
                               anchor=tk.W, fill=FG_DIM, font=FONT_SMALL)

            y += bar_height + 6

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

        # Update inventory value on dashboard
        if self.report_data:
            self.stat_cards["inv_value"].config(text=f"${get_total_value():,.2f}")

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

    def _build_report_text(self, data):
        """Fill the report tab with formatted stats."""
        rt = self.report_text
        rt.configure(state=tk.NORMAL)
        rt.delete("1.0", tk.END)

        rt.insert(tk.END, "=" * 55 + "\n", "header")
        rt.insert(tk.END, "  DETAILED WEEKLY REPORT\n", "header")
        rt.insert(tk.END, "=" * 55 + "\n\n", "header")

        # Revenue section
        rt.insert(tk.END, "  REVENUE\n", "info")
        rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
        avg = data["total_revenue"] / data["total_customers"] if data["total_customers"] else 0
        lines = [
            f"  Total revenue:          ${data['total_revenue']:,.2f}",
            f"  Total items sold:       {data['total_items_sold']}",
            f"  Failed purchases:       {data['failed_purchases']}",
            f"  Inventory before:       ${data['value_before']:,.2f}",
            f"  Inventory after:        ${data['value_after']:,.2f}",
            f"  Value decrease:         ${data['value_before'] - data['value_after']:,.2f}",
            f"  Avg spend / customer:   ${avg:,.2f}",
            f"  Deliveries received:    {len(data.get('deliveries_log', []))}",
        ]
        for line in lines:
            rt.insert(tk.END, line + "\n")

        # Revenue by day
        day_sales = data.get("sales_by_day", {})
        if day_sales:
            rt.insert(tk.END, "\n  REVENUE BY DAY\n", "info")
            rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
            custs = data.get("customers_by_day", {})
            for day, rev in day_sales.items():
                pct = (rev / data['total_revenue'] * 100) if data['total_revenue'] else 0
                c = custs.get(day, 0)
                bar = "#" * int(pct / 2)
                rt.insert(tk.END, f"  {day:<12} ${rev:>8,.2f}  ({pct:4.1f}%)  "
                                  f"{c:>3} cust  {bar}\n")

        # Time block breakdown
        rt.insert(tk.END, "\n  REVENUE BY TIME BLOCK (weekly)\n", "info")
        rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
        for label, rev in data["sales_by_time_block"].items():
            pct = (rev / data["total_revenue"] * 100) if data["total_revenue"] else 0
            bar = "\u2588" * int(pct / 2)
            rt.insert(tk.END, f"  {label:<25} ${rev:>8,.2f} ({pct:4.1f}%)  {bar}\n")

        # Profile distribution
        rt.insert(tk.END, "\n  SHOPPER PROFILE DISTRIBUTION\n", "info")
        rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
        profile_counts = data.get("profile_counts", {})
        for name, count in sorted(profile_counts.items(), key=lambda x: -x[1]):
            bar = "\u2588" * count
            rt.insert(tk.END, f"  {name:<22} {count:>3} shoppers  {bar}\n")

        # Top products
        sales = data["sales_by_product"]
        if sales:
            sorted_sales = sorted(sales.items(), key=lambda x: -x[1])
            rt.insert(tk.END, "\n  TOP 5 MOST PURCHASED\n", "info")
            rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
            for rank, (name, qty) in enumerate(sorted_sales[:5], 1):
                bar = "\u2588" * qty
                rt.insert(tk.END, f"  {rank}. {name:<20} {qty:>3} sold  {bar}\n", "success")

            rt.insert(tk.END, "\n  BOTTOM 3 LEAST PURCHASED\n", "info")
            rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
            for name, qty in sorted_sales[-3:]:
                rt.insert(tk.END, f"  {name:<22} {qty:>3} sold\n", "warning")

        # Low stock hits
        hits = data["low_stock_hits"]
        if hits:
            rt.insert(tk.END, f"\n  ITEMS THAT HIT LOW STOCK ({len(hits)})\n", "warning")
            rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
            for name in sorted(hits):
                rt.insert(tk.END, f"  - {name}\n", "warning")

        # Deliveries
        deliveries = data.get("deliveries_log", [])
        if deliveries:
            rt.insert(tk.END, f"\n  DELIVERIES\n", "info")
            rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
            for day, units in deliveries:
                rt.insert(tk.END, f"  {day}: {units} units from warehouse\n")

        # Friday sales
        sale_items = data.get("sale_suggestions", [])
        if sale_items:
            rt.insert(tk.END, f"\n  FRIDAY SALES APPLIED ({len(sale_items)} items)\n", "info")
            rt.insert(tk.END, "  " + "-" * 40 + "\n", "dim")
            for p, sale_price in sale_items:
                rt.insert(tk.END, f"  {p.name:<20} sale: ${sale_price:.2f}\n", "success")

        rt.insert(tk.END, "\n" + "=" * 55 + "\n", "header")
        rt.configure(state=tk.DISABLED)


# ─── Launch ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = MiniMeijerApp(root)
    root.mainloop()
