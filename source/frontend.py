import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional

from backend import AdGuardVpnBackend, VpnLocation, VpnStatus


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTOMATIC_LOCATION_LABEL = "⚡ Automatic (fastest)"
POLL_INTERVAL_MS = 5000          # How often to refresh status in the background
WINDOW_TITLE = "AdGuard VPN"
WINDOW_MIN_WIDTH = 480
WINDOW_MIN_HEIGHT = 340

COLOR_CONNECTED = "#2ecc71"      # Green
COLOR_DISCONNECTED = "#e74c3c"   # Red
COLOR_NEUTRAL = "#7f8c8d"        # Grey


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class VpnApplicationWindow:
    """
    Root Tkinter window for the AdGuard VPN GUI.

    All CLI calls are dispatched to background threads to keep the
    UI responsive.  Results are posted back to the main thread via
    tk.after() callbacks.
    """

    def __init__(self, root: tk.Tk):
        print("[frontend] Initialising VPN application window.")
        self.root = root
        self.backend = AdGuardVpnBackend()

        self._available_locations: list[VpnLocation] = []
        self._is_operation_in_progress = False

        self._setup_window()
        self._build_widgets()
        self._load_locations_in_background()
        self._refresh_status_in_background()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.root.title(WINDOW_TITLE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.resizable(True, True)
        self.root.configure(padx=16, pady=16)
        # Try to set a small icon if one is bundled
        try:
            self.root.iconbitmap("adguard_vpn.ico")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widgets(self):
        # ── Title ──────────────────────────────────────────────────────
        title_label = tk.Label(
            self.root,
            text="AdGuard VPN",
            font=("Helvetica", 18, "bold"),
        )
        title_label.pack(pady=(0, 12))

        # ── Status area ────────────────────────────────────────────────
        status_frame = tk.Frame(self.root, relief="groove", borderwidth=1)
        status_frame.pack(fill="x", pady=(0, 12))

        tk.Label(status_frame, text="Status:", font=("Helvetica", 10)).pack(
            side="left", padx=8, pady=6
        )

        self.status_indicator_label = tk.Label(
            status_frame,
            text="Checking…",
            font=("Helvetica", 10, "bold"),
            fg=COLOR_NEUTRAL,
            width=30,
            anchor="w",
        )
        self.status_indicator_label.pack(side="left", padx=4, pady=6)

        # ── Location selector ──────────────────────────────────────────
        location_frame = tk.Frame(self.root)
        location_frame.pack(fill="x", pady=(0, 12))

        tk.Label(location_frame, text="Location:", font=("Helvetica", 10)).pack(
            side="left"
        )

        self.selected_location_var = tk.StringVar(value=AUTOMATIC_LOCATION_LABEL)

        self.location_combobox = ttk.Combobox(
            location_frame,
            textvariable=self.selected_location_var,
            state="readonly",
            width=42,
            font=("Helvetica", 10),
        )
        self.location_combobox["values"] = [AUTOMATIC_LOCATION_LABEL]
        self.location_combobox.pack(side="left", padx=(8, 0))

        # ── Connect / Disconnect button ────────────────────────────────
        self.connect_button = tk.Button(
            self.root,
            text="Connect",
            font=("Helvetica", 12, "bold"),
            width=20,
            height=2,
            bg="#3498db",
            fg="white",
            activebackground="#2980b9",
            cursor="hand2",
            command=self._on_connect_button_clicked,
        )
        self.connect_button.pack(pady=(0, 12))

        # ── Log / output area ─────────────────────────────────────────
        log_label = tk.Label(self.root, text="Output:", font=("Helvetica", 9))
        log_label.pack(anchor="w")

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill="both", expand=True)

        self.log_text_widget = tk.Text(
            log_frame,
            height=8,
            font=("Courier", 9),
            state="disabled",
            wrap="word",
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
        )
        log_scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text_widget.yview
        )
        self.log_text_widget.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text_widget.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------------
    # Status display helpers
    # ------------------------------------------------------------------

    def _update_status_display(self, vpn_status: VpnStatus):
        """Refresh the status label and button text from a VpnStatus object."""
        print(f"[frontend] Updating status display: connected={vpn_status.is_connected}")
        if vpn_status.is_connected:
            status_text = "● Connected"
            if vpn_status.location_name:
                status_text += f"  —  {vpn_status.location_name}"
            self.status_indicator_label.configure(
                text=status_text, fg=COLOR_CONNECTED
            )
            self.connect_button.configure(
                text="Disconnect",
                bg="#e74c3c",
                activebackground="#c0392b",
            )
        else:
            self.status_indicator_label.configure(
                text="● Disconnected", fg=COLOR_DISCONNECTED
            )
            self.connect_button.configure(
                text="Connect",
                bg="#3498db",
                activebackground="#2980b9",
            )

    def _append_log_message(self, message: str):
        """Append a line of text to the output log widget."""
        self.log_text_widget.configure(state="normal")
        self.log_text_widget.insert("end", message.rstrip() + "\n")
        self.log_text_widget.see("end")
        self.log_text_widget.configure(state="disabled")

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable interactive controls during operations."""
        new_state = "normal" if enabled else "disabled"
        combobox_state = "readonly" if enabled else "disabled"
        self.connect_button.configure(state=new_state)
        self.location_combobox.configure(state=combobox_state)
        self._is_operation_in_progress = not enabled

    # ------------------------------------------------------------------
    # Background task: load locations
    # ------------------------------------------------------------------

    def _load_locations_in_background(self):
        """Fetch the location list in a background thread."""
        print("[frontend] Spawning thread to load locations.")
        thread = threading.Thread(
            target=self._background_load_locations, daemon=True
        )
        thread.start()

    def _background_load_locations(self):
        success, locations = self.backend.list_locations()
        self.root.after(0, self._on_locations_loaded, success, locations)

    def _on_locations_loaded(self, success: bool, locations: list):
        if not success or not locations:
            print("[frontend] Could not load locations.")
            self._append_log_message(
                "⚠  Could not load location list. Is adguardvpn-cli installed?"
            )
            return

        self._available_locations = locations
        display_labels = [AUTOMATIC_LOCATION_LABEL] + [
            location.display_label() for location in locations
        ]
        self.location_combobox["values"] = display_labels
        self.location_combobox.current(0)
        print(f"[frontend] Location dropdown populated with {len(locations)} entries.")

    # ------------------------------------------------------------------
    # Background task: refresh status
    # ------------------------------------------------------------------

    def _refresh_status_in_background(self):
        """Fetch VPN status in a background thread (non-blocking)."""
        thread = threading.Thread(
            target=self._background_fetch_status, daemon=True
        )
        thread.start()

    def _background_fetch_status(self):
        vpn_status = self.backend.get_status()
        self.root.after(0, self._on_status_fetched, vpn_status)

    def _on_status_fetched(self, vpn_status: VpnStatus):
        self._update_status_display(vpn_status)
        # Schedule the next periodic poll
        self.root.after(POLL_INTERVAL_MS, self._refresh_status_in_background)

    # ------------------------------------------------------------------
    # Button click handler
    # ------------------------------------------------------------------

    def _on_connect_button_clicked(self):
        if self._is_operation_in_progress:
            print("[frontend] Operation already in progress — ignoring click.")
            return

        # Decide whether to connect or disconnect based on current label
        current_button_text = self.connect_button.cget("text")
        if current_button_text == "Disconnect":
            self._initiate_disconnect()
        else:
            self._initiate_connect()

    # ------------------------------------------------------------------
    # Connect flow
    # ------------------------------------------------------------------

    def _initiate_connect(self):
        selected_label = self.selected_location_var.get()
        target_city_name = self._resolve_city_name_from_label(selected_label)

        if target_city_name:
            print(f"[frontend] User requested connect to: {target_city_name!r}")
            self._append_log_message(f"Connecting to {target_city_name}…")
        else:
            print("[frontend] User requested automatic connect.")
            self._append_log_message("Connecting to fastest location…")

        self._set_controls_enabled(False)
        self.connect_button.configure(text="Connecting…", state="disabled")
        self.status_indicator_label.configure(
            text="● Connecting…", fg=COLOR_NEUTRAL
        )

        thread = threading.Thread(
            target=self._background_connect,
            args=(target_city_name,),
            daemon=True,
        )
        thread.start()

    def _background_connect(self, city_name: Optional[str]):
        success, output = self.backend.connect(city_name)
        self.root.after(0, self._on_connect_finished, success, output)

    def _on_connect_finished(self, success: bool, output: str):
        self._set_controls_enabled(True)
        self._append_log_message(output)

        if success:
            print("[frontend] Connect succeeded.")
        else:
            print(f"[frontend] Connect failed: {output[:200]}")
            messagebox.showerror(
                "Connection failed",
                f"Could not connect to VPN.\n\n{output[:400]}",
            )
        # Refresh status regardless of outcome
        self._refresh_status_in_background()

    # ------------------------------------------------------------------
    # Disconnect flow
    # ------------------------------------------------------------------

    def _initiate_disconnect(self):
        print("[frontend] User requested disconnect.")
        self._append_log_message("Disconnecting…")
        self._set_controls_enabled(False)
        self.connect_button.configure(text="Disconnecting…", state="disabled")

        thread = threading.Thread(
            target=self._background_disconnect, daemon=True
        )
        thread.start()

    def _background_disconnect(self):
        success, output = self.backend.disconnect()
        self.root.after(0, self._on_disconnect_finished, success, output)

    def _on_disconnect_finished(self, success: bool, output: str):
        self._set_controls_enabled(True)
        self._append_log_message(output)

        if not success:
            print(f"[frontend] Disconnect reported failure: {output[:200]}")
            # Not showing a modal here — "VPN stopped" can come via stderr
            # and still be a success in practice.
        else:
            print("[frontend] Disconnect succeeded.")

        self._refresh_status_in_background()

    # ------------------------------------------------------------------
    # Helper: map dropdown label → city name for CLI
    # ------------------------------------------------------------------

    def _resolve_city_name_from_label(self, display_label: str) -> Optional[str]:
        """
        Given the text currently shown in the dropdown, return the city
        name to pass to `adguardvpn-cli connect -l`, or None for automatic.
        """
        if display_label == AUTOMATIC_LOCATION_LABEL:
            return None

        for location in self._available_locations:
            if location.display_label() == display_label:
                return location.connect_argument()

        print(f"[frontend] WARNING: Could not match label to location: {display_label!r}")
        return None
