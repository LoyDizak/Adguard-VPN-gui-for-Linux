"""
ui_status_panel.py — Left-side status panel (connection state + controls).

Contains:
  • Decorative illustration (IllustrationCanvas)
  • Connection status badge
  • Current location label
  • Connect / Disconnect button
  • Compact output log
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

import ui_theme as T
from ui_illustration import IllustrationCanvas
from backend import VpnStatus


class StatusPanel(tk.Frame):
    """
    Left panel: shows connection state and the primary action button.

    Callbacks
    ---------
    on_connect(city_name: Optional[str])   → called when user requests connect
    on_disconnect()                         → called when user requests disconnect
    """

    def __init__(
        self,
        parent,
        on_connect: Callable[[Optional[str]], None],
        on_disconnect: Callable[[], None],
        **kwargs,
    ):
        super().__init__(parent, bg=T.BG_SURFACE, **kwargs)
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._is_busy = False

        self._build()

    # ── Build ──────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1)

        # Illustration
        self._illustration = IllustrationCanvas(self, width=T.PANEL_LEFT_W, height=220)
        self._illustration.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        # Status badge row
        badge_frame = tk.Frame(self, bg=T.BG_SURFACE)
        badge_frame.grid(row=1, column=0, pady=(T.PAD, 4))

        self._dot = tk.Label(badge_frame, text="●", font=("Helvetica", 14),
                             fg=T.ACCENT_RED, bg=T.BG_SURFACE)
        self._dot.pack(side="left", padx=(0, 6))

        self._status_label = tk.Label(
            badge_frame, text="Disconnected",
            font=T.FONT_HEADING, fg=T.TEXT_PRIMARY, bg=T.BG_SURFACE,
        )
        self._status_label.pack(side="left")

        # Location sub-label
        self._location_label = tk.Label(
            self, text="", font=T.FONT_SMALL,
            fg=T.TEXT_SECONDARY, bg=T.BG_SURFACE,
        )
        self._location_label.grid(row=2, column=0, pady=(0, T.PAD))

        # Action button
        self._btn = tk.Button(
            self,
            text="Connect",
            font=T.FONT_BODY_BOLD,
            height=2,
            bg=T.ACCENT_GREEN,
            fg=T.BG_BASE,
            activebackground=T.ACCENT_GREEN_D,
            activeforeground=T.BG_BASE,
            relief="flat",
            cursor="hand2",
            bd=0,
            command=self._on_button_clicked,
        )
        self._btn.grid(row=3, column=0, padx=T.PAD, pady=(0, T.PAD), sticky="ew")

        # Separator
        sep = tk.Frame(self, bg=T.BORDER, height=1)
        sep.grid(row=4, column=0, sticky="ew", padx=T.PAD)

        # Output log label
        log_hdr = tk.Label(self, text="Output", font=T.FONT_SMALL,
                           fg=T.TEXT_SECONDARY, bg=T.BG_SURFACE)
        log_hdr.grid(row=5, column=0, sticky="w", padx=T.PAD, pady=(T.PAD_S, 2))

        # Log text widget
        log_frame = tk.Frame(self, bg=T.BG_SURFACE)
        log_frame.grid(row=6, column=0, sticky="nsew", padx=T.PAD, pady=(0, T.PAD))
        self.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(
            log_frame,
            height=5,
            font=T.FONT_MONO,
            state="disabled",
            wrap="word",
            bg=T.BG_BASE,
            fg="#7ec99a",
            insertbackground="white",
            relief="flat",
            bd=0,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical",
                                  command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._log.grid(row=0, column=0, sticky="nsew")

    # ── Public API ────────────────────────────────────────────────────

    def update_status(self, vpn_status: VpnStatus):
        """Refresh all status indicators from a VpnStatus object."""
        if vpn_status.is_connected:
            self._dot.configure(fg=T.ACCENT_GREEN)
            self._status_label.configure(text="Connected")
            loc = vpn_status.location_name or ""
            self._location_label.configure(text=loc)
            self._btn.configure(
                text="Disconnect",
                bg=T.ACCENT_RED,
                activebackground=T.ACCENT_RED_D,
            )
        else:
            self._dot.configure(fg=T.ACCENT_RED)
            self._status_label.configure(text="Disconnected")
            self._location_label.configure(text="")
            self._btn.configure(
                text="Connect",
                bg=T.ACCENT_GREEN,
                activebackground=T.ACCENT_GREEN_D,
            )

    def set_busy(self, busy: bool, label: str = ""):
        """Disable/enable controls during in-progress operations."""
        self._is_busy = busy
        if busy:
            self._btn.configure(text=label or "Please wait…",
                                state="disabled", bg=T.BG_ITEM)
        else:
            self._btn.configure(state="normal")

    def append_log(self, message: str):
        """Append a line to the output log."""
        self._log.configure(state="normal")
        self._log.insert("end", message.rstrip() + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Internal ─────────────────────────────────────────────────────

    def _on_button_clicked(self):
        if self._is_busy:
            return
        text = self._btn.cget("text")
        if text == "Disconnect":
            self._on_disconnect()
        else:
            self._on_connect(None)   # automatic — no city
