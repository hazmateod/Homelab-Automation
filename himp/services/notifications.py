"""
Notification Service.

Owns transport-independent notification validation, routing decisions,
duplicate suppression, acknowledgement, and recovery lifecycle semantics.
"""

from datetime import datetime, timezone

from himp.database.notifications import (
    NotificationRepository,
)
from himp.models.notification import (
    NotificationEvent,
)
from himp.services.notification_delivery import (
    NotificationDeliveryService,
)


class NotificationRoutingPolicy:
    ROUTABLE_SEVERITIES = {
        "WARNING",
        "CRITICAL",
        "RECOVERY",
    }

    def __init__(
        self,
        logical_destinations=None,
    ):
        self.logical_destinations = tuple(
            logical_destinations
            if logical_destinations is not None
            else (
                "DEFAULT",
            )
        )

    def route(
        self,
        event,
    ):
        if (
            event.severity
            not in self.ROUTABLE_SEVERITIES
        ):
            return {
                "decision": "SUPPRESS",
                "logical_destinations": [],
                "reason": (
                    "severity is not routable"
                ),
            }

        return {
            "decision": "ROUTE",
            "logical_destinations": list(
                self.logical_destinations
            ),
            "reason": None,
        }


class NotificationService:
    EVENT_TYPES = {
        "STORAGE_WARNING",
        "STORAGE_CRITICAL",
        "STORAGE_RECOVERED",
    }

    SEVERITIES = {
        "INFO",
        "WARNING",
        "CRITICAL",
        "RECOVERY",
    }

    def __init__(
        self,
        repository=None,
        routing_policy=None,
        delivery=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else NotificationRepository()
        )

        self.routing_policy = (
            routing_policy
            if routing_policy is not None
            else NotificationRoutingPolicy()
        )

        self.delivery = (
            delivery
            if delivery is not None
            else NotificationDeliveryService()
        )

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    @staticmethod
    def _required_text(
        value,
        name,
    ):
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{name} is required"
            )

        return value.strip()

    def publish(
        self,
        event,
    ):
        if not isinstance(
            event,
            NotificationEvent,
        ):
            raise TypeError(
                "event must be a NotificationEvent"
            )

        if event.event_type not in self.EVENT_TYPES:
            raise ValueError(
                "unsupported notification event type: "
                f"{event.event_type}"
            )

        if event.severity not in self.SEVERITIES:
            raise ValueError(
                "unsupported notification severity: "
                f"{event.severity}"
            )

        self._required_text(
            event.source_type,
            "source_type",
        )
        self._required_text(
            event.source_id,
            "source_id",
        )
        self._required_text(
            event.title,
            "title",
        )
        self._required_text(
            event.message,
            "message",
        )
        self._required_text(
            event.deduplication_key,
            "deduplication_key",
        )
        self._required_text(
            event.correlation_key,
            "correlation_key",
        )

        if event.severity == "RECOVERY":
            self.repository.recover_correlation(
                event.correlation_key,
                recovered_at=event.occurred_at,
            )

        route = self.routing_policy.route(
            event
        )

        if (
            event.severity != "RECOVERY"
            and self.repository
            .active_for_deduplication(
                event.deduplication_key
            )
            is not None
        ):
            return self.repository.create(
                event,
                lifecycle_status="SUPPRESSED",
                routing_decision="SUPPRESS",
                logical_destinations=[],
                suppression_reason=(
                    "duplicate active notification"
                ),
            )

        lifecycle_status = (
            "RECOVERED"
            if event.severity == "RECOVERY"
            else (
                "SUPPRESSED"
                if route["decision"]
                == "SUPPRESS"
                else "PENDING"
            )
        )

        notification = self.repository.create(
            event,
            lifecycle_status=lifecycle_status,
            routing_decision=route["decision"],
            logical_destinations=(
                route["logical_destinations"]
            ),
            suppression_reason=(
                route["reason"]
            ),
        )

        if route["decision"] == "ROUTE":
            self.delivery.deliver(
                notification
            )

        return notification

    def history(
        self,
        limit=100,
        lifecycle_status=None,
        severity=None,
    ):
        notifications = self.repository.list(
            limit=limit,
            lifecycle_status=lifecycle_status,
            severity=severity,
        )

        return [
            {
                **notification,
                "latest_delivery": (
                    self.delivery.repository
                    .latest_for_notification(
                        notification["id"]
                    )
                ),
            }
            for notification in notifications
        ]

    def summary(
        self,
        limit=100,
        lifecycle_status=None,
        severity=None,
    ):
        rows = self.history(
            limit=limit,
            lifecycle_status=lifecycle_status,
            severity=severity,
        )

        return {
            "rows": rows,
            "count": len(rows),
            "pending": sum(
                1
                for row in rows
                if row["lifecycle_status"]
                == "PENDING"
            ),
            "critical": sum(
                1
                for row in rows
                if row["severity"]
                == "CRITICAL"
            ),
            "delivery_failures": sum(
                1
                for row in rows
                if row["latest_delivery"]
                is not None
                and row["latest_delivery"]["status"]
                == "FAILED"
            ),
        }

    def acknowledge(
        self,
        notification_id,
        acknowledged_by,
    ):
        return self.repository.acknowledge(
            notification_id,
            acknowledged_by,
        )

    def storage_transition(
        self,
        transition,
        occurred_at=None,
    ):
        if not isinstance(
            transition,
            dict,
        ):
            raise TypeError(
                "transition must be a mapping"
            )

        hostname = self._required_text(
            transition.get("hostname"),
            "hostname",
        )

        mount_point = self._required_text(
            transition.get("mount_point"),
            "mount_point",
        )

        current_status = self._required_text(
            transition.get(
                "current_status"
            ),
            "current_status",
        ).upper()

        source_id = (
            f"{hostname}:{mount_point}"
        )

        correlation_key = (
            f"storage:{source_id}"
        )

        mapping = {
            "WARNING": (
                "STORAGE_WARNING",
                "WARNING",
                "Storage capacity warning",
            ),
            "CRITICAL": (
                "STORAGE_CRITICAL",
                "CRITICAL",
                "Storage capacity critical",
            ),
            "PASS": (
                "STORAGE_RECOVERED",
                "RECOVERY",
                "Storage capacity recovered",
            ),
        }

        if current_status not in mapping:
            raise ValueError(
                "unsupported storage transition "
                f"status: {current_status}"
            )

        (
            event_type,
            severity,
            title,
        ) = mapping[current_status]

        used_percent = transition.get(
            "used_percent"
        )

        if current_status == "PASS":
            message = (
                f"{hostname} {mount_point} "
                "returned to normal storage capacity."
            )
        else:
            message = (
                f"{hostname} {mount_point} "
                f"is {current_status.lower()}"
            )

            if used_percent is not None:
                message += (
                    f" at {float(used_percent):.1f}% used."
                )
            else:
                message += "."

        if occurred_at is None:
            occurred_at = self._now()

        event = NotificationEvent(
            event_type=event_type,
            source_type="storage_filesystem",
            source_id=source_id,
            severity=severity,
            title=title,
            message=message,
            deduplication_key=(
                f"{event_type}:{source_id}"
            ),
            correlation_key=correlation_key,
            occurred_at=occurred_at,
            metadata={
                "hostname": hostname,
                "filesystem": (
                    transition.get(
                        "filesystem"
                    )
                ),
                "mount_point": mount_point,
                "used_percent": used_percent,
                "previous_status": (
                    transition.get(
                        "previous_status"
                    )
                ),
                "current_status": (
                    current_status
                ),
            },
        )

        return self.publish(event)
