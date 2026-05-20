#!/usr/bin/env bash
set -euo pipefail

# Wardex installer for macOS.
# Installs the Python package, sets up the launchd agent, and starts the daemon.

PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DIR="${HOME}/.local/wardex"
CONFIG_DIR="${HOME}/.config/wardex"
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
PLIST_NAME="com.threatcraft.wardex.plist"

echo "==> Installing wardex"

# Verify Python
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Error: ${PYTHON_BIN} not found. Install Python 3.11+ first." >&2
    exit 1
fi

# Create venv and install
mkdir -p "${INSTALL_DIR}"
"${PYTHON_BIN}" -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install -e .

# Wire up CLI
mkdir -p "${HOME}/.local/bin"
ln -sf "${INSTALL_DIR}/venv/bin/wardex" "${HOME}/.local/bin/wardex"

# Config
mkdir -p "${CONFIG_DIR}"
if [[ ! -f "${CONFIG_DIR}/wardex.yaml" ]]; then
    cp config/wardex.yaml "${CONFIG_DIR}/wardex.yaml"
    echo "==> Wrote default config to ${CONFIG_DIR}/wardex.yaml"
fi

# launchd agent
mkdir -p "${LAUNCH_AGENT_DIR}"
sed "s|/usr/local/bin/wardex|${HOME}/.local/bin/wardex|g" \
    "${PLIST_NAME}" > "${LAUNCH_AGENT_DIR}/${PLIST_NAME}"

launchctl unload "${LAUNCH_AGENT_DIR}/${PLIST_NAME}" 2>/dev/null || true
launchctl load "${LAUNCH_AGENT_DIR}/${PLIST_NAME}"

echo "==> wardex installed and started"
echo "==> Edit ${CONFIG_DIR}/wardex.yaml to switch from alert mode to enforce mode"