#!/usr/bin/env bash

###############################################################################
# HIMP Application Deployment
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_ROOT="/opt/himp"
SYSTEMD_INSTALLER="$PROJECT_ROOT/scripts/systemd/install.sh"

cd "$PROJECT_ROOT"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    echo "Run: sudo $0"
    exit 1
fi

echo
echo "========================================="
echo " HIMP Application Deployment"
echo "========================================="
echo

if [[ ! -d "$DEPLOY_ROOT" ]]; then
    echo "ERROR: Deployment directory not found:"
    echo "  $DEPLOY_ROOT"
    exit 1
fi

if ! id himp >/dev/null 2>&1; then
    echo "ERROR: User 'himp' does not exist."
    exit 1
fi

DEPLOY_DIRS=(
    himp
    plugins
    playbooks
    inventory
    roles
    templates
    static
    config
)

DEPLOY_FILES=(
    ansible.cfg
    requirements.txt
    requirements-dev.txt
)

echo "Validating deployment source..."

for dir in "${DEPLOY_DIRS[@]}"; do
    if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
        echo "ERROR: Missing deployment directory:"
        echo "  $PROJECT_ROOT/$dir"
        exit 1
    fi
done

for file in "${DEPLOY_FILES[@]}"; do
    if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
        echo "ERROR: Missing deployment file:"
        echo "  $PROJECT_ROOT/$file"
        exit 1
    fi
done

echo
echo "Deploying application directories..."

for dir in "${DEPLOY_DIRS[@]}"; do
    cp -a         "$PROJECT_ROOT/$dir/."         "$DEPLOY_ROOT/$dir/"
done

echo
echo "Deploying application files..."

for file in "${DEPLOY_FILES[@]}"; do
    install -m 0644         "$PROJECT_ROOT/$file"         "$DEPLOY_ROOT/$file"
done

echo
echo "Setting application ownership..."

chown -R himp:himp     "$DEPLOY_ROOT/himp"     "$DEPLOY_ROOT/plugins"     "$DEPLOY_ROOT/playbooks"     "$DEPLOY_ROOT/inventory"     "$DEPLOY_ROOT/roles"     "$DEPLOY_ROOT/templates"     "$DEPLOY_ROOT/static"     "$DEPLOY_ROOT/config"

chown himp:himp     "$DEPLOY_ROOT/ansible.cfg"     "$DEPLOY_ROOT/requirements.txt"     "$DEPLOY_ROOT/requirements-dev.txt"

echo
echo "Installing Git-managed systemd units..."

"$SYSTEMD_INSTALLER"

echo
echo "Restarting HIMP..."

systemctl restart himp

echo
echo "Waiting for HIMP..."

for attempt in {1..10}; do
    if systemctl is-active --quiet himp; then
        break
    fi

    sleep 1
done

if ! systemctl is-active --quiet himp; then
    echo "ERROR: HIMP service failed to start."
    systemctl status himp --no-pager
    exit 1
fi

echo
echo "========================================="
echo " HIMP Deployment Complete"
echo "========================================="
echo

systemctl status himp --no-pager
