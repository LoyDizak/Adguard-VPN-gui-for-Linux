"""
ui_location_panel.py — Right-side scrollable location list panel.

Features
--------
• Search / filter field
• "Fastest locations" section (sorted by ping)
• "All locations" section (alphabetical)
• Click a row → immediately triggers connect (callback)
• Ping badge coloured orange → green by speed
• Hover highlight on rows
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

import ui_theme as T
from backend import VpnLocation


# Ping thresholds for badge colouring
_PING_FAST   = 80    # ≤ this: green
_PING_MEDIUM = 200   # ≤ this: orange, else red


def _ping_color(ping: int) -> str:
    if ping <= _PING_FAST:
        return T.ACCENT_GREEN
    if ping <= _PING_MEDIUM:
        return T.ACCENT_ORANGE
    return T.ACCENT_RED


# ── Section header widget ──────────────────────────────────────────────────

class _SectionHeader(tk.Frame):
    def __init__(self, parent, title: str):
        super().__init__(parent, bg=T.BG_PANEL)
        tk.Label(
            self, text=title.upper(),
            font=("Helvetica", 8, "bold"),
            fg=T.TEXT_SECONDARY,
            bg=T.BG_PANEL,
            pady=4,
        ).pack(side="left", padx=T.PAD)


# ── Individual location row ────────────────────────────────────────────────

class _LocationRow(tk.Frame):
    """
    A single clickable row representing one VPN location.

    Parameters
    ----------
    on_select : callable(VpnLocation) — triggered on click
    is_connected : bool — highlight if this is the active location
    """

    def __init__(
        self,
        parent,
        location: VpnLocation,
        on_select: Callable[[VpnLocation], None],
        is_connected: bool = False,
        on_mousewheel: Callable = None,
    ):
        super().__init__(
            parent,
            bg=T.BG_ITEM_ACTIVE if is_connected else T.BG_ITEM,
            cursor="hand2",
        )
        self._location = location
        self._on_select = on_select
        self._is_connected = is_connected
        self._on_mousewheel = on_mousewheel

        self._build()
        self._bind_hover()

    def _build(self):
        self.columnconfigure(1, weight=1)

        # Country + city column
        text_col = tk.Frame(self, bg=self["bg"])
        text_col.grid(row=0, column=0, columnspan=2, sticky="w",
                      padx=(T.PAD, 0), pady=T.PAD_S)

        tk.Label(
            text_col,
            text=self._location.country,
            font=T.FONT_BODY_BOLD,
            fg=T.TEXT_PRIMARY,
            bg=self["bg"],
        ).pack(side="left")

        tk.Label(
            text_col,
            text=f"  {self._location.city}",
            font=T.FONT_BODY,
            fg=T.TEXT_SECONDARY,
            bg=self["bg"],
        ).pack(side="left")

        # Ping badge (right side)
        ping_lbl = tk.Label(
            self,
            text=f"{self._location.ping_estimate} ms",
            font=("Helvetica", 9, "bold"),
            fg=_ping_color(self._location.ping_estimate),
            bg=self["bg"],
        )
        ping_lbl.grid(row=0, column=2, padx=(0, T.PAD), pady=T.PAD_S, sticky="e")

        # Thin bottom divider
        div = tk.Frame(self, bg=T.BORDER, height=1)
        div.grid(row=1, column=0, columnspan=3, sticky="ew")

        # Make divider + children participte in hover
        self._all_children = [self, text_col, ping_lbl, div] + list(
            text_col.winfo_children()
        )

    def _bind_hover(self):
        normal_bg = self["bg"]
        hover_bg  = T.BG_ITEM_HOVER if not self._is_connected else T.BG_ITEM_ACTIVE

        def enter(_):
            for w in self._all_children:
                try:
                    w.configure(bg=hover_bg)
                except tk.TclError:
                    pass

        def leave(_):
            for w in self._all_children:
                try:
                    w.configure(bg=normal_bg)
                except tk.TclError:
                    pass

        def click(_):
            self._on_select(self._location)

        for widget in self._all_children:
            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)
            widget.bind("<Button-1>", click)
            if self._on_mousewheel:
                widget.bind("<MouseWheel>", self._on_mousewheel)
                widget.bind("<Button-4>", self._on_mousewheel)
                widget.bind("<Button-5>", self._on_mousewheel)


# ── Location Panel ─────────────────────────────────────────────────────────

class LocationPanel(tk.Frame):
    """
    Scrollable right panel showing all available VPN locations.

    on_location_selected(city_name: Optional[str]) is called immediately
    when the user clicks a row (None = automatic).
    """

    def __init__(
        self,
        parent,
        on_location_selected: Callable[[Optional[str]], None],
        **kwargs,
    ):
        super().__init__(parent, bg=T.BG_PANEL, **kwargs)
        self._on_location_selected = on_location_selected
        self._all_locations: List[VpnLocation] = []
        self._connected_city: Optional[str] = None
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)

        self._build()

    # ── Build ──────────────────────────────────────────────────────────

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ── Search bar ─────────────────────────────────────────────────
        search_outer = tk.Frame(self, bg=T.BG_PANEL, pady=T.PAD)
        search_outer.grid(row=0, column=0, sticky="ew", padx=T.PAD)

        search_inner = tk.Frame(search_outer, bg=T.BG_ITEM,
                                padx=T.PAD_S, pady=T.PAD_S)
        search_inner.pack(fill="x")

        tk.Label(search_inner, text="⌕", font=("Helvetica", 12),
                 fg=T.TEXT_SECONDARY, bg=T.BG_ITEM).pack(side="left")

        self._search_entry = tk.Entry(
            search_inner,
            textvariable=self._search_var,
            font=T.FONT_BODY,
            bg=T.BG_ITEM,
            fg=T.TEXT_PRIMARY,
            insertbackground=T.TEXT_PRIMARY,
            relief="flat",
            bd=0,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._search_entry.insert(0, "")

        # Placeholder simulation
        self._search_entry.bind("<FocusIn>",  self._on_search_focus_in)
        self._search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self._search_placeholder_active = False
        self._set_search_placeholder()

        # ── Scrollable list container ──────────────────────────────────
        list_outer = tk.Frame(self, bg=T.BG_PANEL)
        list_outer.grid(row=1, column=0, sticky="nsew")
        list_outer.rowconfigure(0, weight=1)
        list_outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(list_outer, bg=T.BG_PANEL,
                           highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_outer, orient="vertical",
                                  command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        self._scroll_canvas = canvas
        self._list_frame = tk.Frame(canvas, bg=T.BG_PANEL)
        self._canvas_window = canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw"
        )

        self._list_frame.bind("<Configure>", self._on_list_frame_configure)
        canvas.bind("<Configure>",           self._on_canvas_configure)

        # Mousewheel events for both canvas and list frame
        for widget in [canvas, self._list_frame, self]:
            widget.bind("<MouseWheel>",          self._on_mousewheel)
            widget.bind("<Button-4>",            self._on_mousewheel)
            widget.bind("<Button-5>",            self._on_mousewheel)

        # Loading placeholder
        self._loading_label = tk.Label(
            self._list_frame, text="Loading locations…",
            font=T.FONT_BODY, fg=T.TEXT_SECONDARY, bg=T.BG_PANEL,
        )
        self._loading_label.pack(pady=T.PAD * 2)

    # ── Public API ────────────────────────────────────────────────────

    def set_locations(self, locations: List[VpnLocation]):
        """Populate the panel with the fetched location list."""
        self._all_locations = locations
        self._render_list(locations)

    def mark_connected(self, city: Optional[str]):
        """Highlight the row for the currently connected city."""
        if city == self._connected_city:
            return
        self._connected_city = city
        self._render_list(self._filtered_locations())

    # ── Search ────────────────────────────────────────────────────────

    def _set_search_placeholder(self):
        self._search_entry.insert(0, "Search")
        self._search_entry.configure(fg=T.TEXT_DISABLED)
        self._search_placeholder_active = True

    def _on_search_focus_in(self, _event):
        if self._search_placeholder_active:
            self._search_entry.delete(0, "end")
            self._search_entry.configure(fg=T.TEXT_PRIMARY)
            self._search_placeholder_active = False

    def _on_search_focus_out(self, _event):
        if not self._search_entry.get():
            self._set_search_placeholder()

    def _on_search_changed(self, *_):
        if self._search_placeholder_active:
            return
        self._render_list(self._filtered_locations())

    def _filtered_locations(self) -> List[VpnLocation]:
        query = self._search_var.get().strip().lower()
        if not query or self._search_placeholder_active:
            return self._all_locations
        return [
            loc for loc in self._all_locations
            if query in loc.country.lower() or query in loc.city.lower()
        ]

    # ── Rendering ────────────────────────────────────────────────────

    def _render_list(self, locations: List[VpnLocation]):
        # Clear existing widgets
        for child in self._list_frame.winfo_children():
            child.destroy()

        if not locations:
            tk.Label(
                self._list_frame, text="No locations found",
                font=T.FONT_BODY, fg=T.TEXT_SECONDARY, bg=T.BG_PANEL,
            ).pack(pady=T.PAD * 2)
            return

        # ── Fastest locations (top 5 sorted by ping) ─────────────────
        fastest = sorted(locations, key=lambda l: l.ping_estimate)[:5]
        _SectionHeader(self._list_frame, "Fastest locations").pack(fill="x")
        for loc in fastest:
            self._add_row(loc)

        # ── All locations (alphabetical) ─────────────────────────────
        all_sorted = sorted(locations, key=lambda l: (l.country, l.city))
        _SectionHeader(self._list_frame, "All locations").pack(fill="x")
        for loc in all_sorted:
            self._add_row(loc)

    def _add_row(self, location: VpnLocation):
        connected = (
            self._connected_city is not None
            and self._connected_city.lower() == location.city.lower()
        )
        row = _LocationRow(
            self._list_frame,
            location=location,
            on_select=self._on_row_clicked,
            is_connected=connected,
            on_mousewheel=self._on_mousewheel,
        )
        row.pack(fill="x")

    def _on_row_clicked(self, location: VpnLocation):
        self._on_location_selected(location.city)

    # ── Scroll canvas helpers ─────────────────────────────────────────

    def _on_list_frame_configure(self, _event):
        self._scroll_canvas.configure(
            scrollregion=self._scroll_canvas.bbox("all")
        )

    def _on_canvas_configure(self, event):
        self._scroll_canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-event.delta / 120)
        self._scroll_canvas.yview_scroll(delta, "units")
