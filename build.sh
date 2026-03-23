#!/usr/bin/env bash
set -e

ENTRY_POINT="source/main.py"
APP_NAME="adguardvpn-gui"
TARGET_DIR="builds"
BUILD_NAME="${APP_NAME}"
ICON_FILE="icon.png"
INSTALL_SCRIPT="install.sh"
UNINSTALL_SCRIPT="uninstall.sh"

# 1. Build binary
python3 -m PyInstaller \
  --onefile \
  --name "${APP_NAME}" \
  "${ENTRY_POINT}"

mkdir -p "${TARGET_DIR}"

# 2. Find unique name for archive
NEW_NAME="${BUILD_NAME}"
count=1
while [[ -e "${TARGET_DIR}/${NEW_NAME}.tar.gz" ]]; do
    NEW_NAME="${APP_NAME} (${count})"
    ((count++))
done

# 3. Prepare temp folder for archive contents
TEMP_DIR=$(mktemp -d)
cp "dist/${BUILD_NAME}" "$TEMP_DIR/${APP_NAME}"
cp "${ICON_FILE}"        "$TEMP_DIR/${ICON_FILE}"
cp "${INSTALL_SCRIPT}"   "$TEMP_DIR/${INSTALL_SCRIPT}"
cp "${UNINSTALL_SCRIPT}" "$TEMP_DIR/${UNINSTALL_SCRIPT}"
chmod +x "$TEMP_DIR/${APP_NAME}"
chmod +x "$TEMP_DIR/${INSTALL_SCRIPT}"
chmod +x "$TEMP_DIR/${UNINSTALL_SCRIPT}"

# 4. Pack into archive
tar -czf "${TARGET_DIR}/${NEW_NAME}.tar.gz" -C "$TEMP_DIR" .

# 5. Cleanup
rm -rf "$TEMP_DIR" build dist
rm -f "${APP_NAME}.spec"

echo "Archive created: ${TARGET_DIR}/${NEW_NAME}.tar.gz"
read -p "Press Enter to exit..."