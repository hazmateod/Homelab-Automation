import json
from datetime import datetime
from urllib.error import URLError

from himp.services.notification_transports import (
    DiscordWebhookTransport,
)


def notification():
    return {
        "id": 1,
        "event_type": "STORAGE_CRITICAL",
        "source_type": "storage_filesystem",
        "source_id": "pbs01:/backup",
        "severity": "CRITICAL",
        "title": "Storage capacity critical",
        "message": "pbs01 /backup is critical at 93.2% used.",
        "occurred_at": datetime(
            2026,
            8,
            22,
            18,
            30,
        ),
    }


class FakeResponse:
    def __init__(
        self,
        status_code=204,
    ):
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def getcode(self):
        return self.status_code


def test_discord_transport_skips_when_unconfigured():
    transport = DiscordWebhookTransport(
        webhook_url=""
    )

    assert transport.send(
        notification()
    ) == {
        "status": "SKIPPED",
        "status_code": None,
        "error": "Discord webhook is not configured.",
    }


def test_discord_transport_posts_expected_payload():
    captured = {}

    def opener(
        request,
        timeout,
    ):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(
            request.data.decode("utf-8")
        )

        return FakeResponse(204)

    transport = DiscordWebhookTransport(
        webhook_url=(
            "https://discord.com/api/webhooks/"
            "123456/secret-value"
        ),
        opener=opener,
    )

    result = transport.send(
        notification()
    )

    assert result == {
        "status": "SUCCESS",
        "status_code": 204,
        "error": None,
    }

    assert (
        captured["url"]
        == "https://discord.com/api/webhooks/"
        "123456/secret-value"
    )

    assert captured["timeout"] == 10

    embed = captured["payload"]["embeds"][0]

    assert (
        embed["title"]
        == "Storage capacity critical"
    )
    assert embed["color"] == 16711680
    assert (
        embed["fields"][0]["value"]
        == "CRITICAL"
    )


def test_discord_transport_does_not_expose_url_on_failure():
    def opener(
        request,
        timeout,
    ):
        raise URLError(
            "contains-sensitive-endpoint"
        )

    transport = DiscordWebhookTransport(
        webhook_url=(
            "https://discord.com/api/webhooks/"
            "123456/do-not-expose"
        ),
        opener=opener,
    )

    result = transport.send(
        notification()
    )

    assert result["status"] == "FAILED"
    assert result["status_code"] is None
    assert "do-not-expose" not in result["error"]
    assert "contains-sensitive-endpoint" not in result["error"]
