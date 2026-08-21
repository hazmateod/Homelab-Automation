import sqlite3

from himp.database.remediation_audit import (
    RemediationAuditRepository,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()
        cursor.execute(
            sql,
            parameters,
        )
        self.connection.commit()
        return cursor

    def query(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()
        cursor.execute(
            sql,
            parameters,
        )
        return cursor.fetchall()

    def execute_insert(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor.lastrowid

    def table_columns(
        self,
        table,
    ):
        rows = self.query(
            f"PRAGMA table_info({table})"
        )

        return {
            row["name"]
            for row in rows
        }


def make_repository():
    repository = object.__new__(
        RemediationAuditRepository
    )

    repository.database = TemporaryDatabase()
    repository.initialize()

    return repository


def audit(
    source_type="host",
    source_id="pve01",
    task_id="scheduled_updates",
    decision="ALLOW",
    reason="Host health indicates maintenance is required.",
    evidence=None,
    risk_level="maintenance",
    confirmation_required=False,
    confirmed=False,
    execution_id=42,
    execution_success=True,
    verification_status=None,
    verification_success=None,
    verification_evidence=None,
):
    return {
        "source_type": source_type,
        "source_id": source_id,
        "task_id": task_id,
        "decision": decision,
        "reason": reason,
        "evidence": (
            evidence
            or {
                "hostname": "pve01",
                "status": "WARNING",
            }
        ),
        "risk_level": risk_level,
        "confirmation_required": confirmation_required,
        "confirmed": confirmed,
        "execution_id": execution_id,
        "execution_success": execution_success,
        "verification_status": verification_status,
        "verification_success": verification_success,
        "verification_evidence": verification_evidence,
    }


def test_repository_creates_audit_record():
    repository = make_repository()

    result = repository.save(
        **audit()
    )

    assert result["id"] == 1
    assert result["source_type"] == "host"
    assert result["source_id"] == "pve01"
    assert result["task_id"] == "scheduled_updates"
    assert result["decision"] == "ALLOW"
    assert result["execution_id"] == 42
    assert result["execution_success"] is True


def test_repository_round_trips_evidence():
    repository = make_repository()

    evidence = {
        "hostname": "pve01",
        "status": "WARNING",
        "details": {
            "failed_checks": [
                "disk_space",
                "updates",
            ],
        },
    }

    created = repository.save(
        **audit(
            evidence=evidence
        )
    )

    found = repository.find(
        created["id"]
    )

    assert found["evidence"] == evidence


def test_repository_round_trips_boolean_fields():
    repository = make_repository()

    created = repository.save(
        **audit(
            confirmation_required=True,
            confirmed=True,
            execution_id=None,
            execution_success=None,
        )
    )

    found = repository.find(
        created["id"]
    )

    assert found["confirmation_required"] is True
    assert found["confirmed"] is True
    assert found["execution_id"] is None
    assert found["execution_success"] is None


def test_repository_returns_none_for_unknown_record():
    repository = make_repository()

    assert repository.find(
        999
    ) is None


def test_repository_lists_latest_records_first():
    repository = make_repository()

    repository.save(
        **audit(
            source_id="pve01"
        )
    )

    repository.save(
        **audit(
            source_id="pve02"
        )
    )

    results = repository.history()

    assert [
        result["source_id"]
        for result in results
    ] == [
        "pve02",
        "pve01",
    ]


def test_repository_filters_by_source():
    repository = make_repository()

    repository.save(
        **audit(
            source_id="pve01"
        )
    )

    repository.save(
        **audit(
            source_id="pve02"
        )
    )

    results = repository.history(
        source_type="host",
        source_id="pve01",
    )

    assert len(results) == 1
    assert results[0]["source_id"] == "pve01"


def test_repository_filters_by_decision():
    repository = make_repository()

    repository.save(
        **audit(
            decision="ALLOW"
        )
    )

    repository.save(
        **audit(
            decision="DENY",
            execution_id=None,
            execution_success=None,
        )
    )

    results = repository.history(
        decision="DENY"
    )

    assert len(results) == 1
    assert results[0]["decision"] == "DENY"


def test_repository_respects_history_limit():
    repository = make_repository()

    for source_id in (
        "pve01",
        "pve02",
        "pve03",
    ):
        repository.save(
            **audit(
                source_id=source_id
            )
        )

    results = repository.history(
        limit=2
    )

    assert len(results) == 2
    assert [
        result["source_id"]
        for result in results
    ] == [
        "pve03",
        "pve02",
    ]

def test_repository_summary_is_zero_when_empty():
    repository = make_repository()

    assert repository.summary() == {
        "total": 0,
        "allow_count": 0,
        "deny_count": 0,
        "confirmation_required_count": 0,
        "execution_success_count": 0,
        "execution_failure_count": 0,
        "verification_success_count": 0,
        "verification_failure_count": 0,
        "verification_not_supported_count": 0,
    }


def test_repository_summary_counts_decisions():
    repository = make_repository()

    repository.save(
        **audit(
            decision="ALLOW",
            execution_id=42,
            execution_success=True,
        )
    )

    repository.save(
        **audit(
            decision="DENY",
            execution_id=None,
            execution_success=None,
        )
    )

    repository.save(
        **audit(
            decision="CONFIRM_REQUIRED",
            confirmation_required=True,
            execution_id=None,
            execution_success=None,
        )
    )

    assert repository.summary() == {
        "total": 3,
        "allow_count": 1,
        "deny_count": 1,
        "confirmation_required_count": 1,
        "execution_success_count": 1,
        "execution_failure_count": 0,
        "verification_success_count": 0,
        "verification_failure_count": 0,
        "verification_not_supported_count": 0,
    }


def test_repository_summary_counts_execution_failures():
    repository = make_repository()

    repository.save(
        **audit(
            execution_id=42,
            execution_success=True,
        )
    )

    repository.save(
        **audit(
            source_id="pve02",
            execution_id=43,
            execution_success=False,
        )
    )

    repository.save(
        **audit(
            source_id="pve03",
            decision="DENY",
            execution_id=None,
            execution_success=None,
        )
    )

    assert repository.summary() == {
        "total": 3,
        "allow_count": 2,
        "deny_count": 1,
        "confirmation_required_count": 0,
        "execution_success_count": 1,
        "execution_failure_count": 1,
        "verification_success_count": 0,
        "verification_failure_count": 0,
        "verification_not_supported_count": 0,
    }


def test_repository_round_trips_verification_outcome():
    repository = make_repository()

    verification_evidence = {
        "status": "VERIFIED",
        "success": True,
        "condition": "HOST_UNHEALTHY",
        "reason": "Condition cleared.",
        "evidence": {
            "fresh_health": {
                "hostname": "pve01",
            },
        },
    }

    created = repository.save(
        **audit(
            verification_status="VERIFIED",
            verification_success=True,
            verification_evidence=(
                verification_evidence
            ),
        )
    )

    found = repository.find(
        created["id"]
    )

    assert found[
        "execution_success"
    ] is True

    assert found[
        "verification_status"
    ] == "VERIFIED"

    assert found[
        "verification_success"
    ] is True

    assert found[
        "verification_evidence"
    ] == verification_evidence


def test_repository_preserves_execution_success_when_verification_fails():
    repository = make_repository()

    created = repository.save(
        **audit(
            execution_success=True,
            verification_status=(
                "NOT_VERIFIED"
            ),
            verification_success=False,
            verification_evidence={
                "reason":
                    "Condition remains."
            },
        )
    )

    found = repository.find(
        created["id"]
    )

    assert found[
        "execution_success"
    ] is True

    assert found[
        "verification_success"
    ] is False

    assert found[
        "verification_status"
    ] == "NOT_VERIFIED"


def test_repository_summary_counts_verification_results():
    repository = make_repository()

    repository.save(
        **audit(
            source_id="pve01",
            verification_status="VERIFIED",
            verification_success=True,
        )
    )

    repository.save(
        **audit(
            source_id="pve02",
            verification_status=(
                "NOT_VERIFIED"
            ),
            verification_success=False,
        )
    )

    repository.save(
        **audit(
            source_id="pve03",
            verification_status=(
                "NOT_SUPPORTED"
            ),
            verification_success=False,
        )
    )

    summary = repository.summary()

    assert summary[
        "verification_success_count"
    ] == 1

    assert summary[
        "verification_failure_count"
    ] == 2

    assert summary[
        "verification_not_supported_count"
    ] == 1
