from himp.services.infrastructure_intelligence import (
    InfrastructureIntelligenceService,
)


def test_infrastructure_intelligence_aggregates_existing_sources():
    class FakeRelationships:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            return [
                {
                    "target_id": "pve02",
                    "health_status": "FAIL",
                },
            ]

    class FakeInventory:
        def changes(
            self,
            limit=100,
        ):
            assert limit == 10

            return [
                {
                    "hostname": "pve01",
                    "change_type": "UPDATED",
                    "field": "ip",
                },
            ]

    class FakeBaseline:
        def compare(
            self,
            name,
        ):
            assert name == "production"

            return {
                "baseline": "production",
                "drift": [
                    {
                        "hostname": "pve01",
                        "field": "ip",
                        "expected": "192.168.10.51",
                        "actual": "192.168.10.52",
                        "drift_type": "CHANGED",
                    },
                ],
            }

    class FakeHealthCorrelation:
        def correlate(
            self,
            source_type,
            source_id,
        ):
            assert source_type == "host"
            assert source_id == "pve01"

            return {
                "source_type": "host",
                "source_id": "pve01",
                "relationships": [
                    {
                        "target_id": "pve02",
                        "health_status": "FAIL",
                    },
                ],
            }

    service = InfrastructureIntelligenceService(
        relationships=FakeRelationships(),
        inventory=FakeInventory(),
        health=FakeHealthCorrelation(),
        baseline=FakeBaseline(),
    )

    result = service.inspect(
        source_type="host",
        source_id="pve01",
        baseline="production",
        change_limit=10,
    )

    assert result == {
        "source_type": "host",
        "source_id": "pve01",
        "relationships": [
            {
                "target_id": "pve02",
                "health_status": "FAIL",
            },
        ],
        "changes": [
            {
                "hostname": "pve01",
                "change_type": "UPDATED",
                "field": "ip",
            },
        ],
        "drift": [
            {
                "hostname": "pve01",
                "field": "ip",
                "expected": "192.168.10.51",
                "actual": "192.168.10.52",
                "drift_type": "CHANGED",
            },
        ],
    }


def test_infrastructure_intelligence_without_baseline_returns_empty_drift():
    class FakeRelationships:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            return {
                "source_type": source_type,
                "source_id": source_id,
                "relationships": [],
            }

    class FakeInventory:
        def changes(
            self,
            limit=100,
        ):
            return []

    class FakeHealthCorrelation:
        def correlate(
            self,
            source_type,
            source_id,
        ):
            return {
                "source_type": source_type,
                "source_id": source_id,
                "relationships": [],
            }

    class FakeBaseline:
        def compare(
            self,
            name,
        ):
            raise AssertionError(
                "baseline comparison should not run"
            )

    service = InfrastructureIntelligenceService(
        relationships=FakeRelationships(),
        inventory=FakeInventory(),
        health=FakeHealthCorrelation(),
        baseline=FakeBaseline(),
    )

    result = service.inspect(
        source_type="host",
        source_id="pve01",
    )

    assert result == {
        "source_type": "host",
        "source_id": "pve01",
        "relationships": [],
        "changes": [],
        "drift": [],
    }


def test_infrastructure_intelligence_propagates_missing_baseline():
    class FakeRelationships:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            return {
                "source_type": source_type,
                "source_id": source_id,
                "relationships": [],
            }

    class FakeInventory:
        def changes(
            self,
            limit=100,
        ):
            return []

    class FakeHealthCorrelation:
        def correlate(
            self,
            source_type,
            source_id,
        ):
            return {
                "source_type": source_type,
                "source_id": source_id,
                "relationships": [],
            }

    class FakeBaseline:
        def compare(
            self,
            name,
        ):
            raise ValueError(
                "Inventory baseline not found: missing"
            )

    service = InfrastructureIntelligenceService(
        relationships=FakeRelationships(),
        inventory=FakeInventory(),
        health=FakeHealthCorrelation(),
        baseline=FakeBaseline(),
    )

    try:
        service.inspect(
            source_type="host",
            source_id="pve01",
            baseline="missing",
        )
    except ValueError as error:
        assert str(error) == (
            "Inventory baseline not found: missing"
        )
    else:
        raise AssertionError(
            "missing baseline should raise ValueError"
        )
