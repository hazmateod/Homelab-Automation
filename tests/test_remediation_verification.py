from himp.services.remediation_verification import (
    RemediationVerificationService,
)


class FakeHealthService:
    def __init__(
        self,
        status="PASS",
    ):
        self.status = status
        self.calls = []

    def check_host(
        self,
        hostname,
    ):
        self.calls.append(
            hostname
        )

        return {
            "hostname": hostname,
            "results": [
                {
                    "status": self.status,
                }
            ],
        }


class FakeAnalysisService:
    def __init__(
        self,
        *,
        is_flapping=False,
        available=True,
    ):
        self.is_flapping = (
            is_flapping
        )
        self.available = available
        self.calls = []

    def host(
        self,
        hostname,
        limit=100,
    ):
        self.calls.append(
            {
                "hostname": hostname,
                "limit": limit,
            }
        )

        if not self.available:
            return None

        return {
            "kind": "host",
            "hostname": hostname,
            "limit": limit,
            "analysis": {
                "history_available": True,
                "is_flapping":
                    self.is_flapping,
                "current_status": "PASS",
                "current_state": "HEALTHY",
            },
        }


def allowed_remediation(
    success=True,
):
    return {
        "decision": "ALLOW",
        "execution": {
            "id": 42,
            "success": success,
        },
    }


def denied_remediation():
    return {
        "decision": "DENY",
        "policy": {
            "decision": "DENY",
        },
    }


def host_proposal(
    condition=None,
):
    proposal = {
        "task_id": "scheduled_updates",
        "reason": (
            "Related host pve02 has "
            "failed health."
        ),
        "evidence": {
            "source_type": "host",
            "source_id": "pve01",
            "target_type": "host",
            "target_id": "pve02",
            "health_status": "FAIL",
        },
    }

    if condition is not None:
        proposal["condition"] = (
            condition
        )

    return proposal


def make_service(
    *,
    status="PASS",
    is_flapping=False,
    analysis_available=True,
):
    health = FakeHealthService(
        status=status
    )

    analysis = FakeAnalysisService(
        is_flapping=is_flapping,
        available=analysis_available,
    )

    service = (
        RemediationVerificationService(
            health=health,
            analysis=analysis,
        )
    )

    return service, health, analysis


def test_legacy_host_proposal_with_pass_is_verified():
    service, health, analysis = (
        make_service()
    )

    result = service.verify(
        proposal=host_proposal(),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "VERIFIED"
    )
    assert result["success"] is True
    assert result["hostname"] == "pve02"
    assert (
        result["reason"]
        == "Fresh host health returned PASS."
    )
    assert health.calls == ["pve02"]
    assert analysis.calls == []


def test_legacy_host_proposal_with_failed_health_is_not_verified():
    service, health, analysis = (
        make_service(
            status="FAIL"
        )
    )

    result = service.verify(
        proposal=host_proposal(),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "NOT_VERIFIED"
    )
    assert result["success"] is False
    assert result["hostname"] == "pve02"
    assert health.calls == ["pve02"]
    assert analysis.calls == []


def test_host_unhealthy_pass_confirms_condition_cleared():
    service, health, _ = (
        make_service(
            status="PASS"
        )
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_UNHEALTHY"
        ),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "VERIFIED"
    )
    assert result["success"] is True
    assert result["condition"] == (
        "HOST_UNHEALTHY"
    )
    assert health.calls == ["pve02"]


def test_host_unhealthy_fail_remains_not_verified():
    service, health, _ = (
        make_service(
            status="FAIL"
        )
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_UNHEALTHY"
        ),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "NOT_VERIFIED"
    )
    assert result["success"] is False
    assert result["condition"] == (
        "HOST_UNHEALTHY"
    )
    assert health.calls == ["pve02"]


def test_host_flapping_clears_after_pass_and_non_flapping_analysis():
    (
        service,
        health,
        analysis,
    ) = make_service(
        status="PASS",
        is_flapping=False,
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_FLAPPING"
        ),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "VERIFIED"
    )
    assert result["success"] is True
    assert result["condition"] == (
        "HOST_FLAPPING"
    )

    assert health.calls == [
        "pve02",
    ]

    assert analysis.calls == [
        {
            "hostname": "pve02",
            "limit": 100,
        }
    ]


def test_host_flapping_still_flapping_is_not_verified():
    (
        service,
        _,
        analysis,
    ) = make_service(
        status="PASS",
        is_flapping=True,
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_FLAPPING"
        ),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "NOT_VERIFIED"
    )
    assert result["success"] is False
    assert analysis.calls


def test_host_flapping_without_analysis_is_not_supported():
    service, _, analysis = (
        make_service(
            status="PASS",
            analysis_available=False,
        )
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_FLAPPING"
        ),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "NOT_SUPPORTED"
    )
    assert result["success"] is False
    assert analysis.calls


def test_unknown_condition_is_not_supported():
    service, health, analysis = (
        make_service()
    )

    result = service.verify(
        proposal=host_proposal(
            "UNKNOWN_CONDITION"
        ),
        remediation=allowed_remediation(),
    )

    assert result["status"] == (
        "NOT_SUPPORTED"
    )
    assert result["success"] is False
    assert health.calls == [
        "pve02",
    ]
    assert analysis.calls == []


def test_failed_execution_returns_execution_failed_without_health_check():
    service, health, analysis = (
        make_service()
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_UNHEALTHY"
        ),
        remediation=allowed_remediation(
            success=False
        ),
    )

    assert result["status"] == (
        "EXECUTION_FAILED"
    )
    assert result["success"] is False
    assert health.calls == []
    assert analysis.calls == []


def test_denied_remediation_is_not_executed():
    service, health, analysis = (
        make_service()
    )

    result = service.verify(
        proposal=host_proposal(
            "HOST_UNHEALTHY"
        ),
        remediation=denied_remediation(),
    )

    assert result["status"] == (
        "NOT_EXECUTED"
    )
    assert result["success"] is False
    assert health.calls == []
    assert analysis.calls == []
