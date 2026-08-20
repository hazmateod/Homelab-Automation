from himp.models.execution import Execution
from himp.services.automation import AutomationService
from himp.services.health import HealthService


class FakeHealth:
    def __init__(
        self,
        executions,
    ):
        self.executions = executions
        self.all_calls = []

    def all(
        self,
        timeout=None,
    ):
        self.all_calls.append(
            timeout
        )
        return self.executions

    def summary(self):
        raise AssertionError(
            "health_check must execute plugin health, "
            "not read the existing health summary"
        )


class FakeRunner:
    def __init__(
        self,
        executions,
    ):
        self.executions = executions
        self.calls = []

    def health_all(
        self,
        timeout=None,
    ):
        self.calls.append(
            timeout
        )
        return self.executions


def execution(
    plugin,
    success,
    return_code,
):
    return Execution(
        plugin=plugin,
        success=success,
        return_code=return_code,
    )


def test_health_service_all_forwards_timeout_to_runner():
    service = object.__new__(
        HealthService
    )

    expected = [
        execution(
            "infrastructure",
            True,
            0,
        )
    ]

    runner = FakeRunner(
        expected
    )
    service.runner = runner

    result = service.all(
        timeout=300
    )

    assert result is expected
    assert runner.calls == [
        300
    ]


def test_health_check_executes_all_plugin_health():
    service = AutomationService()

    expected = [
        execution(
            "infrastructure",
            True,
            0,
        ),
        execution(
            "proxmox",
            True,
            0,
        ),
    ]

    health = FakeHealth(
        expected
    )
    service.health = health

    result = service._execute_task(
        "health_check",
        timeout=300,
    )

    assert health.all_calls == [
        300
    ]

    assert result == {
        "success": True,
        "executions": expected,
    }


def test_health_check_fails_when_any_plugin_health_fails():
    service = AutomationService()

    executions = [
        execution(
            "infrastructure",
            True,
            0,
        ),
        execution(
            "proxmox",
            False,
            2,
        ),
    ]

    service.health = FakeHealth(
        executions
    )

    result = service._execute_task(
        "health_check",
        timeout=300,
    )

    assert result[
        "success"
    ] is False

    assert result[
        "executions"
    ] == executions


def test_health_check_fails_closed_when_no_health_plugins_execute():
    service = AutomationService()
    service.health = FakeHealth(
        []
    )

    result = service._execute_task(
        "health_check",
        timeout=300,
    )

    assert result == {
        "success": False,
        "executions": [],
    }


def test_health_execution_result_normalizes_plugin_executions():
    raw = {
        "success": True,
        "executions": [
            execution(
                "infrastructure",
                True,
                0,
            ),
        ],
    }

    normalized = (
        AutomationService._normalize_result(
            raw
        )
    )

    assert normalized == {
        "success": True,
        "executions": [
            {
                "plugin": "infrastructure",
                "success": True,
                "return_code": 0,
                "elapsed": 0.0,
                "stdout": "",
                "stderr": "",
                "warnings": [],
                "artifacts": [],
            },
        ],
    }
