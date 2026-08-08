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

for unit in \
    himp-inventory-sync.service \
    himp-inventory-sync.timer
do
    if [[ ! -f "$SYSTEMD_DIR/$unit" ]]; then
        echo "ERROR: Missing systemd unit:"
        echo "  $SYSTEMD_DIR/$unit"
        exit 1
    fi
done

echo "Installing systemd units..."

install -m 0644 \
    "$SYSTEMD_DIR/himp-inventory-sync.service" \
    /etc/systemd/system/himp-inventory-sync.service

install -m 0644 \
    "$SYSTEMD_DIR/himp-inventory-sync.timer" \
    /etc/systemd/system/himp-inventory-sync.timer

echo
echo "Reloading systemd..."
systemctl daemon-reload

echo
echo "Enabling inventory synchronization timer..."
systemctl enable himp-inventory-sync.timer

echo
echo "Starting inventory synchronization timer..."
systemctl start himp-inventory-sync.timer

echo
echo "========================================="
echo " HIMP Systemd Installation Complete"
echo "========================================="
echo

systemctl status \
    himp-inventory-sync.timer \
    --no-pager

echo
echo "Scheduled timers:"
systemctl list-timers --all --no-pager |
    grep -E '^.*himp-inventory-sync\.timer' || true

echo
