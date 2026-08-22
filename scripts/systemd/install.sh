#!/usr/bin/env bash

###############################################################################
# HIMP Systemd Installer
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SYSTEMD_DIR="$PROJECT_ROOT/systemd"
SYSTEMD_TARGET_ROOT="${SYSTEMD_TARGET_ROOT:-/etc/systemd/system}"

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
    himp.service
    himp-inventory-sync.service
    himp-scheduled-updates.service
    himp-scheduler.service
    himp-scheduler.timer
)

for unit in "${UNITS[@]}"; do
    if [[ ! -f "$SYSTEMD_DIR/$unit" ]]; then
        echo "ERROR: Missing systemd unit:"
        echo "  $SYSTEMD_DIR/$unit"
        exit 1
    fi
done

SYSTEMD_CHANGED=false
TIMER_CHANGED=false

echo "Installing systemd units..."

for unit in "${UNITS[@]}"; do
    source="$SYSTEMD_DIR/$unit"
    target="$SYSTEMD_TARGET_ROOT/$unit"

    if [[ -f "$target" ]] && cmp -s "$source" "$target"; then
        echo "  unchanged: $unit"
        continue
    fi

    install -m 0644 "$source" "$target"
    echo "  updated:   $unit"
    SYSTEMD_CHANGED=true

    if [[ "$unit" == "himp-scheduler.timer" ]]; then
        TIMER_CHANGED=true
    fi
done

if [[ "$SYSTEMD_CHANGED" == "true" ]]; then
    echo
    echo "Reloading systemd..."
    systemctl daemon-reload
else
    echo
    echo "No systemd unit changes detected."
fi

echo
echo "Disabling legacy timers..."
systemctl disable --now \
    himp-inventory-sync.timer \
    himp-scheduled-updates.timer \
    2>/dev/null || true

echo
echo "Enabling scheduler timer..."
systemctl enable himp-scheduler.timer

echo
if [[ "${HIMP_START_SCHEDULER_TIMER:-0}" == "1" ]]; then
    if systemctl is-active --quiet himp-scheduler.timer; then
        echo "Scheduler timer is already active; leaving it running."
    else
        echo "Starting scheduler timer by explicit request..."
        systemctl start himp-scheduler.timer
    fi
else
    echo "Scheduler timer runtime state left unchanged."
    echo "To start it explicitly:"
    echo "  HIMP_START_SCHEDULER_TIMER=1 $0"
fi

echo
echo "========================================="
echo " HIMP Systemd Installation Complete"
echo "========================================="
echo

systemctl status \
    himp-scheduler.timer \
    --no-pager

echo
echo "Scheduled timers:"
systemctl list-timers --all --no-pager |
    grep -E 'himp-(scheduler|inventory-sync|scheduled-updates).timer' || true

echo
