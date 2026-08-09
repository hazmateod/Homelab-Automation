"""
Inventory File Writer.

Provides controlled changes to the Ansible inventory file
while preserving existing formatting and comments.
"""

from pathlib import Path
import re

import yaml

from himp.config import config


class InventoryFileWriter:
    """
    Writes controlled changes to the Ansible inventory.
    """

    def __init__(self, filename=None):
        self.filename = Path(
            filename or config.inventory
        )

    def _read(self):
        return self.filename.read_text()

    def _load(self, content):
        return yaml.safe_load(content) or {}

    def _children(self, inventory):
        return (
            inventory
            .get("all", {})
            .get("children", {})
        )

    def _find_group_hosts_block(
        self,
        content,
        group,
    ):
        lines = content.splitlines(keepends=True)

        group_pattern = re.compile(
            rf"^    {re.escape(group)}:\s*$"
        )

        group_index = None

        for index, line in enumerate(lines):
            if group_pattern.match(line):
                group_index = index
                break

        if group_index is None:
            raise ValueError(
                f"Inventory group does not exist: {group}"
            )

        hosts_index = None

        for index in range(
            group_index + 1,
            len(lines),
        ):
            line = lines[index]

            if line.startswith("    ") and not line.startswith("      "):
                break

            if line == "      hosts:\n":
                hosts_index = index
                break

            if line == "      hosts:":
                hosts_index = index
                break

        if hosts_index is None:
            raise ValueError(
                f"Inventory group cannot contain hosts: {group}"
            )

        first_host_index = hosts_index + 1

        while (
            first_host_index < len(lines)
            and lines[first_host_index].strip() == ""
        ):
            first_host_index += 1

        block_end = first_host_index

        while block_end < len(lines):
            line = lines[block_end]

            if line.startswith("        "):
                block_end += 1
                continue

            if line.strip() == "":
                block_end += 1
                continue

            break

        return (
            lines,
            hosts_index,
            first_host_index,
            block_end,
        )

    def _find_host_block(
        self,
        content,
        hostname,
    ):
        lines = content.splitlines(keepends=True)

        host_pattern = re.compile(
            rf"^        {re.escape(hostname)}:\s*$"
        )

        host_index = None

        for index, line in enumerate(lines):
            if host_pattern.match(line):
                host_index = index
                break

        if host_index is None:
            raise ValueError(
                f"Inventory host does not exist: {hostname}"
            )

        block_end = host_index + 1

        while block_end < len(lines):
            line = lines[block_end]

            if line.startswith("          "):
                block_end += 1
                continue

            break

        return (
            lines,
            host_index,
            block_end,
        )

    def _host_lines(
        self,
        hostname,
        ip,
        user,
        become,
    ):
        lines = [
            f"        {hostname}:\n",
            f"          ansible_host: {ip}\n",
            f"          ansible_user: {user}\n",
        ]

        if become:
            lines.append(
                "          ansible_become: true\n"
            )

        return lines

    def _insert_host(
        self,
        content,
        group,
        host_lines,
    ):
        (
            lines,
            hosts_index,
            first_host_index,
            block_end,
        ) = self._find_group_hosts_block(
            content,
            group,
        )

        if first_host_index == block_end:
            insertion_index = hosts_index + 1
        else:
            insertion_index = block_end

            while (
                insertion_index > first_host_index
                and lines[insertion_index - 1].strip() == ""
            ):
                insertion_index -= 1

        lines[insertion_index:insertion_index] = host_lines

        return "".join(lines)

    def add_host(
        self,
        hostname,
        group,
        ip,
        user,
        become=False,
    ):
        content = self._read()

        inventory = self._load(content)

        children = self._children(inventory)

        if group not in children:
            raise ValueError(
                f"Inventory group does not exist: {group}"
            )

        group_data = children[group]

        if "hosts" not in group_data:
            raise ValueError(
                f"Inventory group cannot contain hosts: {group}"
            )

        hosts = group_data["hosts"]

        if hostname in hosts:
            raise ValueError(
                f"Inventory host already exists: {hostname}"
            )

        host_lines = self._host_lines(
            hostname=hostname,
            ip=ip,
            user=user,
            become=become,
        )

        updated = self._insert_host(
            content,
            group,
            host_lines,
        )

        yaml.safe_load(updated)

        self.filename.write_text(updated)

        return {
            "hostname": hostname,
            "group": group,
            "ip": ip,
            "user": user,
            "become": bool(become),
        }

    def update_host(
        self,
        hostname,
        group,
        ip,
        user,
        become=False,
    ):
        content = self._read()

        inventory = self._load(content)

        children = self._children(inventory)

        if group not in children:
            raise ValueError(
                f"Inventory group does not exist: {group}"
            )

        group_data = children[group]

        if "hosts" not in group_data:
            raise ValueError(
                f"Inventory group cannot contain hosts: {group}"
            )

        existing_group = None

        for group_name, data in children.items():
            hosts = data.get("hosts")

            if hosts and hostname in hosts:
                existing_group = group_name
                break

        if existing_group is None:
            raise ValueError(
                f"Inventory host does not exist: {hostname}"
            )

        (
            lines,
            host_index,
            block_end,
        ) = self._find_host_block(
            content,
            hostname,
        )

        del lines[host_index:block_end]

        updated = "".join(lines)

        host_lines = self._host_lines(
            hostname=hostname,
            ip=ip,
            user=user,
            become=become,
        )

        updated = self._insert_host(
            updated,
            group,
            host_lines,
        )

        yaml.safe_load(updated)

        self.filename.write_text(updated)

        return {
            "hostname": hostname,
            "group": group,
            "ip": ip,
            "user": user,
            "become": bool(become),
            "previous_group": existing_group,
        }

    def restore_host(
        self,
        hostname,
        group,
        ip,
        user,
        become=False,
    ):
        content = self._read()

        inventory = self._load(content)

        children = self._children(inventory)

        if group not in children:
            raise ValueError(
                f"Inventory group does not exist: {group}"
            )

        group_data = children[group]

        if "hosts" not in group_data:
            raise ValueError(
                f"Inventory group cannot contain hosts: {group}"
            )

        hosts = group_data["hosts"]

        if hosts and hostname in hosts:
            raise ValueError(
                f"Inventory host already exists: {hostname}"
            )

        host_lines = self._host_lines(
            hostname=hostname,
            ip=ip,
            user=user,
            become=become,
        )

        updated = self._insert_host(
            content,
            group,
            host_lines,
        )

        yaml.safe_load(updated)

        self.filename.write_text(updated)

        return {
            "hostname": hostname,
            "group": group,
            "ip": ip,
            "user": user,
            "become": bool(become),
        }

    def remove_host(
        self,
        hostname,
    ):
        content = self._read()

        inventory = self._load(content)

        children = self._children(inventory)

        existing_group = None

        for group_name, data in children.items():
            hosts = data.get("hosts")

            if hosts and hostname in hosts:
                existing_group = group_name
                break

        if existing_group is None:
            raise ValueError(
                f"Inventory host does not exist: {hostname}"
            )

        (
            lines,
            host_index,
            block_end,
        ) = self._find_host_block(
            content,
            hostname,
        )

        del lines[host_index:block_end]

        updated = "".join(lines)

        yaml.safe_load(updated)

        self.filename.write_text(updated)

        return {
            "hostname": hostname,
            "group": existing_group,
        }
