#!/usr/bin/env bash
# AudioForge installer for Decky Loader on SteamOS
set -euo pipefail

PLUGIN_NAME="AudioForge"
PLUGINS_DIR="/home/deck/homebrew/plugins"
TEMP_ZIP="/tmp/${PLUGIN_NAME}.zip"
RELEASE_URL="https://github.com/neoseek/AudioForge/releases/latest/download/${PLUGIN_NAME}.zip"

echo "Installing ${PLUGIN_NAME}..."

echo "Downloading latest release..."
curl -L -o "$TEMP_ZIP" "$RELEASE_URL"

echo "Extracting to ${PLUGINS_DIR}..."
sudo unzip -o "$TEMP_ZIP" -d "$PLUGINS_DIR"

rm -f "$TEMP_ZIP"

echo "Restarting Decky Loader..."
sudo systemctl restart plugin_loader.service

echo "AudioForge installed successfully!"
