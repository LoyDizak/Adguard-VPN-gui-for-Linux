"""
ui_theme.py — Centralised design tokens for the AdGuard VPN dark UI.

To restyle the entire application, only this file needs editing.
"""

# ── Palette ────────────────────────────────────────────────────────────────

BG_BASE        = "#111214"   # deepest background (window fill)
BG_SURFACE     = "#18191d"   # card / panel surface
BG_PANEL       = "#1e2026"   # slightly lighter panel
BG_ITEM        = "#23252b"   # list item background
BG_ITEM_HOVER  = "#2a2d35"   # list item hover state
BG_ITEM_ACTIVE = "#1a3a2a"   # selected / connected location (green tint)

ACCENT_GREEN   = "#3ddc84"   # primary accent – connected, active tab
ACCENT_GREEN_D = "#2aa864"   # darker green for hover states
ACCENT_RED     = "#e05252"   # disconnect / error
ACCENT_RED_D   = "#b83e3e"   # darker red
ACCENT_ORANGE  = "#f0a04b"   # ping badge colour (fast)
ACCENT_BLUE    = "#4a9eff"   # neutral info

TEXT_PRIMARY   = "#e8eaed"   # main readable text
TEXT_SECONDARY = "#8a8f9a"   # subdued / labels
TEXT_DISABLED  = "#4a4f5a"   # ghost / placeholder

BORDER         = "#2c2f38"   # subtle dividers
SCROLLBAR_BG   = "#1e2026"
SCROLLBAR_FG   = "#3a3d48"

# ── Typography (Tkinter font tuples) ──────────────────────────────────────

FONT_TITLE     = ("Helvetica", 20, "bold")
FONT_HEADING   = ("Helvetica", 12, "bold")
FONT_BODY      = ("Helvetica", 10)
FONT_BODY_BOLD = ("Helvetica", 10, "bold")
FONT_SMALL     = ("Helvetica", 9)
FONT_MONO      = ("Courier",    9)

# ── Geometry ──────────────────────────────────────────────────────────────

WINDOW_MIN_W   = 820
WINDOW_MIN_H   = 520
PANEL_LEFT_W   = 320          # fixed pixel width of left (status) panel
CORNER_RADIUS  = 8            # used by Canvas-based widgets
PAD            = 16           # default outer padding
PAD_S          = 8            # small inner padding

# ── Polling ───────────────────────────────────────────────────────────────

STATUS_POLL_MS = 5000
LOCATION_HIGHLIGHT_REFRESH_MS = 60000
