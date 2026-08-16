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
    }
