#!/usr/bin/env bash

###############################################################################
# HIMP HTTPS / Caddy / Firewall Installation
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

CADDYFILE_SOURCE="$PROJECT_ROOT/caddy/Caddyfile"
CADDYFILE_TARGET="/etc/caddy/Caddyfile"

FIREWALL_SOURCE="$PROJECT_ROOT/config/firewall/nftables.conf"
FIREWALL_TARGET="/etc/nftables.conf"

TLS_DIRECTORY="/etc/himp/tls"

CERTIFICATE="$TLS_DIRECTORY/himp.crt"
PRIVATE_KEY="$TLS_DIRECTORY/himp.key"

MKCERT="/usr/local/bin/mkcert"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    exit 1
fi

for required_file in \
    "$CADDYFILE_SOURCE" \
    "$FIREWALL_SOURCE"; do

    if [[ ! -f "$required_file" ]]; then
        echo "ERROR: Missing Git-managed deployment file:"
        echo "  $required_file"
        exit 1
    fi
done

if [[ ! -x "$MKCERT" ]]; then
    echo "ERROR: mkcert not found:"
    echo "  $MKCERT"
    exit 1
fi

echo
echo "========================================="
echo " HIMP HTTPS Installation"
echo "========================================="
echo

echo "Installing Caddy package..."

if ! dpkg-query -W -f='${Status}' caddy 2>/dev/null |
    grep -q 'install ok installed'; then

    apt-get update
    apt-get install -y caddy
else
    echo "Caddy is already installed."
fi

if ! getent group caddy >/dev/null; then
    echo "ERROR: caddy group does not exist after installation."
    exit 1
fi

echo
echo "Creating protected TLS directory..."

install \
    -d \
    -o root \
    -g caddy \
    -m 0750 \
    "$TLS_DIRECTORY"

if [[ ! -f "$CERTIFICATE" || ! -f "$PRIVATE_KEY" ]]; then
    echo
    echo "Issuing HIMP internal certificate..."

    "$MKCERT" \
        -cert-file "$CERTIFICATE" \
        -key-file "$PRIVATE_KEY" \
        automation.server.arpa \
        automation \
        10.10.37.56

    chown root:caddy \
        "$CERTIFICATE" \
        "$PRIVATE_KEY"

    chmod 0644 "$CERTIFICATE"
    chmod 0640 "$PRIVATE_KEY"
else
    echo
    echo "Existing HIMP TLS certificate preserved."
fi

echo
echo "Validating Git-managed Caddy configuration..."

caddy validate \
    --config "$CADDYFILE_SOURCE" \
    --adapter caddyfile

echo
echo "Validating Git-managed firewall configuration..."

nft -c -f "$FIREWALL_SOURCE"

echo
echo "Installing Git-managed Caddy configuration..."

install \
    -o root \
    -g root \
    -m 0644 \
    "$CADDYFILE_SOURCE" \
    "$CADDYFILE_TARGET"

echo
echo "Installing Git-managed firewall configuration..."

if [[ -f "$FIREWALL_TARGET" ]]; then
    cp -a \
        "$FIREWALL_TARGET" \
        "${FIREWALL_TARGET}.pre-himp-tls-install"
fi

install \
    -o root \
    -g root \
    -m 0644 \
    "$FIREWALL_SOURCE" \
    "$FIREWALL_TARGET"

echo
echo "Applying firewall configuration..."

nft -f "$FIREWALL_TARGET"

echo
echo "Enabling and reloading Caddy..."

systemctl enable caddy
systemctl reload-or-restart caddy

echo
echo "Waiting for HTTPS listener..."

for attempt in {1..15}; do
    if ss -lnt |
        grep -qE 'LISTEN.+:443[[:space:]]'; then
        break
    fi

    sleep 1
done

if ! systemctl is-active --quiet caddy; then
    echo "ERROR: Caddy is not active."
    systemctl status caddy --no-pager -l || true
    exit 1
fi

if ! ss -lnt |
    grep -qE 'LISTEN.+:443[[:space:]]'; then
    echo "ERROR: HTTPS listener did not appear on TCP 443."
    ss -lntp
    exit 1
fi

echo
echo "HTTPS and firewall installation complete."
