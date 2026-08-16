#!/usr/bin/env bash

set -euo pipefail

DATABASE_CONFIG_TARGET="${HIMP_DATABASE_CONFIG_TARGET:-/etc/himp/database.env}"

BACKEND="${HIMP_DATABASE_BACKEND:-postgresql}"
HOST="${HIMP_DATABASE_HOST:-himpdb01.server.arpa}"
PORT="${HIMP_DATABASE_PORT:-5432}"
DATABASE="${HIMP_DATABASE_NAME:-himp}"
USER="${HIMP_DATABASE_USER:-himp_app}"

PASSWORD_FILE="${HIMP_DATABASE_PASSWORD_FILE:-}"

usage() {
    cat <<'EOF'
Usage:

  Install PostgreSQL configuration:

    HIMP_DATABASE_PASSWORD_FILE=/secure/password/file \
      scripts/database/install-config.sh

  Remove external database configuration and restore the
  default SQLite configuration boundary:

    scripts/database/install-config.sh --remove

Optional installation environment variables:

  HIMP_DATABASE_CONFIG_TARGET
  HIMP_DATABASE_BACKEND
  HIMP_DATABASE_HOST
  HIMP_DATABASE_PORT
  HIMP_DATABASE_NAME
  HIMP_DATABASE_USER

The password is read only from HIMP_DATABASE_PASSWORD_FILE.

The password must not be supplied directly through
HIMP_DATABASE_PASSWORD.

This script never starts, stops, or restarts HIMP services.
EOF
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

validate_value() {
    local name="$1"
    local value="$2"

    [[ -n "$value" ]] || \
        fail "$name must not be empty."

    if [[ "$value" == *$'\n'* || \
          "$value" == *$'\r'* ]]; then
        fail "$name contains an invalid newline."
    fi
}

quote_environment_value() {
    local value="$1"

    # systemd EnvironmentFile supports quoted values.
    # Escape the characters meaningful inside double quotes.
    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"

    printf '"%s"' "$value"
}

if [[ "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [[ "${1:-}" == "--remove" ]]; then
    if [[ $# -ne 1 ]]; then
        fail "--remove accepts no additional arguments."
    fi

    if [[ -e "$DATABASE_CONFIG_TARGET" ]]; then
        rm -f -- "$DATABASE_CONFIG_TARGET"
        printf 'HIMP database configuration removed.\n'
    else
        printf 'HIMP database configuration already absent.\n'
    fi

    printf 'target=%s\n' "$DATABASE_CONFIG_TARGET"
    printf 'effective_default_backend=sqlite\n'
    printf 'No HIMP services were restarted.\n'

    exit 0
fi

if [[ $# -ne 0 ]]; then
    fail "unexpected command-line arguments."
fi

if [[ -n "${HIMP_DATABASE_PASSWORD:-}" ]]; then
    fail \
        "HIMP_DATABASE_PASSWORD must not be supplied to this installer; use HIMP_DATABASE_PASSWORD_FILE."
fi

if [[ "$BACKEND" != "postgresql" ]]; then
    fail \
        "secure database configuration installer currently supports only the postgresql backend."
fi

validate_value \
    "HIMP_DATABASE_HOST" \
    "$HOST"

validate_value \
    "HIMP_DATABASE_NAME" \
    "$DATABASE"

validate_value \
    "HIMP_DATABASE_USER" \
    "$USER"

if [[ ! "$PORT" =~ ^[0-9]+$ ]]; then
    fail "HIMP_DATABASE_PORT must be numeric."
fi

if (( PORT < 1 || PORT > 65535 )); then
    fail "HIMP_DATABASE_PORT must be between 1 and 65535."
fi

[[ -n "$PASSWORD_FILE" ]] || \
    fail "HIMP_DATABASE_PASSWORD_FILE is required."

[[ -f "$PASSWORD_FILE" ]] || \
    fail "database password file does not exist."

[[ ! -L "$PASSWORD_FILE" ]] || \
    fail "database password file must not be a symbolic link."

PASSWORD="$(
    cat -- "$PASSWORD_FILE"
)"

[[ -n "$PASSWORD" ]] || \
    fail "database password file is empty."

if [[ "$PASSWORD" == *$'\n'* || \
      "$PASSWORD" == *$'\r'* ]]; then
    fail "database password contains an invalid embedded newline."
fi

TARGET_DIRECTORY="$(
    dirname -- "$DATABASE_CONFIG_TARGET"
)"

TARGET_NAME="$(
    basename -- "$DATABASE_CONFIG_TARGET"
)"

mkdir -p \
    "$TARGET_DIRECTORY"

chmod 0755 \
    "$TARGET_DIRECTORY"

TEMP_FILE="$(
    mktemp \
        "${TARGET_DIRECTORY}/.${TARGET_NAME}.tmp.XXXXXX"
)"

cleanup() {
    rm -f -- "$TEMP_FILE"
}

trap cleanup EXIT

chmod 0600 \
    "$TEMP_FILE"

{
    printf 'HIMP_DATABASE_BACKEND=%s\n' \
        "$(quote_environment_value "$BACKEND")"

    printf 'HIMP_DATABASE_HOST=%s\n' \
        "$(quote_environment_value "$HOST")"

    printf 'HIMP_DATABASE_PORT=%s\n' \
        "$(quote_environment_value "$PORT")"

    printf 'HIMP_DATABASE_NAME=%s\n' \
        "$(quote_environment_value "$DATABASE")"

    printf 'HIMP_DATABASE_USER=%s\n' \
        "$(quote_environment_value "$USER")"

    printf 'HIMP_DATABASE_PASSWORD=%s\n' \
        "$(quote_environment_value "$PASSWORD")"
} > "$TEMP_FILE"

chmod 0600 \
    "$TEMP_FILE"

mv -f \
    "$TEMP_FILE" \
    "$DATABASE_CONFIG_TARGET"

trap - EXIT

chmod 0600 \
    "$DATABASE_CONFIG_TARGET"

printf 'HIMP database configuration installed.\n'
printf 'target=%s\n' "$DATABASE_CONFIG_TARGET"
printf 'backend=%s\n' "$BACKEND"
printf 'host=%s\n' "$HOST"
printf 'port=%s\n' "$PORT"
printf 'database=%s\n' "$DATABASE"
printf 'user=%s\n' "$USER"
printf 'credentials=REDACTED\n'
printf 'No HIMP services were restarted.\n'
