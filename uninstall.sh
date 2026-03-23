#!/bin/bash

APP_DIR="$HOME/.local/share/adguardvpn-gui"
ICON_DIR="$HOME/.local/share/icons"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_DIR=$(xdg-user-dir DESKTOP)

echo "Uninstalling Adguard VPN GUI..."

rm -rf "$APP_DIR"
rm -f  "$ICON_DIR/adguardvpn.png"
rm -f  "$APPS_DIR/adguardvpn.desktop"
rm -f  "$DESKTOP_DIR/adguardvpn.desktop"

echo "Done! AdGuard VPN GUI has been removed."
echo "Note: AdGuard VPN CLI is still on your device."

read -p "Press Enter to exit..."