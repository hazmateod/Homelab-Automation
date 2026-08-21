from himp.services.remediation_autonomous_execution import (
    RemediationAutonomousExecutionService,
)


class FakeAutonomy:
    def __init__(
        self,
        decision="ALLOW_AUTOMATIC",
    ):
        self.decision = decision
        self.calls = []

    def evaluate(
        self,
        recommendation,
    ):
        self.calls.append(
            recommendation
        )

        return {
            "decision":
                self.decision,
            "automatic_execution_permitted":
                (
                    self.decision
                    == "ALLOW_AUTOMATIC"
                ),
            "recommendation_id":
                recommendation[
                    "recommendation_id"
                ],
            "condition":
                recommendation[
                    "condition"
                ],
            "task_id":
                "update_host",
            "target_type":
                "host",
            "target_id":
                "pve01",
            "risk_level":
                "maintenance",
            "reason":
                "test policy",
        }


class FakeExecution:
    def __init__(
        self,
        *,
        decision="ALLOW",
        success=True,
    ):
        self.decision = decision
        self.success = success
        self.calls = []

    def execute(
        self,
        proposal,
        confirmed=False,
        limit=None,
    ):
        self.calls.append(
            {
                "proposal": proposal,
                "confirmed": confirmed,
                "limit": limit,
            }
        )

        result = {
            "decision":
                self.decision,
            "policy": {
                "decision":
                    self.decision,
                "task_id":
                    proposal["task_id"],
                "risk_level":
                    "maintenance",
                "confirmation_required":
                    False,
                "reason":
                    proposal["reason"],
                "evidence":
                    proposal["evidence"],
            },
        }

        if self.decision == "ALLOW":
            result["execution"] = {
                "id": 42,
                "task":
                    proposal[
                        "task_id"
                    ],
                "success":
                    self.success,
                "result": {
                    "success":
                        self.success,
                },
            }

        return result


class FakeVerification:
    def __init__(
        self,
        success=True,
        status=None,
    ):
        self.success = success
        self.status = (
            status
            or (
                "VERIFIED"
                if success
                else "NOT_VERIFIED"
            )
        )
        self.calls = []

    def verify(
        self,
        proposal,
        remediation,
    ):
        self.calls.append(
            {
                "proposal": proposal,
                "remediation":
                    remediation,
            }
        )

        return {
            "status":
                self.status,
            "success":
                self.success,
            "hostname":
                "pve01",
            "condition":
                proposal.get(
                    "condition"
                ),
            "reason":
                "test verification",
            "evidence": {},
        }


class FakeAudit:
    def __init__(self):
        self.calls = []

    def record(
        self,
        source_type,
        source_id,
        proposal,
        remediation,
        confirmed=False,
    ):
        self.calls.append(
            {
                "source_type":
                    source_type,
                "source_id":
                    source_id,
                "proposal":
                    proposal,
                "remediation":
                    remediation,
                "confirmed":
                    confirmed,
            }
        )

        return {
            "id": 77,
        }


def recommendation():
    return {
        "recommendation_id":
            "PACKAGE_UPDATES_AVAILABLE:pve01",
        "condition":
            "PACKAGE_UPDATES_AVAILABLE",
        "severity":
            "INFO",
        "target": {
            "entity_type": "host",
            "entity_id": "pve01",
        },
        "evidence": {
            "observation_count": 3,
        },
        "recommended_action":
            "Apply package updates.",
        "rationale":
            "Supported update evidence.",
        "automation": {
            "task_id":
                "update_host",
            "target_type":
                "host",
            "target_id":
                "pve01",
        },
    }


def make_service(
    *,
    autonomy_decision=(
        "ALLOW_AUTOMATIC"
    ),
    execution_decision="ALLOW",
    execution_success=True,
    verification_success=True,
    verification_status=None,
):
    autonomy = FakeAutonomy(
        decision=autonomy_decision
    )

    execution = FakeExecution(
        decision=execution_decision,
        success=execution_success,
    )

    verification = FakeVerification(
        success=verification_success,
        status=verification_status,
    )

    audit = FakeAudit()

    service = (
        RemediationAutonomousExecutionService(
            autonomy=autonomy,
            execution=execution,
            verification=verification,
            audit=audit,
        )
    )

    return (
        service,
        autonomy,
        execution,
        verification,
        audit,
    )


def test_require_approval_never_executes():
    (
        service,
        _,
        execution,
        verification,
        audit,
    ) = make_service(
        autonomy_decision=(
            "REQUIRE_APPROVAL"
        )
    )

    result = service.execute(
        recommendation(),
        source_type="host",
        source_id="pve01",
    )

    assert result["executed"] is False

    assert result["decision"] == (
        "REQUIRE_APPROVAL"
    )

    assert execution.calls == []
    assert verification.calls == []
    assert audit.calls == []


def test_denied_autonomy_never_executes():
    (
        service,
        _,
        execution,
        verification,
        audit,
    ) = make_service(
        autonomy_decision="DENY"
    )

    result = service.execute(
        recommendation(),
        source_type="host",
        source_id="pve01",
    )

    assert result["executed"] is False
    assert result["decision"] == "DENY"

    assert execution.calls == []
    assert verification.calls == []
    assert audit.calls == []


def test_automatic_execution_passes_exact_host_target():
    (
        service,
        _,
        execution,
        verification,
        audit,
    ) = make_service()

    result = service.execute(
        recommendation(),
        source_type="host",
        source_id="pve01",
    )

    assert result["decision"] == (
        "COMPLETED"
    )

    assert result["executed"] is True

    assert len(
        execution.calls
    ) == 1

    call = execution.calls[0]

    assert call["limit"] == "pve01"

    assert call[
        "confirmed"
    ] is False

    assert call[
        "proposal"
    ]["task_id"] == (
        "update_host"
    )

    assert call[
        "proposal"
    ]["condition"] == (
        "PACKAGE_UPDATES_AVAILABLE"
    )

    assert len(
        verification.calls
    ) == 1

    assert len(audit.calls) == 1

    assert result["audit_id"] == 77


def test_execution_policy_block_prevents_automation_closure():
    (
        service,
        _,
        execution,
        verification,
        audit,
    ) = make_service(
        execution_decision="DENY"
    )

    result = service.execute(
        recommendation(),
        source_type="host",
        source_id="pve01",
    )

    assert result["executed"] is False
    assert result["decision"] == "DENY"

    assert len(
        execution.calls
    ) == 1

    assert verification.calls == []

    assert len(audit.calls) == 1


def test_successful_execution_requires_successful_verification():
    (
        service,
        _,
        _,
        verification,
        audit,
    ) = make_service(
        execution_success=True,
        verification_success=False,
        verification_status=(
            "NOT_VERIFIED"
        ),
    )

    result = service.execute(
        recommendation(),
        source_type="host",
        source_id="pve01",
    )

    assert result["executed"] is True
    assert result["decision"] == "FAILED"

    assert result[
        "verification"
    ]["status"] == (
        "NOT_VERIFIED"
    )

    assert len(
        verification.calls
    ) == 1

    assert len(audit.calls) == 1


def test_execution_failure_is_not_reported_as_success():
    (
        service,
        _,
        _,
        verification,
        audit,
    ) = make_service(
        execution_success=False,
        verification_success=False,
        verification_status=(
            "EXECUTION_FAILED"
        ),
    )

    result = service.execute(
        recommendation(),
        source_type="host",
        source_id="pve01",
    )

    assert result["decision"] == "FAILED"

    assert result[
        "remediation"
    ]["execution"][
        "success"
    ] is False

    assert len(
        verification.calls
    ) == 1

    assert len(audit.calls) == 1
