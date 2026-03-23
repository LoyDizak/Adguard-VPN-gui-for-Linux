#!/bin/bash

APP_NAME="Adguard VPN"
APP_DIR="$HOME/.local/share/adguardvpn-gui"
ICON_DIR="$HOME/.local/share/icons"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_DIR=$(xdg-user-dir DESKTOP)
DESKTOP_FILE="$APPS_DIR/adguardvpn.desktop"

# 1. Ask about CLI
echo "AdGuard VPN CLI is required for this application to work. Do you want to install it? [y/n]"
read -r answer

CLI_INSTALLED=false

if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Installing AdGuard VPN CLI..."
    curl -fsSL https://raw.githubusercontent.com/AdguardTeam/AdGuardVPNCLI/master/scripts/release/install.sh | sh -s -- -v
    rm -f adguardvpn-cli-*.tar.gz
    CLI_INSTALLED=true
fi

echo "Installing GUI..."

# 2. Create directories
mkdir -p "$APP_DIR" "$ICON_DIR" "$APPS_DIR"

# 3. Copy files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/adguardvpn-gui" "$APP_DIR/adguardvpn-gui"
chmod +x "$APP_DIR/adguardvpn-gui"
cp "$SCRIPT_DIR/icon.png" "$ICON_DIR/adguardvpn.png"

# 4. Create .desktop file
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Exec="$APP_DIR/adguardvpn-gui"
Icon=adguardvpn.png
Terminal=false
Categories=Network;
EOF

# 5. Copy to desktop
cp "$DESKTOP_FILE" "$DESKTOP_DIR/"
chmod +x "$DESKTOP_DIR/adguardvpn.desktop"

echo "Done!"

# 6. Offer to log in only if CLI was installed
if [ "$CLI_INSTALLED" = true ]; then
    echo "Do you want to log in to your account? (you can do this later with: adguardvpn-cli login) [y/n]"
    read -r login_answer
    if [[ "$login_answer" =~ ^[Yy]$ ]]; then
        adguardvpn-cli login 
    fi
fi

read -p "Press Enter to close..."