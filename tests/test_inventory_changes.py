import sqlite3

from himp.database.inventory import InventoryRepository


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

    def table_columns(self, table_name):
        cursor = self.connection.cursor()
        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )
        return [
            row["name"]
            for row in cursor.fetchall()
        ]


def make_repository():
    repository = object.__new__(InventoryRepository)
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


def test_new_host_records_added_change():
    repository = make_repository()

    repository.save_snapshot([
        host(),
    ])

    changes = repository.changes()

    assert len(changes) == 1
    assert changes[0]["hostname"] == "pve01"
    assert changes[0]["change_type"] == "ADDED"
    assert changes[0]["field"] is None


def test_changed_host_fields_record_updated_changes():
    repository = make_repository()

    repository.save_snapshot([
        host(),
    ])

    repository.save_snapshot([
        host(
            ip="192.168.10.52",
            user="ansible",
            become=True,
        ),
    ])

    changes = repository.changes()

    assert len(changes) == 4

    updated = [
        change
        for change in changes
        if change["change_type"] == "UPDATED"
    ]

    assert len(updated) == 3

    fields = {
        change["field"]: change
        for change in updated
    }

    assert fields["ip"]["old_value"] == "192.168.10.51"
    assert fields["ip"]["new_value"] == "192.168.10.52"

    assert fields["ansible_user"]["old_value"] == "root"
    assert fields["ansible_user"]["new_value"] == "ansible"

    assert fields["become"]["old_value"] == "0"
    assert fields["become"]["new_value"] == "1"



def test_unchanged_snapshot_records_no_duplicate_changes():
    repository = make_repository()

    inventory = [
        host(),
    ]

    repository.save_snapshot(inventory)
    repository.save_snapshot(inventory)

    changes = repository.changes()

    assert len(changes) == 1
    assert changes[0]["change_type"] == "ADDED"


def test_missing_host_records_removed_change():
    repository = make_repository()

    repository.save_snapshot([
        host(),
        host(
            hostname="pve02",
            ip="192.168.10.52",
        ),
    ])

    repository.save_snapshot([
        host(),
    ])

    changes = repository.changes()

    removed = [
        change
        for change in changes
        if change["hostname"] == "pve02"
    ]

    assert len(removed) == 2
    assert [
        change["change_type"]
        for change in removed
    ] == [
        "REMOVED",
        "ADDED",
    ]


def test_removed_host_returning_records_restored_change():
    repository = make_repository()

    repository.save_snapshot([
        host(),
    ])

    repository.save_snapshot([])

    repository.save_snapshot([
        host(),
    ])

    changes = repository.changes()

    assert [
        change["change_type"]
        for change in changes
    ] == [
        "RESTORED",
        "REMOVED",
        "ADDED",
    ]
