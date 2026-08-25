#!/usr/bin/env bash

set -euo pipefail

SOURCE_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

HELPER_SOURCE="$SOURCE_ROOT/scripts/greenbone/himp_greenbone.py"
LAUNCHER_SOURCE="$SOURCE_ROOT/scripts/greenbone/himp-greenbone"
SUDOERS_SOURCE="$SOURCE_ROOT/config/greenbone/himp-greenbone.sudoers"

HELPER_TARGET="/opt/himp-greenbone/himp_greenbone.py"
LAUNCHER_TARGET="/usr/local/sbin/himp-greenbone"
SUDOERS_TARGET="/etc/sudoers.d/himp-greenbone"

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: installer must run as root"
    exit 1
fi

for file in \
    "$HELPER_SOURCE" \
    "$LAUNCHER_SOURCE" \
    "$SUDOERS_SOURCE"
do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: missing source file: $file"
        exit 1
    fi
done

if [[ ! -x /opt/himp-greenbone/venv/bin/python ]]; then
    echo "ERROR: Greenbone integration Python runtime is missing"
    exit 1
fi

echo "Validating Python helper..."
/opt/himp-greenbone/venv/bin/python \
    -m py_compile \
    "$HELPER_SOURCE"

echo "Validating sudoers source..."
visudo -cf "$SUDOERS_SOURCE"

echo "Installing Greenbone helper..."
install \
    -o root \
    -g root \
    -m 0755 \
    "$HELPER_SOURCE" \
    "$HELPER_TARGET"

echo "Installing Greenbone launcher..."
install \
    -o root \
    -g root \
    -m 0755 \
    "$LAUNCHER_SOURCE" \
    "$LAUNCHER_TARGET"

echo "Installing sudoers policy..."
install \
    -o root \
    -g root \
    -m 0440 \
    "$SUDOERS_SOURCE" \
    "$SUDOERS_TARGET"

visudo -cf "$SUDOERS_TARGET"

echo "Verifying installed files..."

cmp -s \
    "$HELPER_SOURCE" \
    "$HELPER_TARGET"

cmp -s \
    "$LAUNCHER_SOURCE" \
    "$LAUNCHER_TARGET"

cmp -s \
    "$SUDOERS_SOURCE" \
    "$SUDOERS_TARGET"

echo "GREENBONE_HELPER_INSTALL=PASS"
