import sqlite3

from himp.database.inventory_baseline import (
    InventoryBaselineRepository,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def query(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        return cursor.fetchall()


def make_repository():
    repository = object.__new__(
        InventoryBaselineRepository
    )
    repository.database = TemporaryDatabase()
    repository.initialize()
    return repository


def host(
    hostname="pve01",
    group="proxmox",
    ip="192.168.10.51",
    user="root",
    become=False,
):
    return {
        "hostname": hostname,
        "group": group,
        "ip": ip,
        "user": user,
        "become": become,
    }


def test_repository_creates_and_finds_baseline():
    repository = make_repository()

    repository.create(
        "production",
        [
            host(),
        ],
    )

    baseline = repository.find(
        "production"
    )

    assert baseline["name"] == "production"
    assert baseline["hosts"] == [
        host(),
    ]


def test_repository_returns_none_for_missing_baseline():
    repository = make_repository()

    assert repository.find(
        "missing"
    ) is None


def test_repository_lists_baselines_deterministically():
    repository = make_repository()

    repository.create(
        "production",
        [host()],
    )

    repository.create(
        "development",
        [
            host(
                hostname="dev01",
                ip="192.168.60.10",
            ),
        ],
    )

    baselines = repository.list()

    assert [
        baseline["name"]
        for baseline in baselines
    ] == [
        "development",
        "production",
    ]


def test_repository_rejects_duplicate_baseline():
    repository = make_repository()

    repository.create(
        "production",
        [host()],
    )

    try:
        repository.create(
            "production",
            [host()],
        )
    except ValueError as error:
        assert str(error) == (
            "Inventory baseline already exists: production"
        )
    else:
        raise AssertionError(
            "Expected duplicate baseline to raise ValueError"
        )
