from himp.services.inventory import InventoryService


class FakeWriter:
    def __init__(self):
        self.calls = []

    def rename_group(self, group, new_group):
        self.calls.append(
            (group, new_group)
        )

        return {
            "previous_group": group,
            "group": new_group,
        }


class FakeRepository:
    def __init__(self):
        self.saved = []

    def all_hosts(self, include_inactive=False):
        return [
            {
                "hostname": "pve01",
                "group_name": "proxmox",
                "ip": "10.10.37.50",
                "ansible_user": "root",
                "become": 0,
            },
            {
                "hostname": "pve02",
                "group_name": "proxmox",
                "ip": "10.10.37.51",
                "ansible_user": "root",
                "become": 0,
            },
            {
                "hostname": "pbs01",
                "group_name": "backup",
                "ip": "10.10.37.52",
                "ansible_user": "root",
                "become": 0,
            },
        ]

    def save_host(self, host):
        self.saved.append(host)


def make_service():
    service = object.__new__(InventoryService)
    service.writer = FakeWriter()
    service.repository = FakeRepository()
    return service


def test_rename_group_updates_all_matching_hosts():
    service = make_service()

    result = service.rename_group(
        "proxmox",
        "proxmox-production",
    )

    assert result == {
        "previous_group": "proxmox",
        "group": "proxmox-production",
    }

    assert service.writer.calls == [
        ("proxmox", "proxmox-production"),
    ]

    assert service.repository.saved == [
        {
            "hostname": "pve01",
            "group": "proxmox-production",
            "ip": "10.10.37.50",
            "user": "root",
            "become": False,
        },
        {
            "hostname": "pve02",
            "group": "proxmox-production",
            "ip": "10.10.37.51",
            "user": "root",
            "become": False,
        },
    ]


def test_rename_group_does_not_change_other_groups():
    service = make_service()

    service.rename_group(
        "proxmox",
        "proxmox-production",
    )

    assert all(
        host["group"] != "backup"
        for host in service.repository.saved
    )
