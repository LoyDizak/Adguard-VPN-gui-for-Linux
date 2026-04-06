"""
frontend.py — Main application window for AdGuard VPN GUI.

Coordinates:
  • StatusPanel   (left)  — connection state, action button, log
  • LocationPanel (right) — scrollable location list with search

All backend calls run in daemon threads; results are posted back to
the main thread via root.after() to keep the UI responsive.
"""

import threading
import time
import tkinter as tk
from typing import Optional

import ui_theme as T
from ui_status_panel   import StatusPanel
from ui_location_panel import LocationPanel
from backend import AdGuardVpnBackend, VpnStatus


class VpnApplicationWindow:
    """Root application window."""

    def __init__(self, root: tk.Tk):
        print("[frontend] Initialising application window.")
        self.root    = root
        self.backend = AdGuardVpnBackend()
        self._current_connected_city: Optional[str] = None
        self._last_location_highlight_update = 0.0

        self._setup_window()
        self._build_layout()
        self._load_locations()
        self._poll_status()

    # ── Window setup ──────────────────────────────────────────────────

    def _setup_window(self):
        self.root.title("AdGuard VPN")
        self.root.minsize(T.WINDOW_MIN_W, T.WINDOW_MIN_H)
        self.root.configure(bg=T.BG_BASE)
        self.root.resizable(True, True)

        try:
            import os
            icon_path = os.path.expanduser("~/.local/share/icons/adguardvpn.png")
            self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception:
            pass

    # ── Layout ────────────────────────────────────────────────────────

    def _build_layout(self):
        # App title bar
        header = tk.Frame(self.root, bg=T.BG_BASE, pady=T.PAD_S)
        header.pack(fill="x", padx=T.PAD)

        tk.Label(
            header,
            text="AdGuard VPN",
            font=T.FONT_TITLE,
            fg=T.TEXT_PRIMARY,
            bg=T.BG_BASE,
        ).pack(side="left")

        # Version / info label (right side of header)
        tk.Label(
            header,
            text="Vibecoded GUI for linux",
            font=T.FONT_SMALL,
            fg=T.TEXT_SECONDARY,
            bg=T.BG_BASE,
        ).pack(side="right", padx=T.PAD)

        # Thin separator under header
        tk.Frame(self.root, bg=T.BORDER, height=1).pack(fill="x")

        # ── Two-panel body using grid for flexible layout ─────────────────
        self._body = tk.Frame(self.root, bg=T.BG_BASE)
        self._body.pack(fill="both", expand=True)
        self._body.rowconfigure(0, weight=1)
        self._body.columnconfigure(0, weight=3)  # left column: larger weight (shrinks first)
        self._body.columnconfigure(1, weight=0)  # divider: fixed size
        self._body.columnconfigure(2, weight=1)  # right column: smaller weight (shrinks last)

        # Left (status) panel — resizable with minimum width
        self._status_panel = StatusPanel(
            self._body,
            on_connect=self._request_connect,
            on_disconnect=self._request_disconnect,
            width=T.PANEL_LEFT_W,
        )
        self._status_panel.grid(
            row=0, column=0, sticky="nsew",
            padx=(T.PAD, 0), pady=T.PAD
        )

        # Vertical divider
        tk.Frame(self._body, bg=T.BORDER, width=1).grid(
            row=0, column=1, sticky="ns",
            padx=(T.PAD, 0), pady=T.PAD
        )

        # Right (location) panel — resizable with minimum width
        self._location_panel = LocationPanel(
            self._body,
            on_location_selected=self._request_connect,
        )
        self._location_panel.grid(
            row=0, column=2, sticky="nsew",
            padx=(0, T.PAD), pady=T.PAD
        )

        # Bind window resize to enforce minimum column widths
        self.root.bind("<Configure>", self._on_window_resize)
        self._apply_column_widths()


    # ── Load locations ────────────────────────────────────────────────

    def _load_locations(self):
        threading.Thread(target=self._bg_load_locations, daemon=True).start()

    def _bg_load_locations(self):
        success, locations = self.backend.list_locations()
        self.root.after(0, self._on_locations_loaded, success, locations)

    def _on_locations_loaded(self, success: bool, locations: list):
        if not success or not locations:
            self._status_panel.append_log(
                "⚠  Could not load locations. Is adguardvpn-cli installed?"
            )
            return
        print(f"[frontend] Loaded {len(locations)} locations.")
        self._location_panel.set_locations(locations)

    # ── Status polling ────────────────────────────────────────────────

    def _poll_status(self):
        threading.Thread(target=self._bg_fetch_status, daemon=True).start()

    def _bg_fetch_status(self):
        status = self.backend.get_status()
        self.root.after(0, self._on_status_fetched, status)

    def _on_status_fetched(self, status: VpnStatus):
        self._status_panel.update_status(status)

        connected_city = status.location_name if status.is_connected else None
        now = time.monotonic()

        if connected_city != self._current_connected_city:
            self._location_panel.mark_connected(connected_city)
            self._current_connected_city = connected_city
            self._last_location_highlight_update = now
        elif now - self._last_location_highlight_update >= (
            T.LOCATION_HIGHLIGHT_REFRESH_MS / 1000
        ):
            self._location_panel.mark_connected(connected_city)
            self._last_location_highlight_update = now

        self.root.after(T.STATUS_POLL_MS, self._poll_status)

    # ── Connect ───────────────────────────────────────────────────────

    def _request_connect(self, city_name: Optional[str]):
        label = f"Connecting to {city_name}…" if city_name else "Connecting…"
        self._status_panel.append_log(label)
        self._status_panel.set_busy(True, "Connecting…")

        threading.Thread(
            target=self._bg_connect,
            args=(city_name,),
            daemon=True,
        ).start()

    def _bg_connect(self, city_name: Optional[str]):
        success, output = self.backend.connect(city_name)
        self.root.after(0, self._on_connect_done, success, output)

    def _on_connect_done(self, success: bool, output: str):
        self._status_panel.set_busy(False)
        self._status_panel.append_log(output)
        if not success:
            print(f"[frontend] Connect failed: {output[:200]}")
            tk.messagebox.showerror(
                "Connection failed",
                f"Could not connect to VPN.\n\n{output[:400]}",
            )
        self._poll_status()

    # ── Disconnect ────────────────────────────────────────────────────

    def _request_disconnect(self):
        self._status_panel.append_log("Disconnecting…")
        self._status_panel.set_busy(True, "Disconnecting…")

        threading.Thread(target=self._bg_disconnect, daemon=True).start()

    def _bg_disconnect(self):
        success, output = self.backend.disconnect()
        self.root.after(0, self._on_disconnect_done, success, output)

    def _on_disconnect_done(self, success: bool, output: str):
        self._status_panel.set_busy(False)
        self._status_panel.append_log(output)
        self._poll_status()
