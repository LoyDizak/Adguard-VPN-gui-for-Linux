"""
ui_illustration.py — Decorative canvas illustration for the left panel.

Built entirely from primitive Tkinter Canvas shapes so it works without
external image files.  To replace the artwork, subclass IllustrationCanvas
and override draw().
"""

import math
import tkinter as tk
from ui_theme import (
    BG_SURFACE, ACCENT_GREEN, ACCENT_GREEN_D, BORDER, TEXT_SECONDARY
)


class IllustrationCanvas(tk.Canvas):
    """
    Base class for the decorative panel illustration.
    Override draw() to swap out the artwork.
    """

    def __init__(self, parent, width: int, height: int, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BG_SURFACE,
            highlightthickness=0,
            **kwargs,
        )
        self._canvas_width = width
        self._canvas_height = height
        self.bind("<Configure>", self._on_resize)
        self.after(10, self.draw)

    def _on_resize(self, event):
        self._canvas_width = event.width
        self._canvas_height = event.height
        self.delete("all")
        self.draw()

    def draw(self):
        """Override in subclasses to render custom artwork."""
        ShieldIllustration.render(self, self._canvas_width, self._canvas_height)


class ShieldIllustration:
    """
    Renders a stylised shield + concentric signal arcs — a classic VPN motif —
    using only Tkinter Canvas primitives.

    Layout (all values relative to canvas size for easy resizing):

        ┌──────────────────────────────┐
        │   · · background dots · ·   │
        │                              │
        │      ┌──────────────┐        │
        │      │  shield body │        │
        │      │   lock icon  │        │
        │      └──────────────┘        │
        │   )))  signal arcs  (((      │
        │                              │
        └──────────────────────────────┘
    """

    # Colour overrides — change here to restyle just the illustration
    SHIELD_FILL     = "#1e3a2a"
    SHIELD_OUTLINE  = ACCENT_GREEN
    LOCK_BODY       = ACCENT_GREEN
    LOCK_SHACKLE    = ACCENT_GREEN
    ARC_COLOR       = ACCENT_GREEN
    ARC_COLOR_DIM   = "#2a4a38"
    DOT_COLOR       = "#25293060"   # subtle background texture

    @classmethod
    def render(cls, canvas: tk.Canvas, w: int, h: int):
        cx = w / 2
        cy = h / 2 - h * 0.04   # slightly above centre

        cls._draw_bg_dots(canvas, w, h)
        cls._draw_signal_arcs(canvas, cx, cy, w, h)
        cls._draw_shield(canvas, cx, cy, w, h)

    # ── Background dot grid ───────────────────────────────────────────

    @classmethod
    def _draw_bg_dots(cls, canvas, w, h):
        spacing = 28
        r = 1.5
        for row in range(0, int(h / spacing) + 2):
            for col in range(0, int(w / spacing) + 2):
                x = col * spacing
                y = row * spacing
                canvas.create_oval(
                    x - r, y - r, x + r, y + r,
                    fill=BORDER, outline=""
                )

    # ── Concentric signal arcs ────────────────────────────────────────

    @classmethod
    def _draw_signal_arcs(cls, canvas, cx, cy, w, h):
        unit = min(w, h) * 0.06
        arc_y = cy + min(w, h) * 0.18   # arcs sit below the shield

        arc_configs = [
            (unit * 1.0, 3,   cls.ARC_COLOR_DIM),
            (unit * 1.9, 2,   cls.ARC_COLOR_DIM),
            (unit * 2.8, 1.5, cls.ARC_COLOR),
        ]
        for radius, width, color in arc_configs:
            canvas.create_arc(
                cx - radius, arc_y - radius,
                cx + radius, arc_y + radius,
                start=20, extent=140,
                style="arc",
                outline=color,
                width=width,
            )

    # ── Shield body + lock icon ───────────────────────────────────────

    @classmethod
    def _draw_shield(cls, canvas, cx, cy, w, h):
        unit = min(w, h) * 0.22
        top    = cy - unit * 1.0
        bottom = cy + unit * 1.1
        mid_y  = cy + unit * 0.25

        # Build shield polygon points
        # Classic shield: top-left, top-right, sides taper to a bottom point
        shield_pts = [
            cx - unit,        top,               # top-left
            cx + unit,        top,               # top-right
            cx + unit,        mid_y,             # right notch
            cx,               bottom,            # bottom tip
            cx - unit,        mid_y,             # left notch
        ]

        # Drop shadow (offset polygon)
        shadow = [p + (4 if i % 2 else 2) for i, p in enumerate(shield_pts)]
        canvas.create_polygon(shadow, fill="#0a1510", outline="", smooth=False)

        # Main shield body
        canvas.create_polygon(
            shield_pts,
            fill=cls.SHIELD_FILL,
            outline=cls.SHIELD_OUTLINE,
            width=2,
            smooth=False,
        )

        # Inner border highlight
        inset = unit * 0.12
        inner_pts = [
            cx - unit + inset,  top + inset,
            cx + unit - inset,  top + inset,
            cx + unit - inset,  mid_y - inset * 0.3,
            cx,                 bottom - inset * 1.8,
            cx - unit + inset,  mid_y - inset * 0.3,
        ]
        canvas.create_polygon(
            inner_pts,
            fill="",
            outline="#2a5a3a",
            width=1,
            smooth=False,
        )

        # Lock icon centred in shield
        lk_cx = cx
        lk_cy = cy - unit * 0.05
        lk_bw  = unit * 0.30   # body half-width
        lk_bh  = unit * 0.28   # body height
        lk_sr  = unit * 0.18   # shackle radius

        # Shackle (upper arc of the padlock)
        canvas.create_arc(
            lk_cx - lk_sr, lk_cy - lk_bh * 0.6 - lk_sr,
            lk_cx + lk_sr, lk_cy - lk_bh * 0.6 + lk_sr,
            start=0, extent=180,
            style="arc",
            outline=cls.LOCK_SHACKLE,
            width=max(2, int(unit * 0.07)),
        )

        # Lock body (rounded rectangle via rectangle + ovals)
        canvas.create_rectangle(
            lk_cx - lk_bw, lk_cy - lk_bh * 0.6,
            lk_cx + lk_bw, lk_cy + lk_bh * 0.8,
            fill=cls.LOCK_BODY,
            outline="",
        )

        # Keyhole circle
        kh_r = unit * 0.06
        canvas.create_oval(
            lk_cx - kh_r, lk_cy - kh_r,
            lk_cx + kh_r, lk_cy + kh_r,
            fill=cls.SHIELD_FILL,
            outline="",
        )
