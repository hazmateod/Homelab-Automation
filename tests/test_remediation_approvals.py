import pytest

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.remediation_approvals import (
    RemediationApprovalRepository,
)


def recommendation():
    return {
        "recommendation_id": (
            "HOST_UNHEALTHY:pve01"
        ),
        "condition": "HOST_UNHEALTHY",
        "severity": "CRITICAL",
        "target": {
            "entity_type": "host",
            "entity_id": "pve01",
        },
        "dependency_depth": 2,
        "dependency_path": [
            {
                "source_type": "application",
                "source_id": "himp",
                "relationship_type": "depends_on",
                "target_type": "host",
                "target_id": "pve01",
            }
        ],
        "evidence": {
            "current_state": "UNHEALTHY",
            "current_status": "FAIL",
            "observation_count": 4,
        },
        "affected_assets": [
            {
                "entity_type": "application",
                "entity_id": "himp",
                "depth": 1,
            }
        ],
        "recommended_action": (
            "Investigate host connectivity."
        ),
        "rationale": (
            "Persisted health evidence is unhealthy."
        ),
        "automation": None,
        "execution_permitted": False,
    }


def make_repository(tmp_path):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path / "approvals.db"
            ),
        )
    )

    return RemediationApprovalRepository(
        database=database
    )


def test_create_persists_pending_approval(tmp_path):
    repository = make_repository(
        tmp_path
    )

    result = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    assert result["id"] == 1
    assert result["status"] == "PENDING"
    assert result["requested_by"] == "admin"
    assert result["decided_by"] is None
    assert result["decided_at"] is None
    assert result["recommendation_id"] == (
        "HOST_UNHEALTHY:pve01"
    )
    assert result["target_id"] == "pve01"
    assert result["evidence"][
        "current_status"
    ] == "FAIL"
    assert result["affected_assets"][0][
        "entity_id"
    ] == "himp"
    assert result["dependency_depth"] == 2


def test_find_returns_none_for_missing_record(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    assert repository.find(999) is None


def test_list_filters_by_status(tmp_path):
    repository = make_repository(
        tmp_path
    )

    first = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    repository.decide(
        approval_id=first["id"],
        status="APPROVED",
        decided_by="admin",
    )

    second = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    pending = repository.list(
        status="PENDING"
    )

    assert len(pending) == 1
    assert pending[0]["id"] == second["id"]

    approved = repository.list(
        status="APPROVED"
    )

    assert len(approved) == 1
    assert approved[0]["id"] == first["id"]


def test_summary_counts_lifecycle_states(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    one = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    two = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    repository.decide(
        approval_id=one["id"],
        status="APPROVED",
        decided_by="admin",
    )

    repository.decide(
        approval_id=two["id"],
        status="DENIED",
        decided_by="admin",
    )

    assert repository.summary() == {
        "total": 3,
        "pending": 1,
        "approved": 1,
        "denied": 1,
    }


def test_approve_records_operator_and_note(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    approval = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="requester",
    )

    result = repository.decide(
        approval_id=approval["id"],
        status="APPROVED",
        decided_by="admin",
        decision_note="Reviewed evidence.",
    )

    assert result["status"] == "APPROVED"
    assert result["decided_by"] == "admin"
    assert result["decision_note"] == (
        "Reviewed evidence."
    )
    assert result["decided_at"] is not None


def test_deny_records_operator_and_note(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    approval = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="requester",
    )

    result = repository.decide(
        approval_id=approval["id"],
        status="DENIED",
        decided_by="admin",
        decision_note="No change required.",
    )

    assert result["status"] == "DENIED"
    assert result["decided_by"] == "admin"


def test_decision_cannot_be_overwritten(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    approval = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    repository.decide(
        approval_id=approval["id"],
        status="APPROVED",
        decided_by="admin",
    )

    with pytest.raises(
        ValueError,
        match="already been decided",
    ):
        repository.decide(
            approval_id=approval["id"],
            status="DENIED",
            decided_by="admin",
        )

    assert repository.find(
        approval["id"]
    )["status"] == "APPROVED"


def test_deciding_missing_record_fails(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    with pytest.raises(
        KeyError,
        match="does not exist",
    ):
        repository.decide(
            approval_id=999,
            status="APPROVED",
            decided_by="admin",
        )


def test_invalid_status_filter_fails(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="invalid approval status",
    ):
        repository.list(
            status="EXECUTED"
        )


def test_invalid_decision_fails(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    approval = repository.create(
        recommendation=recommendation(),
        source_type="application",
        source_id="himp",
        requested_by="admin",
    )

    with pytest.raises(
        ValueError,
        match="APPROVED or DENIED",
    ):
        repository.decide(
            approval_id=approval["id"],
            status="PENDING",
            decided_by="admin",
        )
