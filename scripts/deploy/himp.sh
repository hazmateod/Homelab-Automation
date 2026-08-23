#!/usr/bin/env bash

###############################################################################
# HIMP Application Deployment
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/himp}"
SYSTEMD_TARGET_ROOT="${SYSTEMD_TARGET_ROOT:-/etc/systemd/system}"
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
    roles
    templates
    static
    config
)

SOURCE_INVENTORY="$PROJECT_ROOT/inventory/hosts.yml"
RUNTIME_INVENTORY="$DEPLOY_ROOT/inventory/hosts.yml"

DEPLOY_FILES=(
    ansible.cfg
    requirements.txt
    requirements-dev.txt
)

echo "Validating deployment source..."

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: Deployment source is not a Git working tree."
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: Deployment source contains uncommitted changes."
    echo
    git status --short
    echo
    echo "Commit or discard all changes before deploying HIMP."
    exit 1
fi

SOURCE_REVISION="$(git rev-parse HEAD)"
RELEASE_MARKER="$DEPLOY_ROOT/.himp-release"
REQUIREMENTS_MARKER="$DEPLOY_ROOT/.requirements.sha256"

echo "Source revision: $SOURCE_REVISION"

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

if [[ ! -f "$SOURCE_INVENTORY" ]]; then
    echo "ERROR: Missing source inventory:"
    echo "  $SOURCE_INVENTORY"
    exit 1
fi

INVENTORY_SEEDED=false

if [[ ! -f "$RUNTIME_INVENTORY" ]]; then
    echo
    echo "Seeding persistent runtime inventory..."

    mkdir -p "$DEPLOY_ROOT/inventory"

    cp -a         "$PROJECT_ROOT/inventory/."         "$DEPLOY_ROOT/inventory/"

    INVENTORY_SEEDED=true

    echo "Runtime inventory seeded from Git baseline."
else
    echo
    echo "Preserving persistent runtime inventory."
fi

echo
echo "Checking deployment changes..."

APPLICATION_CHANGED=false

if [[ "$INVENTORY_SEEDED" == "true" ]]; then
    APPLICATION_CHANGED=true
fi

for dir in "${DEPLOY_DIRS[@]}"; do
    source="$PROJECT_ROOT/$dir"
    target="$DEPLOY_ROOT/$dir"

    if [[ ! -d "$target" ]] || \
       ! diff -qr \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           "$source" \
           "$target" >/dev/null; then
        APPLICATION_CHANGED=true
        break
    fi
done

if [[ "$APPLICATION_CHANGED" == "false" ]]; then
    for file in "${DEPLOY_FILES[@]}"; do
        source="$PROJECT_ROOT/$file"
        target="$DEPLOY_ROOT/$file"

        if [[ ! -f "$target" ]] || \
           ! cmp -s "$source" "$target"; then
            APPLICATION_CHANGED=true
            break
        fi
    done
fi

HIMP_SERVICE_CHANGED=false

if [[ ! -f "$SYSTEMD_TARGET_ROOT/himp.service" ]] || \
   ! cmp -s \
       "$PROJECT_ROOT/systemd/himp.service" \
       "$SYSTEMD_TARGET_ROOT/himp.service"; then
    HIMP_SERVICE_CHANGED=true
fi

SOURCE_REQUIREMENTS_HASH="$(
    sha256sum "$PROJECT_ROOT/requirements.txt" |
    awk '{print $1}'
)"

INSTALLED_REQUIREMENTS_HASH=""

if [[ -f "$REQUIREMENTS_MARKER" ]]; then
    INSTALLED_REQUIREMENTS_HASH="$(
        tr -d '[:space:]' < "$REQUIREMENTS_MARKER"
    )"
fi

REQUIREMENTS_CHANGED=false

if [[ "$SOURCE_REQUIREMENTS_HASH" != \
      "$INSTALLED_REQUIREMENTS_HASH" ]]; then
    REQUIREMENTS_CHANGED=true
fi

echo "  Application changed: $APPLICATION_CHANGED"
echo "  HIMP service changed: $HIMP_SERVICE_CHANGED"
echo "  Requirements changed: $REQUIREMENTS_CHANGED"

echo
echo "Deploying application directories..."

for dir in "${DEPLOY_DIRS[@]}"; do
    cp -a \
        "$PROJECT_ROOT/$dir/." \
        "$DEPLOY_ROOT/$dir/"
done

echo
echo "Deploying application files..."

for file in "${DEPLOY_FILES[@]}"; do
    install -m 0644 \
        "$PROJECT_ROOT/$file" \
        "$DEPLOY_ROOT/$file"
done

echo
echo "Setting application ownership..."

chown -R himp:himp \
    "$DEPLOY_ROOT/himp" \
    "$DEPLOY_ROOT/plugins" \
    "$DEPLOY_ROOT/playbooks" \
    "$DEPLOY_ROOT/inventory" \
    "$DEPLOY_ROOT/roles" \
    "$DEPLOY_ROOT/templates" \
    "$DEPLOY_ROOT/static" \
    "$DEPLOY_ROOT/config"

chown himp:himp \
    "$DEPLOY_ROOT/ansible.cfg" \
    "$DEPLOY_ROOT/requirements.txt" \
    "$DEPLOY_ROOT/requirements-dev.txt"

if [[ "$REQUIREMENTS_CHANGED" == "true" ]]; then
    echo
    echo "Synchronizing HIMP runtime dependencies..."

    if [[ ! -x "$DEPLOY_ROOT/.venv/bin/python" ]]; then
        echo "ERROR: HIMP runtime Python not found:"
        echo "  $DEPLOY_ROOT/.venv/bin/python"
        exit 1
    fi

    "$DEPLOY_ROOT/.venv/bin/python" \
        -m pip install \
        -r "$DEPLOY_ROOT/requirements.txt"

    printf '%s\n' \
        "$SOURCE_REQUIREMENTS_HASH" \
        > "$REQUIREMENTS_MARKER"

    chown himp:himp \
        "$REQUIREMENTS_MARKER"

    chmod 0644 \
        "$REQUIREMENTS_MARKER"

    echo "Runtime dependencies synchronized."
else
    echo
    echo "Runtime dependencies already synchronized."
fi

echo
echo "Installing Git-managed systemd units..."

"$SYSTEMD_INSTALLER"

if [[ "$APPLICATION_CHANGED" == "true" ]] || \
   [[ "$HIMP_SERVICE_CHANGED" == "true" ]]; then
    echo
    echo "Restarting HIMP..."
    systemctl restart himp
else
    echo
    echo "No HIMP changes detected; restart not required."
fi

echo
echo "Waiting for HIMP service..."

HIMP_READINESS_URL="${HIMP_READINESS_URL:-http://127.0.0.1:9347/}"
HIMP_READINESS_ATTEMPTS="${HIMP_READINESS_ATTEMPTS:-15}"
HIMP_READINESS_SLEEP_SECONDS="${HIMP_READINESS_SLEEP_SECONDS:-1}"

for ((attempt = 1; attempt <= HIMP_READINESS_ATTEMPTS; attempt++)); do
    if systemctl is-active --quiet himp; then
        break
    fi

    sleep "$HIMP_READINESS_SLEEP_SECONDS"
done

if ! systemctl is-active --quiet himp; then
    echo "ERROR: HIMP service failed to start."
    systemctl status himp --no-pager || true
    journalctl -u himp -n 100 --no-pager || true
    exit 1
fi

echo
echo "Waiting for HIMP application readiness..."

HIMP_READY=false

for ((attempt = 1; attempt <= HIMP_READINESS_ATTEMPTS; attempt++)); do
    if curl \
        --fail \
        --silent \
        --show-error \
        --output /dev/null \
        --max-time 2 \
        "$HIMP_READINESS_URL"; then

        HIMP_READY=true
        break
    fi

    sleep "$HIMP_READINESS_SLEEP_SECONDS"
done

if [[ "$HIMP_READY" != "true" ]]; then
    echo "ERROR: HIMP service is active but application readiness failed."
    echo "  readiness URL: $HIMP_READINESS_URL"
    systemctl status himp --no-pager || true
    journalctl -u himp -n 100 --no-pager || true
    exit 1
fi

echo "HIMP application is ready."

printf '%s\n' "$SOURCE_REVISION" > "$RELEASE_MARKER"
chown himp:himp "$RELEASE_MARKER"
chmod 0644 "$RELEASE_MARKER"

if [[ ! -s "$RELEASE_MARKER" ]]; then
    echo "ERROR: Release marker was not created:"
    echo "  $RELEASE_MARKER"
    exit 1
fi

if [[ "$(cat "$RELEASE_MARKER")" != "$SOURCE_REVISION" ]]; then
    echo "ERROR: Release marker does not match deployed source revision."
    echo "  expected: $SOURCE_REVISION"
    echo "  actual:   $(cat "$RELEASE_MARKER")"
    exit 1
fi

echo
echo "Deployed revision: $(cat "$RELEASE_MARKER")"

echo
echo "========================================="
echo " HIMP Deployment Complete"
echo "========================================="
echo

systemctl status himp --no-pager
