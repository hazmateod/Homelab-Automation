#!/usr/bin/env bash

###############################################################################
# HIMP Dedicated Automation Identity Installation
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

ACCOUNT="himp-automation"
ACCOUNT_HOME="/home/${ACCOUNT}"

HIMP_PUBLIC_KEY="/var/lib/himp/.ssh/id_ed25519.pub"

AUTHORIZED_KEYS="${ACCOUNT_HOME}/.ssh/authorized_keys"

SUDOERS_SOURCE="$PROJECT_ROOT/config/ssh/himp-automation.sudoers"
SUDOERS_TARGET="/etc/sudoers.d/himp-automation"

SOURCE_INVENTORY="$PROJECT_ROOT/inventory/hosts.yml"
RUNTIME_INVENTORY="/opt/himp/inventory/hosts.yml"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    exit 1
fi

for required in \
    "$HIMP_PUBLIC_KEY" \
    "$SUDOERS_SOURCE" \
    "$SOURCE_INVENTORY"
do
    if [[ ! -f "$required" ]]; then
        echo "ERROR: Missing required file:"
        echo "  $required"
        exit 1
    fi
done

echo
echo "========================================="
echo " HIMP Automation Identity Installation"
echo "========================================="
echo

echo "Ensuring dedicated automation account exists..."

if ! getent passwd "$ACCOUNT" >/dev/null; then
    useradd \
        --create-home \
        --home-dir "$ACCOUNT_HOME" \
        --shell /bin/bash \
        --comment "HIMP unattended automation" \
        "$ACCOUNT"
fi

passwd -l "$ACCOUNT" >/dev/null

echo
echo "Installing dedicated HIMP SSH authorization..."

install \
    -d \
    -o "$ACCOUNT" \
    -g "$ACCOUNT" \
    -m 0700 \
    "${ACCOUNT_HOME}/.ssh"

install \
    -o "$ACCOUNT" \
    -g "$ACCOUNT" \
    -m 0600 \
    "$HIMP_PUBLIC_KEY" \
    "$AUTHORIZED_KEYS"

echo
echo "Installing unattended Ansible sudo policy..."

install \
    -o root \
    -g root \
    -m 0440 \
    "$SUDOERS_SOURCE" \
    "$SUDOERS_TARGET"

visudo -cf "$SUDOERS_TARGET"

echo
echo "Validating source inventory..."

ansible-inventory \
    --inventory "$SOURCE_INVENTORY" \
    --host automation.server.arpa \
    >/dev/null

echo
echo "Installing explicitly approved runtime inventory..."

if [[ -f "$RUNTIME_INVENTORY" ]]; then
    cp -a \
        "$RUNTIME_INVENTORY" \
        "${RUNTIME_INVENTORY}.pre-himp-automation-identity"
fi

install \
    -o himp \
    -g himp \
    -m 0644 \
    "$SOURCE_INVENTORY" \
    "$RUNTIME_INVENTORY"

echo
echo "Validating runtime inventory..."

sudo -u himp \
    env \
    HOME=/var/lib/himp \
    PATH=/opt/himp/.venv/bin:/usr/local/bin:/usr/bin:/bin \
    ANSIBLE_PRIVATE_KEY_FILE=/var/lib/himp/.ssh/id_ed25519 \
    /usr/bin/ansible-inventory \
    --inventory "$RUNTIME_INVENTORY" \
    --host automation.server.arpa \
    >/dev/null

echo
echo "Verifying SSH key identity..."

diff -u \
    "$HIMP_PUBLIC_KEY" \
    "$AUTHORIZED_KEYS"

echo
echo "Verifying non-interactive sudo..."

sudo -u "$ACCOUNT" \
    sudo -n true

echo
echo "HIMP automation identity installation complete."
