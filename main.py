"""
Local Lead Finder - Free Lite Edition (GitHub Open-Source)
Extracts up to 10 local leads. Upgrade to Pro Edition for unlimited leads & email scraper.
"""

import os
import sys
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk
from models import Lead
from scraper import GoogleMapsScraper
from exporter import export_to_excel, export_to_csv

GUMROAD_URL = "https://mhmadkadoor.gumroad.com/l/local-lead-finder"
SHOPIER_URL = "https://shopier.com"  # Replace with your Shopier link

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class LiteLeadFinderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Local Lead Finder (Free Lite Version - Max 10 Leads)")
        self.geometry("1060x720")
        self.minsize(940, 640)

        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.leads: List[Lead] = []
        self.is_scraping = False
        self.stop_event = threading.Event()

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Pro Upsell Header Banner
        banner = ctk.CTkFrame(self, corner_radius=0, fg_color="#1E3A8A", height=54)
        banner.grid(row=0, column=0, sticky="ew")

        b_text = ctk.CTkLabel(
            banner,
            text="⚡ FREE LITE VERSION (Max 10 Leads • No Email Hunter) — Upgrade to Pro for Unlimited Leads + Email Crawler + Standalone .exe!",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#F8FAFC"
        )
        b_text.pack(side="left", padx=20, pady=12)

        btn_gumroad = ctk.CTkButton(
            banner,
            text="Get Pro on Gumroad ($9.99)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#F59E0B",
            text_color="#000000",
            hover_color="#D97706",
            height=28,
            command=lambda: webbrowser.open(GUMROAD_URL)
        )
        btn_gumroad.pack(side="right", padx=(6, 20))

        btn_shopier = ctk.CTkButton(
            banner,
            text="Shopier (290 TL)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#10B981",
            text_color="#FFFFFF",
            hover_color="#059669",
            height=28,
            command=lambda: webbrowser.open(SHOPIER_URL)
        )
        btn_shopier.pack(side="right", padx=6)

        # 2. Controls Frame
        controls = ctk.CTkFrame(self, corner_radius=8, fg_color="#1E293B")
        controls.grid(row=1, column=0, sticky="ew", padx=16, pady=12)

        input_row = ctk.CTkFrame(controls, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=12)
        input_row.grid_columnconfigure((0, 1), weight=1)

        # Query
        q_box = ctk.CTkFrame(input_row, fg_color="transparent")
        q_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(q_box, text="Business Category / Query", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.entry_query = ctk.CTkEntry(q_box, placeholder_text="e.g. Dentists, Cafes, Plumbers", height=36)
        self.entry_query.pack(fill="x", pady=(4, 0))

        # Location
        loc_box = ctk.CTkFrame(input_row, fg_color="transparent")
        loc_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(loc_box, text="Target Location / City", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.entry_location = ctk.CTkEntry(loc_box, placeholder_text="e.g. Austin, TX or London, UK", height=36)
        self.entry_location.pack(fill="x", pady=(4, 0))

        # Action Buttons Row
        btn_row = ctk.CTkFrame(controls, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 12))

        lbl_limit = ctk.CTkLabel(
            btn_row,
            text="Note: Free Lite edition extracts up to 10 results per search.",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        lbl_limit.pack(side="left")

        btn_cluster = ctk.CTkFrame(btn_row, fg_color="transparent")
        btn_cluster.pack(side="right")

        self.btn_start = ctk.CTkButton(
            btn_cluster, text="▶ Start Scraping (10 Leads)", fg_color="#10B981", hover_color="#059669",
            font=ctk.CTkFont(size=12, weight="bold"), height=32, command=self._start_scraping
        )
        self.btn_start.pack(side="left", padx=4)

        self.btn_stop = ctk.CTkButton(
            btn_cluster, text="⏹ Stop", fg_color="#EF4444", hover_color="#DC2626",
            font=ctk.CTkFont(size=12, weight="bold"), height=32, width=70, state="disabled", command=self._stop_scraping
        )
        self.btn_stop.pack(side="left", padx=4)

        self.btn_export = ctk.CTkButton(
            btn_cluster, text="📊 Export Excel", fg_color="#2563EB", hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12, weight="bold"), height=32, state="disabled", command=self._export_excel
        )
        self.btn_export.pack(side="left", padx=4)

        # 3. Status Bar
        status_bar = ctk.CTkFrame(self, corner_radius=6, fg_color="#0F172A", height=36)
        status_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.lbl_status = ctk.CTkLabel(status_bar, text="Status: Ready", font=ctk.CTkFont(size=11), text_color="#38BDF8")
        self.lbl_status.pack(side="left", padx=12, pady=6)

        # 4. Results Table
        table_card = ctk.CTkFrame(self, corner_radius=8, fg_color="#1E293B")
        table_card.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 14))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#0F172A", foreground="#F8FAFC", fieldbackground="#0F172A", rowheight=26)
        style.configure("Treeview.Heading", background="#1E293B", foreground="#93C5FD", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#2563EB")], foreground=[("selected", "#FFFFFF")])

        cols = ["#", "Name", "Phone", "Email", "Website", "Rating", "Address", "Maps Link"]
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")
        col_widths = [35, 170, 120, 130, 140, 60, 220, 160]
        for idx, c in enumerate(cols):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=col_widths[idx], anchor="center" if idx in (0, 2, 5) else "w")

        ysb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(table_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._on_double_click)

    def _start_scraping(self):
        query = self.entry_query.get().strip()
        loc = self.entry_location.get().strip()
        if not query:
            messagebox.showwarning("Input Required", "Please enter a business category or query.")
            return

        self.leads.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.is_scraping = True
        self.stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_export.configure(state="disabled")

        scraper = GoogleMapsScraper(
            query=query,
            location=loc,
            max_results=10,
            on_lead=self._add_lead,
            on_status=lambda msg: self.after(0, lambda: self.lbl_status.configure(text=msg)),
            on_finished=self._on_finished,
            stop_event=self.stop_event,
        )
        threading.Thread(target=scraper.run, daemon=True).start()

    def _add_lead(self, lead: Lead):
        def update():
            self.leads.append(lead)
            self.tree.insert("", "end", values=(
                len(self.leads), lead.name, lead.phone or "", lead.email,
                lead.website or "", lead.rating or "", lead.address or "", lead.google_maps_url or ""
            ))
        self.after(0, update)

    def _on_finished(self, total: int):
        def update():
            self.is_scraping = False
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            if self.leads:
                self.btn_export.configure(state="normal")
            self.lbl_status.configure(text=f"Completed: {total} leads. Upgrade to Pro for unlimited leads!")
            messagebox.showinfo(
                "Lite Search Finished",
                f"Extracted {total} leads!\n\nWant unlimited leads, website email extraction, and a standalone .exe with no Python required?\nCheck out the Pro Edition on Gumroad & Shopier!"
            )
        self.after(0, update)

    def _stop_scraping(self):
        if self.is_scraping:
            self.stop_event.set()
            self.btn_stop.configure(state="disabled")

    def _export_excel(self):
        if not self.leads:
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            export_to_excel(self.leads, path)
            messagebox.showinfo("Exported", f"Successfully saved {len(self.leads)} leads to:\n{path}")

    def _on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not item_id or not col_id:
            return
        col_idx = int(col_id.replace("#", "")) - 1
        values = self.tree.item(item_id, "values")
        if values and col_idx < len(values):
            val = str(values[col_idx]).strip()
            if val:
                self.clipboard_clear()
                self.clipboard_append(val)
                self.lbl_status.configure(text=f"Copied: '{val[:40]}'")


if __name__ == "__main__":
    app = LiteLeadFinderGUI()
    app.mainloop()
