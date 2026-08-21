from himp.services.health_analysis import (
    HealthAnalysisService,
)


def record(
    identifier,
    status,
    created_at,
):
    return {
        "id": identifier,
        "status": status,
        "created_at": created_at,
    }


class FakePluginRepository:
    def __init__(
        self,
        records=None,
    ):
        self.records = (
            records or {}
        )

    def plugin(
        self,
        plugin,
    ):
        return self.records.get(
            plugin,
            []
        )


class FakeHostRepository:
    def __init__(
        self,
        records=None,
    ):
        self.records = (
            records or {}
        )

    def host(
        self,
        hostname,
        limit,
    ):
        return self.records.get(
            hostname,
            []
        )[:limit]


class FakeDependencies:
    def dependencies(
        self,
        entity_type,
        entity_id,
    ):
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "assets": [
                {
                    "entity_type": "database",
                    "entity_id": "himp",
                    "depth": 1,
                    "path": [],
                },
                {
                    "entity_type": "host",
                    "entity_id": (
                        "automation.server.arpa"
                    ),
                    "depth": 1,
                    "path": [
                        {
                            "relationship_type": (
                                "runs_on"
                            )
                        }
                    ],
                },
                {
                    "entity_type": "host",
                    "entity_id": (
                        "himpdb01.server.arpa"
                    ),
                    "depth": 2,
                    "path": [
                        {
                            "relationship_type": (
                                "depends_on"
                            )
                        },
                        {
                            "relationship_type": (
                                "runs_on"
                            )
                        },
                    ],
                },
            ],
        }


def make_service(
    plugin_records=None,
    host_records=None,
):
    return HealthAnalysisService(
        plugin_repository=(
            FakePluginRepository(
                plugin_records
            )
        ),
        host_repository=(
            FakeHostRepository(
                host_records
            )
        ),
        dependencies=(
            FakeDependencies()
        ),
    )


def test_analysis_counts_health_states():
    result = (
        HealthAnalysisService
        .analyze_records(
            [
                record(
                    1,
                    "PASS",
                    "2026-08-20T00:00:00",
                ),
                record(
                    2,
                    "WARNING",
                    "2026-08-20T01:00:00",
                ),
                record(
                    3,
                    "FAIL",
                    "2026-08-20T02:00:00",
                ),
                record(
                    4,
                    "PASS",
                    "2026-08-20T03:00:00",
                ),
            ]
        )
    )

    assert result[
        "history_available"
    ] is True
    assert result["observation_count"] == 4
    assert result["pass_count"] == 2
    assert result["warning_count"] == 1
    assert result["fail_count"] == 1
    assert result["unhealthy_count"] == 2
    assert result["unhealthy_percentage"] == 50.0
    assert result["failure_percentage"] == 25.0


def test_analysis_computes_transitions_and_flapping():
    result = (
        HealthAnalysisService
        .analyze_records(
            [
                record(
                    1,
                    "PASS",
                    "2026-08-20T00:00:00",
                ),
                record(
                    2,
                    "FAIL",
                    "2026-08-20T01:00:00",
                ),
                record(
                    3,
                    "PASS",
                    "2026-08-20T02:00:00",
                ),
                record(
                    4,
                    "FAIL",
                    "2026-08-20T03:00:00",
                ),
            ]
        )
    )

    assert result["transition_count"] == 3
    assert result["flap_count"] == 2
    assert result["is_flapping"] is True


def test_warning_to_fail_is_not_binary_transition():
    result = (
        HealthAnalysisService
        .analyze_records(
            [
                record(
                    1,
                    "PASS",
                    "2026-08-20T00:00:00",
                ),
                record(
                    2,
                    "WARNING",
                    "2026-08-20T01:00:00",
                ),
                record(
                    3,
                    "FAIL",
                    "2026-08-20T02:00:00",
                ),
            ]
        )
    )

    assert result["transition_count"] == 1


def test_current_streak_uses_binary_state():
    result = (
        HealthAnalysisService
        .analyze_records(
            [
                record(
                    1,
                    "PASS",
                    "2026-08-20T00:00:00",
                ),
                record(
                    2,
                    "WARNING",
                    "2026-08-20T01:00:00",
                ),
                record(
                    3,
                    "FAIL",
                    "2026-08-20T02:00:00",
                ),
            ]
        )
    )

    assert result["current_status"] == "FAIL"
    assert (
        result["current_state"]
        == "UNHEALTHY"
    )
    assert result["current_streak"] == 2


def test_observed_unhealthy_duration():
    result = (
        HealthAnalysisService
        .analyze_records(
            [
                record(
                    1,
                    "PASS",
                    "2026-08-20T00:00:00",
                ),
                record(
                    2,
                    "FAIL",
                    "2026-08-20T01:00:00",
                ),
                record(
                    3,
                    "FAIL",
                    "2026-08-20T02:30:00",
                ),
                record(
                    4,
                    "PASS",
                    "2026-08-20T03:00:00",
                ),
            ]
        )
    )

    assert (
        result[
            "observed_unhealthy_duration_seconds"
        ]
        == 7200.0
    )


def test_analysis_orders_newest_first_repository_rows():
    result = (
        HealthAnalysisService
        .analyze_records(
            [
                record(
                    3,
                    "PASS",
                    "2026-08-20T03:00:00",
                ),
                record(
                    2,
                    "FAIL",
                    "2026-08-20T02:00:00",
                ),
                record(
                    1,
                    "PASS",
                    "2026-08-20T01:00:00",
                ),
            ]
        )
    )

    assert (
        result["first_observation"]
        == "2026-08-20T01:00:00"
    )
    assert (
        result["latest_observation"]
        == "2026-08-20T03:00:00"
    )
    assert result["current_status"] == "PASS"


def test_empty_analysis_is_explicitly_unknown():
    result = (
        HealthAnalysisService
        .analyze_records(
            []
        )
    )

    assert result[
        "history_available"
    ] is False
    assert result["observation_count"] == 0
    assert result["current_status"] is None
    assert result["current_state"] == "UNKNOWN"
    assert result["is_flapping"] is False


def test_plugin_analysis():
    service = make_service(
        plugin_records={
            "technitium": [
                record(
                    2,
                    "PASS",
                    "2026-08-20T02:00:00",
                ),
                record(
                    1,
                    "WARNING",
                    "2026-08-20T01:00:00",
                ),
            ]
        }
    )

    result = service.plugin(
        "technitium",
        limit=100,
    )

    assert result["kind"] == "plugin"
    assert (
        result["analysis"][
            "observation_count"
        ]
        == 2
    )
    assert (
        result["analysis"][
            "transition_count"
        ]
        == 1
    )


def test_missing_plugin_returns_none():
    service = make_service()

    assert service.plugin(
        "missing"
    ) is None


def test_host_analysis():
    service = make_service(
        host_records={
            "pbs01": [
                record(
                    2,
                    "PASS",
                    "2026-08-20T02:00:00",
                ),
                record(
                    1,
                    "FAIL",
                    "2026-08-20T01:00:00",
                ),
            ]
        }
    )

    result = service.host(
        "pbs01",
        limit=100,
    )

    assert result["kind"] == "host"
    assert result["hostname"] == "pbs01"
    assert result["analysis"]["fail_count"] == 1
    assert result["analysis"][
        "history_available"
    ] is True


def test_correlation_analyzes_reachable_hosts():
    service = make_service(
        host_records={
            "automation.server.arpa": [
                record(
                    1,
                    "PASS",
                    "2026-08-20T01:00:00",
                )
            ],
            "himpdb01.server.arpa": [
                record(
                    1,
                    "PASS",
                    "2026-08-20T01:00:00",
                )
            ],
        }
    )

    result = service.correlate(
        "application",
        "himp",
        limit=100,
    )

    assert result["host_count"] == 2
    assert (
        result["history_available_hosts"]
        == 2
    )
    assert (
        result["history_unavailable_hosts"]
        == 0
    )

    assert [
        (
            item["hostname"],
            item["depth"],
        )
        for item in result["hosts"]
    ] == [
        (
            "automation.server.arpa",
            1,
        ),
        (
            "himpdb01.server.arpa",
            2,
        ),
    ]


def test_correlation_preserves_host_without_health_history():
    service = make_service(
        host_records={
            "himpdb01.server.arpa": [
                record(
                    1,
                    "PASS",
                    "2026-08-20T01:00:00",
                )
            ],
        }
    )

    result = service.correlate(
        "application",
        "himp",
    )

    host_map = {
        item["hostname"]: item
        for item in result["hosts"]
    }

    automation = host_map[
        "automation.server.arpa"
    ]

    assert (
        automation[
            "history_available"
        ]
        is False
    )

    assert (
        automation["analysis"][
            "current_state"
        ]
        == "UNKNOWN"
    )

    assert (
        automation["analysis"][
            "observation_count"
        ]
        == 0
    )

    assert (
        result[
            "history_available_hosts"
        ]
        == 1
    )

    assert (
        result[
            "history_unavailable_hosts"
        ]
        == 1
    )

    assert result["unhealthy_hosts"] == 0


def test_correlation_reports_unhealthy_and_flapping_hosts():
    service = make_service(
        host_records={
            "automation.server.arpa": [
                record(
                    4,
                    "FAIL",
                    "2026-08-20T04:00:00",
                ),
                record(
                    3,
                    "PASS",
                    "2026-08-20T03:00:00",
                ),
                record(
                    2,
                    "FAIL",
                    "2026-08-20T02:00:00",
                ),
                record(
                    1,
                    "PASS",
                    "2026-08-20T01:00:00",
                ),
            ],
            "himpdb01.server.arpa": [
                record(
                    1,
                    "PASS",
                    "2026-08-20T01:00:00",
                )
            ],
        }
    )

    result = service.correlate(
        "application",
        "himp",
    )

    assert result["unhealthy_hosts"] == 1
    assert result["flapping_hosts"] == 1
