"""
Notification Delivery Service.

Dispatches routed notifications to configured transports while keeping
transport failure isolated from the originating operational workflow.
"""

import logging

from himp.database.notification_deliveries import (
    NotificationDeliveryRepository,
)
from himp.services.notification_transports import (
    DiscordWebhookTransport,
)


logger = logging.getLogger("himp.notifications")


class NotificationDeliveryService:
    def __init__(
        self,
        repository=None,
        transports=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else NotificationDeliveryRepository()
        )

        self.transports = (
            list(transports)
            if transports is not None
            else [
                DiscordWebhookTransport(),
            ]
        )

    def deliver(
        self,
        notification,
    ):
        if (
            notification["routing_decision"]
            != "ROUTE"
        ):
            return []

        destinations = set(
            notification[
                "logical_destinations"
            ]
        )

        results = []

        for transport in self.transports:
            if (
                transport.destination_name
                not in destinations
            ):
                continue

            try:
                result = transport.send(
                    notification
                )
            except Exception as error:
                logger.exception(
                    "Notification delivery failed "
                    "without exposing destination secrets."
                )

                result = {
                    "status": "FAILED",
                    "status_code": None,
                    "error": (
                        "Unexpected transport failure: "
                        f"{error.__class__.__name__}"
                    ),
                }

            delivery = self.repository.record(
                notification_id=notification["id"],
                destination_type=(
                    transport.destination_type
                ),
                destination_name=(
                    transport.destination_name
                ),
                status=result["status"],
                status_code=result.get(
                    "status_code"
                ),
                error=result.get("error"),
            )

            results.append(delivery)

        return results
