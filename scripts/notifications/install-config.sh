#!/usr/bin/env bash

set -euo pipefail

TARGET="${HIMP_NOTIFICATIONS_CONFIG_TARGET:-/etc/himp/notifications.env}"
WEBHOOK_FILE="${HIMP_DISCORD_WEBHOOK_FILE:-}"


fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}


quote_environment_value() {
    local value="$1"

    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"

    printf '"%s"' "$value"
}


if [[ "${1:-}" == "--remove" ]]; then
    rm -f -- "$TARGET"
    printf 'HIMP notification configuration removed.\n'
    printf 'target=%s\n' "$TARGET"
    printf 'No HIMP services were restarted.\n'
    exit 0
fi


if [[ $# -ne 0 ]]; then
    fail "unexpected command-line arguments."
fi


if [[ -n "${HIMP_DISCORD_WEBHOOK_URL:-}" ]]; then
    fail         "HIMP_DISCORD_WEBHOOK_URL must not be supplied directly; use HIMP_DISCORD_WEBHOOK_FILE."
fi


[[ -n "$WEBHOOK_FILE" ]] ||     fail "HIMP_DISCORD_WEBHOOK_FILE is required."

[[ -f "$WEBHOOK_FILE" ]] ||     fail "Discord webhook file does not exist."

[[ ! -L "$WEBHOOK_FILE" ]] ||     fail "Discord webhook file must not be a symbolic link."


WEBHOOK_URL="$(
    cat -- "$WEBHOOK_FILE"
)"


[[ -n "$WEBHOOK_URL" ]] ||     fail "Discord webhook file is empty."


if [[ "$WEBHOOK_URL" == *$'\n'* ||       "$WEBHOOK_URL" == *$'\r'* ]]; then
    fail "Discord webhook URL contains an invalid newline."
fi


case "$WEBHOOK_URL" in
    https://discord.com/api/webhooks/*|    https://discordapp.com/api/webhooks/*)
        ;;
    *)
        fail "Discord webhook URL is not an approved Discord webhook endpoint."
        ;;
esac


TARGET_DIRECTORY="$(
    dirname -- "$TARGET"
)"

TARGET_NAME="$(
    basename -- "$TARGET"
)"

mkdir -p "$TARGET_DIRECTORY"
chmod 0755 "$TARGET_DIRECTORY"

TEMP_FILE="$(
    mktemp         "${TARGET_DIRECTORY}/.${TARGET_NAME}.tmp.XXXXXX"
)"

cleanup() {
    rm -f -- "$TEMP_FILE"
}

trap cleanup EXIT

chmod 0600 "$TEMP_FILE"

{
    printf 'HIMP_DISCORD_WEBHOOK_URL=%s\n'         "$(quote_environment_value "$WEBHOOK_URL")"
} > "$TEMP_FILE"

chmod 0600 "$TEMP_FILE"

mv -f "$TEMP_FILE" "$TARGET"

trap - EXIT

chmod 0600 "$TARGET"

printf 'HIMP notification configuration installed.\n'
printf 'target=%s\n' "$TARGET"
printf 'discord_webhook=REDACTED\n'
printf 'No HIMP services were restarted.\n'
