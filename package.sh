#!/usr/bin/env bash
# Package AudioForge into a release ZIP for DeckyLoader
set -euo pipefail

cd "$(dirname "$0")"

PLUGIN_NAME=$(jq -r '.name' plugin.json)

rm -rf "out/${PLUGIN_NAME}" "out/${PLUGIN_NAME}.zip"
mkdir -p "out/${PLUGIN_NAME}/dist" \
         "out/${PLUGIN_NAME}/py_modules" \
         "out/${PLUGIN_NAME}/bin" \
         "out/${PLUGIN_NAME}/resources"

# Frontend bundle
cp dist/index.js "out/${PLUGIN_NAME}/dist/"
cp dist/index.js.map "out/${PLUGIN_NAME}/dist/"

# Plugin metadata
cp plugin.json "out/${PLUGIN_NAME}/"
cp package.json "out/${PLUGIN_NAME}/"
cp LICENSE "out/${PLUGIN_NAME}/"

# Backend
cp main.py "out/${PLUGIN_NAME}/"
cp py_modules/*.py "out/${PLUGIN_NAME}/py_modules/"

# Resources
cp defaults/resources/* "out/${PLUGIN_NAME}/resources/"

# Binaries
if ls bin/* 1>/dev/null 2>&1; then
  cp bin/* "out/${PLUGIN_NAME}/bin/"
fi

cd out
zip -r "${PLUGIN_NAME}.zip" "${PLUGIN_NAME}"
echo "Created out/${PLUGIN_NAME}.zip"
