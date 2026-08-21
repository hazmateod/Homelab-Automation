"""
Deterministic historical health analysis.

Analyzes existing HIMP plugin and host health history without creating
another persistence layer. Relationship-aware correlation reuses the
Phase 12.5 dependency graph to analyze reachable host dependencies.

Relationship assets without persisted host-health history remain valid
topology assets and are reported explicitly as history unavailable.
"""

from datetime import datetime

from himp.database.health_history import (
    HealthHistoryRepository,
)
from himp.database.host_health import (
    HostHealthRepository,
)
from himp.services.dependency_impact import (
    DependencyImpactService,
)


class HealthAnalysisService:
    """
    Compute deterministic health behavior from persisted observations.
    """

    HEALTHY_STATUS = "PASS"

    def __init__(
        self,
        plugin_repository=None,
        host_repository=None,
        dependencies=None,
    ):
        self.plugin_repository = (
            plugin_repository
            or HealthHistoryRepository()
        )

        self.host_repository = (
            host_repository
            or HostHealthRepository()
        )

        self.dependencies = (
            dependencies
            or DependencyImpactService()
        )

    @staticmethod
    def _created_at_text(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        return str(value)

    @staticmethod
    def _created_at_datetime(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(
                str(value)
            )
        except ValueError:
            return None

    @classmethod
    def _binary_state(
        cls,
        status,
    ):
        return (
            "HEALTHY"
            if status == cls.HEALTHY_STATUS
            else "UNHEALTHY"
        )

    @classmethod
    def _chronological(
        cls,
        records,
    ):
        return sorted(
            records,
            key=lambda item: (
                cls._created_at_text(
                    item.get("created_at")
                )
                or "",
                item.get("id", 0),
            ),
        )

    @classmethod
    def analyze_records(
        cls,
        records,
    ):
        """
        Analyze one ordered health observation stream.

        Observed unhealthy duration is limited to intervals between
        persisted observations. No duration is invented beyond the
        newest stored record.
        """
        records = cls._chronological(
            records
        )

        if not records:
            return {
                "history_available": False,
                "observation_count": 0,
                "pass_count": 0,
                "warning_count": 0,
                "fail_count": 0,
                "unknown_count": 0,
                "unhealthy_count": 0,
                "unhealthy_percentage": 0.0,
                "failure_percentage": 0.0,
                "transition_count": 0,
                "flap_count": 0,
                "is_flapping": False,
                "current_status": None,
                "current_state": "UNKNOWN",
                "current_streak": 0,
                "first_observation": None,
                "latest_observation": None,
                "observed_unhealthy_duration_seconds": 0.0,
            }

        statuses = [
            str(
                item.get(
                    "status",
                    "UNKNOWN",
                )
            ).upper()
            for item in records
        ]

        states = [
            cls._binary_state(
                status
            )
            for status in statuses
        ]

        pass_count = statuses.count(
            "PASS"
        )

        warning_count = statuses.count(
            "WARNING"
        )

        fail_count = statuses.count(
            "FAIL"
        )

        unknown_count = sum(
            status
            not in {
                "PASS",
                "WARNING",
                "FAIL",
            }
            for status in statuses
        )

        unhealthy_count = (
            len(statuses)
            - pass_count
        )

        transitions = sum(
            current != previous
            for previous, current in zip(
                states,
                states[1:],
            )
        )

        flap_count = max(
            0,
            transitions - 1,
        )

        current_state = states[-1]
        current_streak = 0

        for state in reversed(
            states
        ):
            if state != current_state:
                break

            current_streak += 1

        unhealthy_duration = 0.0

        for index in range(
            len(records) - 1
        ):
            if states[index] != "UNHEALTHY":
                continue

            started = (
                cls._created_at_datetime(
                    records[index].get(
                        "created_at"
                    )
                )
            )

            ended = (
                cls._created_at_datetime(
                    records[index + 1].get(
                        "created_at"
                    )
                )
            )

            if (
                started is None
                or ended is None
            ):
                continue

            seconds = (
                ended - started
            ).total_seconds()

            if seconds > 0:
                unhealthy_duration += seconds

        observation_count = len(
            records
        )

        return {
            "history_available": True,
            "observation_count": (
                observation_count
            ),
            "pass_count": pass_count,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "unknown_count": unknown_count,
            "unhealthy_count": unhealthy_count,
            "unhealthy_percentage": round(
                (
                    unhealthy_count
                    / observation_count
                )
                * 100,
                2,
            ),
            "failure_percentage": round(
                (
                    fail_count
                    / observation_count
                )
                * 100,
                2,
            ),
            "transition_count": transitions,
            "flap_count": flap_count,
            "is_flapping": (
                transitions >= 3
            ),
            "current_status": statuses[-1],
            "current_state": current_state,
            "current_streak": current_streak,
            "first_observation": (
                cls._created_at_text(
                    records[0].get(
                        "created_at"
                    )
                )
            ),
            "latest_observation": (
                cls._created_at_text(
                    records[-1].get(
                        "created_at"
                    )
                )
            ),
            "observed_unhealthy_duration_seconds": (
                round(
                    unhealthy_duration,
                    3,
                )
            ),
        }

    @staticmethod
    def _validate_limit(
        limit,
    ):
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
            or limit > 500
        ):
            raise ValueError(
                "limit must be an integer "
                "between 1 and 500"
            )

        return limit

    def plugin(
        self,
        plugin,
        limit=100,
    ):
        limit = self._validate_limit(
            limit
        )

        if (
            not isinstance(plugin, str)
            or not plugin.strip()
        ):
            raise ValueError(
                "plugin must not be empty"
            )

        plugin = plugin.strip()

        history = (
            self.plugin_repository.plugin(
                plugin
            )
        )[:limit]

        if not history:
            return None

        return {
            "kind": "plugin",
            "plugin": plugin,
            "limit": limit,
            "analysis": (
                self.analyze_records(
                    history
                )
            ),
        }

    def host(
        self,
        hostname,
        limit=100,
    ):
        limit = self._validate_limit(
            limit
        )

        if (
            not isinstance(hostname, str)
            or not hostname.strip()
        ):
            raise ValueError(
                "hostname must not be empty"
            )

        hostname = hostname.strip()

        history = self.host_repository.host(
            hostname=hostname,
            limit=limit,
        )

        if not history:
            return None

        return {
            "kind": "host",
            "hostname": hostname,
            "limit": limit,
            "analysis": (
                self.analyze_records(
                    history
                )
            ),
        }

    def correlate(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        """
        Analyze historical health of reachable host dependencies.

        A relationship host with no host-health observations remains
        present in the result with history_available=False and
        current_state=UNKNOWN.
        """
        limit = self._validate_limit(
            limit
        )

        dependency_result = (
            self.dependencies.dependencies(
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )

        hosts = []

        for dependency in (
            dependency_result["assets"]
        ):
            if (
                dependency["entity_type"]
                != "host"
            ):
                continue

            hostname = dependency[
                "entity_id"
            ]

            host_result = self.host(
                hostname,
                limit=limit,
            )

            analysis = (
                host_result["analysis"]
                if host_result is not None
                else self.analyze_records(
                    []
                )
            )

            hosts.append(
                {
                    "hostname": hostname,
                    "depth": dependency[
                        "depth"
                    ],
                    "path": dependency[
                        "path"
                    ],
                    "history_available": (
                        analysis[
                            "history_available"
                        ]
                    ),
                    "analysis": analysis,
                }
            )

        hosts.sort(
            key=lambda item: (
                item["depth"],
                item["hostname"],
            )
        )

        return {
            "entity_type": (
                dependency_result[
                    "entity_type"
                ]
            ),
            "entity_id": (
                dependency_result[
                    "entity_id"
                ]
            ),
            "limit": limit,
            "host_count": len(
                hosts
            ),
            "history_available_hosts": sum(
                item[
                    "history_available"
                ]
                for item in hosts
            ),
            "history_unavailable_hosts": sum(
                not item[
                    "history_available"
                ]
                for item in hosts
            ),
            "unhealthy_hosts": sum(
                item["analysis"][
                    "current_state"
                ]
                == "UNHEALTHY"
                for item in hosts
            ),
            "flapping_hosts": sum(
                item["analysis"][
                    "is_flapping"
                ]
                for item in hosts
            ),
            "hosts": hosts,
        }
