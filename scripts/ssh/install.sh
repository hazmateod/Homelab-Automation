#!/usr/bin/env bash

###############################################################################
# HIMP SSH Hardening Installation
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

SSH_CONFIG_SOURCE="$PROJECT_ROOT/config/ssh/90-himp-hardening.conf"
SSH_CONFIG_DIRECTORY="/etc/ssh/sshd_config.d"
SSH_CONFIG_TARGET="$SSH_CONFIG_DIRECTORY/90-himp-hardening.conf"
SSH_CONFIG_BACKUP="${SSH_CONFIG_TARGET}.pre-himp-ssh-install"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    exit 1
fi

if [[ ! -f "$SSH_CONFIG_SOURCE" ]]; then
    echo "ERROR: Missing Git-managed SSH hardening configuration:"
    echo "  $SSH_CONFIG_SOURCE"
    exit 1
fi

if ! command -v sshd >/dev/null 2>&1; then
    echo "ERROR: sshd is not installed."
    exit 1
fi

echo
echo "========================================="
echo " HIMP SSH Hardening Installation"
echo "========================================="

install \
    -d \
    -o root \
    -g root \
    -m 0755 \
    "$SSH_CONFIG_DIRECTORY"

HAD_EXISTING_CONFIG=false

if [[ -f "$SSH_CONFIG_TARGET" ]]; then
    HAD_EXISTING_CONFIG=true
    cp -a "$SSH_CONFIG_TARGET" "$SSH_CONFIG_BACKUP"
fi

rollback() {
    echo
    echo "Rolling back SSH hardening configuration..."

    if [[ "$HAD_EXISTING_CONFIG" == "true" ]]; then
        cp -a "$SSH_CONFIG_BACKUP" "$SSH_CONFIG_TARGET"
    else
        rm -f "$SSH_CONFIG_TARGET"
    fi

    sshd -t || true
    systemctl reload ssh || true
}

fail_with_rollback() {
    echo "ERROR: $1"
    rollback
    exit 1
}

echo
echo "Installing Git-managed SSH hardening configuration..."

install \
    -o root \
    -g root \
    -m 0644 \
    "$SSH_CONFIG_SOURCE" \
    "$SSH_CONFIG_TARGET"

echo
echo "Validating complete SSH server configuration..."

if ! sshd -t; then
    fail_with_rollback "SSH configuration validation failed."
fi

echo
echo "Reloading SSH service..."

if ! systemctl reload ssh; then
    fail_with_rollback "SSH reload failed."
fi

echo
echo "Waiting for SSH service to return to active state..."

SSH_ACTIVE=false

for attempt in {1..10}; do
    if [[ "$(systemctl is-active ssh 2>/dev/null || true)" == "active" ]]; then
        SSH_ACTIVE=true
        break
    fi

    sleep 1
done

if [[ "$SSH_ACTIVE" != "true" ]]; then
    systemctl status ssh --no-pager -l || true
    fail_with_rollback "SSH service did not return to active state."
fi

echo
echo "Verifying Git / live configuration match..."

if ! diff -u "$SSH_CONFIG_SOURCE" "$SSH_CONFIG_TARGET"; then
    fail_with_rollback \
        "Live SSH configuration differs from Git-managed source."
fi

echo
echo "Verifying effective SSH security policy..."

EFFECTIVE_CONFIG="$(
    sshd -T -C \
        user=lou,host=automation,addr=192.168.37.60
)"

require_setting() {
    local expected="$1"

    if ! grep -Fxq "$expected" <<<"$EFFECTIVE_CONFIG"; then
        fail_with_rollback \
            "Expected SSH setting is not effective: $expected"
    fi
}

require_setting "permitrootlogin no"
require_setting "pubkeyauthentication yes"
require_setting "passwordauthentication no"
require_setting "kbdinteractiveauthentication no"
require_setting "x11forwarding no"
require_setting "gatewayports no"
require_setting "allowtcpforwarding no"
require_setting "permituserenvironment no"

if grep '^ciphers ' <<<"$EFFECTIVE_CONFIG" |
    grep -q 'chacha20-poly1305@openssh.com'; then

    fail_with_rollback \
        "ChaCha20-Poly1305 remains enabled."
fi

if grep '^macs ' <<<"$EFFECTIVE_CONFIG" |
    grep -q 'umac-64'; then

    fail_with_rollback \
        "A prohibited UMAC-64 algorithm remains enabled."
fi

echo
echo "SSH hardening installation complete."
