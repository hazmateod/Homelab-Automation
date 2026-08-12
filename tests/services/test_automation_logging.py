import logging

from himp.services.automation import AutomationService


def test_automation_run_emits_execution_started_log():
    service = AutomationService()

    service.tasks = [
        {
            "id": "health_check",
            "name": "Health Check",
            "enabled": True,
            "risk_level": "safe",
            "requires_confirmation": False,
            "retry_attempts": 1,
            "retry_delay_seconds": 0,
            "timeout_seconds": 30,
        }
    ]

    service._execute_task = (
        lambda task_id, limit=None, timeout=None: {
            "success": True,
            "message": "healthy",
        }
    )

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.automation")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        service.run("health_check")
    finally:
        logger.removeHandler(handler)

    assert any(
        record.name == "himp.automation"
        and record.message
        == "Automation execution started: health_check"
        for record in records
    )


def test_automation_run_emits_classified_failure_log():
    service = AutomationService()

    service.tasks = [
        {
            "id": "health_check",
            "name": "Health Check",
            "enabled": True,
            "risk_level": "safe",
            "requires_confirmation": False,
            "retry_attempts": 1,
            "retry_delay_seconds": 0,
            "timeout_seconds": 30,
        }
    ]

    def fail_task(task_id, limit=None, timeout=None):
        raise TimeoutError("simulated timeout")

    service._execute_task = fail_task

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.automation")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        try:
            service.run("health_check")
        except TimeoutError:
            pass
    finally:
        logger.removeHandler(handler)

    assert any(
        record.name == "himp.automation"
        and record.message
        == "Automation execution failed: health_check"
        and record.attempt == 1
        and record.attempts == 1
        and record.error_category == "timeout"
        and record.retryable is True
        for record in records
    )


def test_automation_run_emits_retry_log():
    service = AutomationService()

    service.tasks = [
        {
            "id": "health_check",
            "name": "Health Check",
            "enabled": True,
            "risk_level": "safe",
            "requires_confirmation": False,
            "retry_attempts": 2,
            "retry_delay_seconds": 0,
            "timeout_seconds": 30,
        }
    ]

    calls = []

    def task_with_retry(task_id, limit=None, timeout=None):
        calls.append(task_id)

        if len(calls) == 1:
            raise TimeoutError("simulated timeout")

        return {
            "success": True,
            "message": "healthy",
        }

    service._execute_task = task_with_retry

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.automation")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        result = service.run("health_check")
    finally:
        logger.removeHandler(handler)

    assert result["result"]["success"] is True

    assert any(
        record.name == "himp.automation"
        and record.message
        == "Automation execution retrying: health_check"
        and record.attempt == 1
        and record.next_attempt == 2
        and record.error_category == "timeout"
        for record in records
    )


def test_automation_run_emits_retry_log_for_failed_result():
    service = AutomationService()

    service.tasks = [
        {
            "id": "health_check",
            "name": "Health Check",
            "enabled": True,
            "risk_level": "safe",
            "requires_confirmation": False,
            "retry_attempts": 2,
            "retry_delay_seconds": 0,
            "timeout_seconds": 30,
        }
    ]

    calls = []

    def failed_then_success(task_id, limit=None, timeout=None):
        calls.append(task_id)

        if len(calls) == 1:
            return {
                "success": False,
                "message": "temporary failure",
            }

        return {
            "success": True,
            "message": "recovered",
        }

    service._execute_task = failed_then_success

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.automation")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        result = service.run("health_check")
    finally:
        logger.removeHandler(handler)

    assert result["result"]["success"] is True

    assert any(
        record.name == "himp.automation"
        and record.message
        == "Automation execution retrying: health_check"
        and record.attempt == 1
        and record.next_attempt == 2
        and record.error_category == "result"
        for record in records
    )
