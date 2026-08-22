from himp.services.storage_capacity import (
    StorageCapacityService,
)


class FakeInventory:
    def all_hosts(self):
        return [
            {
                "hostname": "host01",
            }
        ]


class FakeCollector:
    def __init__(
        self,
        results,
    ):
        self.results = results

    def collect(
        self,
        timeout=None,
    ):
        return self.results


class FakeRepository:
    def __init__(self):
        self.status = None

    def save(
        self,
        record,
    ):
        previous = self.status
        self.status = record["status"]

        return {
            "previous_status": previous,
            "current_status": self.status,
            "transition": (
                previous != self.status
                and (
                    previous is not None
                    or self.status in {
                        "WARNING",
                        "CRITICAL",
                    }
                )
            ),
        }


class FakeNotifications:
    def __init__(self):
        self.transitions = []

    def storage_transition(
        self,
        transition,
    ):
        self.transitions.append(
            dict(transition)
        )


def host_result(percent):
    return {
        "hostname": "host01",
        "stdout_lines": [
            (
                "Filesystem 1B-blocks Used "
                "Available Use% Mounted on"
            ),
            (
                "/dev/sda1 100 "
                f"{percent} "
                f"{100-percent} "
                f"{percent}% /"
            ),
        ],
    }


def test_storage_threshold_transition_emits_notification():
    repository = FakeRepository()
    notifications = FakeNotifications()

    service = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(82),
            ]
        ),
        notifications=notifications,
    )

    result = service.collect_all()

    assert len(result["transitions"]) == 1
    assert len(notifications.transitions) == 1
    assert (
        notifications.transitions[0][
            "current_status"
        ]
        == "WARNING"
    )


def test_storage_steady_state_does_not_emit_duplicate_event():
    repository = FakeRepository()
    notifications = FakeNotifications()

    first = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(82),
            ]
        ),
        notifications=notifications,
    )

    second = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(82),
            ]
        ),
        notifications=notifications,
    )

    first.collect_all()
    second.collect_all()

    assert len(notifications.transitions) == 1


def test_storage_recovery_emits_notification():
    repository = FakeRepository()
    notifications = FakeNotifications()

    StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(93),
            ]
        ),
        notifications=notifications,
    ).collect_all()

    StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(60),
            ]
        ),
        notifications=notifications,
    ).collect_all()

    assert [
        item["current_status"]
        for item in notifications.transitions
    ] == [
        "CRITICAL",
        "PASS",
    ]
