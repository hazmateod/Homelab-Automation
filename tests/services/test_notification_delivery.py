from himp.services.notification_delivery import (
    NotificationDeliveryService,
)


class FakeRepository:
    def __init__(self):
        self.records = []

    def record(
        self,
        **record,
    ):
        record = {
            "id": len(self.records) + 1,
            **record,
        }

        self.records.append(record)
        return record


class FakeTransport:
    destination_type = "DISCORD"
    destination_name = "DEFAULT"

    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = (
            result
            if result is not None
            else {
                "status": "SUCCESS",
                "status_code": 204,
                "error": None,
            }
        )
        self.error = error
        self.calls = []

    def send(
        self,
        notification,
    ):
        self.calls.append(notification)

        if self.error is not None:
            raise self.error

        return self.result


def notification(
    routing_decision="ROUTE",
):
    return {
        "id": 42,
        "routing_decision": routing_decision,
        "logical_destinations": [
            "DEFAULT",
        ],
    }


def test_delivery_records_success():
    repository = FakeRepository()
    transport = FakeTransport()

    service = NotificationDeliveryService(
        repository=repository,
        transports=[transport],
    )

    result = service.deliver(
        notification()
    )

    assert len(result) == 1
    assert result[0]["status"] == "SUCCESS"
    assert result[0]["status_code"] == 204
    assert len(transport.calls) == 1


def test_delivery_does_not_send_suppressed_notification():
    repository = FakeRepository()
    transport = FakeTransport()

    service = NotificationDeliveryService(
        repository=repository,
        transports=[transport],
    )

    result = service.deliver(
        notification(
            routing_decision="SUPPRESS"
        )
    )

    assert result == []
    assert transport.calls == []
    assert repository.records == []


def test_transport_failure_is_recorded_not_raised():
    repository = FakeRepository()

    transport = FakeTransport(
        error=RuntimeError(
            "sensitive secret should not leak"
        )
    )

    service = NotificationDeliveryService(
        repository=repository,
        transports=[transport],
    )

    result = service.deliver(
        notification()
    )

    assert result[0]["status"] == "FAILED"
    assert (
        result[0]["error"]
        == "Unexpected transport failure: RuntimeError"
    )
    assert (
        "sensitive secret"
        not in result[0]["error"]
    )
