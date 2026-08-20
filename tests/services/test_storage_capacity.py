from himp.services.storage_capacity import (
    StorageCapacityService,
)


class FakeInventory:

    def __init__(self):
        self.hosts = [
            {"hostname": "host01"},
            {"hostname": "host02"},
        ]

    def all_hosts(self):
        return self.hosts

    def find_host(
        self,
        hostname,
    ):
        for host in self.hosts:
            if host["hostname"] == hostname:
                return host

        return None


class FakeCollector:

    def __init__(
        self,
        hosts,
    ):
        self.hosts = hosts
        self.timeouts = []

    def collect(
        self,
        timeout=None,
    ):
        self.timeouts.append(
            timeout
        )
        return self.hosts


class FakeRepository:

    def __init__(self):
        self.records = []
        self.events = []

    def latest(
        self,
        hostname,
        mount_point,
    ):
        matching = [
            record
            for record in self.records
            if (
                record["hostname"] == hostname
                and record["mount_point"] == mount_point
            )
        ]

        return (
            dict(matching[-1])
            if matching
            else None
        )

    def save(
        self,
        record,
    ):
        previous = self.latest(
            record["hostname"],
            record["mount_point"],
        )

        previous_status = (
            previous["status"]
            if previous
            else None
        )

        self.records.append(
            dict(record)
        )

        transition = (
            previous_status != record["status"]
            and (
                previous_status is not None
                or record["status"] in (
                    "WARNING",
                    "CRITICAL",
                )
            )
        )

        if transition:
            self.events.append(
                {
                    "hostname": record["hostname"],
                    "mount_point": record["mount_point"],
                    "previous_status": previous_status,
                    "current_status": record["status"],
                }
            )

        return {
            "previous_status": previous_status,
            "current_status": record["status"],
            "transition": transition,
        }

    def current_host(
        self,
        hostname,
    ):
        latest = {}

        for record in self.records:
            if record["hostname"] == hostname:
                latest[
                    record["mount_point"]
                ] = record

        return list(
            latest.values()
        )

    def current_all(self):
        latest = {}

        for record in self.records:
            latest[
                (
                    record["hostname"],
                    record["mount_point"],
                )
            ] = record

        return list(
            latest.values()
        )

    def alert_events(
        self,
        hostname=None,
        limit=100,
    ):
        events = self.events

        if hostname is not None:
            events = [
                event
                for event in events
                if event["hostname"] == hostname
            ]

        return events[-limit:]


def host_result(
    percent,
):
    used = int(
        100_000_000_000
        * percent
        / 100
    )

    available = (
        100_000_000_000
        - used
    )

    return {
        "hostname": "host01",
        "return_code": 0,
        "stdout_lines": [
            (
                "Filesystem 1B-blocks Used "
                "Available Use% Mounted on"
            ),
            (
                "/dev/sda1 "
                "100000000000 "
                f"{used} "
                f"{available} "
                f"{percent}% /"
            ),
        ],
        "stderr": "",
    }


def test_storage_threshold_contract():
    assert (
        StorageCapacityService.status_for(
            79.9
        )
        == "PASS"
    )

    assert (
        StorageCapacityService.status_for(
            80
        )
        == "WARNING"
    )

    assert (
        StorageCapacityService.status_for(
            89.9
        )
        == "WARNING"
    )

    assert (
        StorageCapacityService.status_for(
            90
        )
        == "CRITICAL"
    )

    assert (
        StorageCapacityService.status_for(
            100
        )
        == "CRITICAL"
    )


def test_collect_all_persists_normalized_filesystems():
    repository = FakeRepository()

    collector = FakeCollector(
        [
            host_result(80),
        ]
    )

    service = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=collector,
    )

    result = service.collect_all(
        timeout=300
    )

    assert collector.timeouts == [
        300
    ]

    assert result["success"] is True
    assert result["hosts"] == 1
    assert result["filesystems"] == 1
    assert result["warning"] == 1
    assert result["critical"] == 0

    record = repository.records[0]

    assert record["hostname"] == "host01"
    assert record["filesystem"] == "/dev/sda1"
    assert record["mount_point"] == "/"
    assert record["used_percent"] == 80.0
    assert record["status"] == "WARNING"


def test_first_threshold_breach_creates_transition():
    repository = FakeRepository()

    service = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(90),
            ]
        ),
    )

    result = service.collect_all()

    assert len(
        result["transitions"]
    ) == 1

    transition = result[
        "transitions"
    ][0]

    assert (
        transition["previous_status"]
        is None
    )

    assert (
        transition["current_status"]
        == "CRITICAL"
    )


def test_pass_to_warning_transition_is_stateful():
    repository = FakeRepository()

    first = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(70),
            ]
        ),
    )

    second = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector(
            [
                host_result(82),
            ]
        ),
    )

    assert (
        first.collect_all()[
            "transitions"
        ]
        == []
    )

    transitions = (
        second.collect_all()[
            "transitions"
        ]
    )

    assert len(transitions) == 1

    assert (
        transitions[0][
            "previous_status"
        ]
        == "PASS"
    )

    assert (
        transitions[0][
            "current_status"
        ]
        == "WARNING"
    )


def test_storage_host_summary_reports_worst_filesystem():
    repository = FakeRepository()

    for percent, mount_point in (
        (45.0, "/"),
        (92.0, "/data"),
    ):
        repository.save(
            {
                "hostname": "host01",
                "filesystem": "/dev/test",
                "mount_point": mount_point,
                "total_bytes": 100,
                "used_bytes": int(percent),
                "available_bytes": (
                    100
                    - int(percent)
                ),
                "used_percent": percent,
                "status": (
                    StorageCapacityService.status_for(
                        percent
                    )
                ),
            }
        )

    service = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector([]),
    )

    host = service.host(
        "host01"
    )

    assert host["status"] == "CRITICAL"

    assert (
        host["highest_used_percent"]
        == 92.0
    )

    assert len(
        host["filesystems"]
    ) == 2


def test_storage_summary_includes_unknown_inventory_hosts():
    repository = FakeRepository()

    repository.save(
        {
            "hostname": "host01",
            "filesystem": "/dev/sda1",
            "mount_point": "/",
            "total_bytes": 100,
            "used_bytes": 50,
            "available_bytes": 50,
            "used_percent": 50.0,
            "status": "PASS",
        }
    )

    service = StorageCapacityService(
        repository=repository,
        inventory=FakeInventory(),
        collector=FakeCollector([]),
    )

    result = service.summary()

    host_map = {
        host["hostname"]: host
        for host in result["hosts"]
    }

    assert (
        host_map["host01"]["status"]
        == "PASS"
    )

    assert (
        host_map["host02"]["status"]
        == "UNKNOWN"
    )

    assert (
        result["unknown_hosts"]
        == 1
    )


def test_storage_parser_preserves_values_larger_than_postgresql_int32():
    host = {
        "hostname": "media01",
        "return_code": 0,
        "stdout_lines": [
            (
                "Filesystem 1B-blocks Used "
                "Available Use% Mounted on"
            ),
            (
                "//nas/Movies "
                "13669205696512 "
                "9974183948288 "
                "3695021748224 "
                "73% /media/Movies"
            ),
        ],
        "stderr": "",
    }

    records = (
        StorageCapacityService._parse_host(
            host
        )
    )

    assert len(records) == 1

    record = records[0]

    assert (
        record["total_bytes"]
        == 13669205696512
    )

    assert (
        record["used_bytes"]
        == 9974183948288
    )

    assert (
        record["available_bytes"]
        == 3695021748224
    )

    assert (
        record["total_bytes"]
        > 2_147_483_647
    )

    assert record["used_percent"] == 73.0
