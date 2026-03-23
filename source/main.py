"""
main.py — Entry point for the AdGuard VPN GUI application.

Run directly:
    python main.py

Build with PyInstaller (single file):
    pyinstaller --onefile --windowed --name adguard-vpn-gui main.py
"""

import tkinter as tk
from frontend import VpnApplicationWindow


def main():
    print("[main] Starting AdGuard VPN GUI application.")
    root = tk.Tk()
    application = VpnApplicationWindow(root)  # noqa: F841  (kept alive via root mainloop)
    root.mainloop()
    print("[main] Application closed.")


if __name__ == "__main__":
    main()
