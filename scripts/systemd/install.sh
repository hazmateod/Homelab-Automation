#!/usr/bin/env bash

###############################################################################
# HIMP Systemd Installer
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SYSTEMD_DIR="$PROJECT_ROOT/systemd"

cd "$PROJECT_ROOT"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    echo "Run: sudo $0"
    exit 1
fi

echo
echo "========================================="
echo " HIMP Systemd Installer"
echo "========================================="
echo

if [[ ! -d "$SYSTEMD_DIR" ]]; then
    echo "ERROR: Systemd directory not found:"
    echo "  $SYSTEMD_DIR"
    exit 1
fi

UNITS=(
    himp-inventory-sync.service
    himp-inventory-sync.timer
    himp-scheduled-updates.service
    himp-scheduled-updates.timer
)

for unit in "${UNITS[@]}"; do
    if [[ ! -f "$SYSTEMD_DIR/$unit" ]]; then
        echo "ERROR: Missing systemd unit:"
        echo "  $SYSTEMD_DIR/$unit"
        exit 1
    fi
done

echo "Installing systemd units..."

for unit in "${UNITS[@]}"; do
    install -m 0644 \
        "$SYSTEMD_DIR/$unit" \
        "/etc/systemd/system/$unit"
done

echo
echo "Reloading systemd..."
systemctl daemon-reload

echo
echo "Enabling timers..."
systemctl enable \
    himp-inventory-sync.timer \
    himp-scheduled-updates.timer

echo
echo "Starting timers..."
systemctl start \
    himp-inventory-sync.timer \
    himp-scheduled-updates.timer

echo
echo "========================================="
echo " HIMP Systemd Installation Complete"
echo "========================================="
echo

systemctl status \
    himp-inventory-sync.timer \
    himp-scheduled-updates.timer \
    --no-pager

echo
echo "Scheduled timers:"
systemctl list-timers --all --no-pager |
    grep -E 'himp-(inventory-sync|scheduled-updates)\.timer' || true

echo
