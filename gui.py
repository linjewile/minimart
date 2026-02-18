"""
gui.py
──────
Tkinter GUI for Mini Meijer grocery store simulation.
Provides a windowed interface with tabs for:
  - Dashboard  (summary stats + time block chart)
  - Inventory  (full product table with search/filter)
  - Simulation Log  (scrollable feed of every transaction)
  - Low Stock  (products that need restocking)
  - Report     (detailed sales breakdown)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
import time
import threading

from inventory import (
    seed_inventory, inventory, purchase, restock,
    print_inventory, get_low_stock, get_total_value,
    get_products_by_category, search_by_name, add_product
)
from simulate_shopping import (
    TIME_BLOCKS, SHOPPER_PROFILES, Customer,
    get_profile_for_time_block, pick_products_by_preference,
    random_purchase_amount, get_all_products, PROFESSION_TO_PROFILE
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
            ("revenue",    "Total Revenue",    "$0.00"),
            ("failed",     "Failed Purchases", "0"),
            ("inv_value",  "Inventory Value",  "$0.00"),
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

    # ─── Tab 4: Low Stock ───────────────────────────────────────────

    def _build_low_stock_tab(self):
        """Build the low stock alerts tab."""
        frame = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(frame, text="  Low Stock  ")

        # Top bar with auto-restock button
        top = tk.Frame(frame, bg=BG)
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="Products at or below 10 units",
                 font=FONT_HEADER, bg=BG, fg=YELLOW).pack(side=tk.LEFT)

        tk.Button(top, text="Auto-Restock All to 50", font=FONT_BOLD,
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

    # ─── Tab 5: Report ──────────────────────────────────────────────

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
        """The simulation logic — runs on a background thread."""
        value_before = get_total_value()
        total_customers = sum(b["customers"] for b in TIME_BLOCKS)

        self._log("=" * 58 + "\n", "header")
        self._log("  Mini Meijer -- Shopping Simulation\n", "header")
        self._log("=" * 58 + "\n\n", "header")
        self._log(f"  Starting inventory value: ${value_before:,.2f}\n", "info")
        self._log(f"  Simulating {total_customers} customers across "
                  f"{len(TIME_BLOCKS)} time blocks...\n\n", "dim")

        total_items_sold = 0
        total_revenue = 0.0
        failed_purchases = 0
        sales_by_product = {}
        low_stock_hits = set()
        sales_by_time_block = {}
        customer_num = 0
        profile_counts = {}       # Track how many of each profile appeared

        for block_index, block in enumerate(TIME_BLOCKS):
            block_label = block["label"]
            block_customers = block["customers"]
            block_max_cart = block["max_cart"]
            block_revenue = 0.0

            self._log("\n" + "=" * 58 + "\n", "header")
            self._log(f"  TIME BLOCK: {block_label}\n", "header")
            self._log(f"  Hours: {block['hours']}  |  "
                      f"Expected customers: {block_customers}\n", "dim")
            self._log("=" * 58 + "\n", "header")

            for j in range(1, block_customers + 1):
                customer_num += 1

                profile_name, profile = get_profile_for_time_block(block_index)
                customer = Customer(profile_name, profile)
                products = get_all_products()

                # Track profile distribution
                profile_counts[profile_name] = profile_counts.get(profile_name, 0) + 1

                if not products:
                    self._log("  [!] No products left in stock!\n", "error")
                    break

                cart = pick_products_by_preference(products, profile, block_max_cart)

                self._log(f"\n  Customer #{customer_num}: ", "customer")
                self._log(f"{customer}\n", "info")

                customer_total = 0.0
                customer_items = 0

                for product in cart:
                    qty = random_purchase_amount()

                    if product.quantity >= qty:
                        purchase(product.id, qty)
                        item_cost = product.price * qty
                        total_items_sold += qty
                        total_revenue += item_cost
                        block_revenue += item_cost
                        customer_total += item_cost
                        customer_items += qty
                        sales_by_product[product.name] = (
                            sales_by_product.get(product.name, 0) + qty
                        )
                        if product.quantity <= 10:
                            low_stock_hits.add(product.name)

                        self._log(f"    [OK] {qty}x {product.name} "
                                  f"(${item_cost:.2f})  -- {product.quantity} left\n", "success")
                    else:
                        self._log(f"    [X] Wanted {qty}x {product.name} "
                                  f"but only {product.quantity} left\n", "error")
                        failed_purchases += 1

                self._log(f"  >> {customer.first_name}'s total: "
                          f"{customer_items} items -- ${customer_total:,.2f}\n", "dim")

                time.sleep(0.15)  # Brief pause for readability

            sales_by_time_block[block_label] = block_revenue
            self._log(f"\n  -- {block_label} revenue: ${block_revenue:,.2f} --\n", "info")

        # Summary
        value_after = get_total_value()

        self._log("\n" + "=" * 58 + "\n", "header")
        self._log("  Simulation Complete!\n", "header")
        self._log("=" * 58 + "\n", "header")

        # Store report data
        self.report_data = {
            "total_revenue":      total_revenue,
            "total_items_sold":   total_items_sold,
            "total_customers":    total_customers,
            "failed_purchases":   failed_purchases,
            "value_before":       value_before,
            "value_after":        value_after,
            "sales_by_product":   sales_by_product,
            "low_stock_hits":     low_stock_hits,
            "sales_by_time_block": sales_by_time_block,
            "profile_counts":     profile_counts,
        }

        # Update all tabs from main thread
        self.root.after(0, self._update_after_simulation)

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

        # Draw time block bars
        self._draw_time_blocks(data["sales_by_time_block"], data["total_revenue"])

        # Refresh tables
        self._refresh_inventory_table()
        self._refresh_low_stock()

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
        """Restock all low items to 50 units."""
        low = get_low_stock()
        if not low:
            messagebox.showinfo("All Good", "No items need restocking.")
            return

        count = 0
        for p in low:
            amount = 50 - p.quantity
            if amount > 0:
                restock(p.id, amount)
                count += 1

        self._refresh_inventory_table()
        self._refresh_low_stock()

        # Update inventory value on dashboard
        if self.report_data:
            self.stat_cards["inv_value"].config(text=f"${get_total_value():,.2f}")

        messagebox.showinfo("Restocked", f"Restocked {count} items to 50 units each.")

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
        rt.insert(tk.END, "  DETAILED SIMULATION REPORT\n", "header")
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
        ]
        for line in lines:
            rt.insert(tk.END, line + "\n")

        # Time block breakdown
        rt.insert(tk.END, "\n  SALES BY TIME BLOCK\n", "info")
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

        rt.insert(tk.END, "\n" + "=" * 55 + "\n", "header")
        rt.configure(state=tk.DISABLED)


# ─── Launch ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = MiniMeijerApp(root)
    root.mainloop()
