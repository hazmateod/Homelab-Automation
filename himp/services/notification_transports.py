"""
Notification transports.

Transport implementations deliberately receive persisted notification
records and never own notification lifecycle state.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DiscordWebhookTransport:
    destination_type = "DISCORD"
    destination_name = "DEFAULT"

    def __init__(
        self,
        webhook_url=None,
        timeout=10,
        opener=None,
    ):
        self.webhook_url = (
            webhook_url
            if webhook_url is not None
            else os.environ.get(
                "HIMP_DISCORD_WEBHOOK_URL"
            )
        )
        self.timeout = timeout
        self.opener = opener or urlopen

    @property
    def configured(self):
        return bool(
            isinstance(self.webhook_url, str)
            and self.webhook_url.strip()
        )

    @staticmethod
    def _color(severity):
        return {
            "WARNING": 16776960,
            "CRITICAL": 16711680,
            "RECOVERY": 65280,
            "INFO": 8421504,
        }.get(
            severity,
            8421504,
        )

    def payload(
        self,
        notification,
    ):
        return {
            "username": "HIMP",
            "embeds": [
                {
                    "title": notification["title"],
                    "description": notification["message"],
                    "color": self._color(
                        notification["severity"]
                    ),
                    "fields": [
                        {
                            "name": "Severity",
                            "value": notification["severity"],
                            "inline": True,
                        },
                        {
                            "name": "Event",
                            "value": notification["event_type"],
                            "inline": True,
                        },
                        {
                            "name": "Source",
                            "value": notification["source_id"],
                            "inline": False,
                        },
                    ],
                    "timestamp": (
                        notification["occurred_at"]
                        .isoformat()
                        + "Z"
                    ),
                }
            ],
        }

    def send(
        self,
        notification,
    ):
        if not self.configured:
            return {
                "status": "SKIPPED",
                "status_code": None,
                "error": "Discord webhook is not configured.",
            }

        payload = json.dumps(
            self.payload(notification)
        ).encode("utf-8")

        request = Request(
            self.webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "HIMP/1.0",
            },
            method="POST",
        )

        try:
            with self.opener(
                request,
                timeout=self.timeout,
            ) as response:
                status_code = response.getcode()

            if 200 <= status_code < 300:
                return {
                    "status": "SUCCESS",
                    "status_code": status_code,
                    "error": None,
                }

            return {
                "status": "FAILED",
                "status_code": status_code,
                "error": (
                    "Discord webhook returned a "
                    f"non-success status: {status_code}"
                ),
            }

        except HTTPError as error:
            return {
                "status": "FAILED",
                "status_code": error.code,
                "error": (
                    "Discord webhook returned HTTP "
                    f"{error.code}"
                ),
            }

        except (URLError, TimeoutError, OSError) as error:
            return {
                "status": "FAILED",
                "status_code": None,
                "error": (
                    "Discord webhook delivery failed: "
                    f"{error.__class__.__name__}"
                ),
            }
