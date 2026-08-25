#!/opt/himp-greenbone/venv/bin/python

import argparse
import os
import sys
from pathlib import Path

from gvm.connections import UnixSocketConnection
from gvm.errors import GvmError
from gvm.protocols.gmp import GMP
from gvm.transforms import EtreeCheckCommandTransform
from gvm.protocols.gmp.requests.v224._targets import AliveTest


SOCKET = (
    "/var/lib/docker/volumes/"
    "greenbone-community-edition_gvmd_socket_vol/"
    "_data/gvmd.sock"
)
CREDENTIAL_FILE = Path(
    "/etc/himp-greenbone/gmp.env"
)


def load_credentials():
    if not CREDENTIAL_FILE.is_file():
        raise RuntimeError(
            "Greenbone credential file is missing"
        )

    values = {}

    for raw_line in CREDENTIAL_FILE.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    username = values.get("GMP_USERNAME")
    password = values.get("GMP_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "Greenbone credentials are incomplete"
        )

    return username, password


def text_value(element, path, default="-"):
    found = element.find(path)

    if found is None or found.text is None:
        return default

    value = found.text.strip()

    return value or default


def command_status(gmp):
    version_response = gmp.get_version()

    version = text_value(
        version_response,
        "version",
    )

    authenticated = gmp.is_authenticated()

    print("GREENBONE_GMP=OK")
    print(f"GMP_VERSION={version}")
    print(
        "AUTHENTICATED="
        + ("YES" if authenticated else "NO")
    )


def command_targets(gmp):
    response = gmp.get_targets(
        filter_string="rows=-1"
    )

    targets = response.xpath("target")

    print(f"TARGET_COUNT={len(targets)}")

    for target in targets:
        target_id = target.get("id", "-")
        name = text_value(target, "name")
        hosts = text_value(target, "hosts")

        print(
            f"{target_id}\t{name}\t{hosts}"
        )


def command_tasks(gmp):
    response = gmp.get_tasks(
        filter_string="rows=-1",
        details=True,
    )

    tasks = response.xpath("task")

    print(f"TASK_COUNT={len(tasks)}")

    for task in tasks:
        task_id = task.get("id", "-")
        name = text_value(task, "name")
        status = text_value(task, "status")
        target = text_value(task, "target/name")

        print(
            f"{task_id}\t"
            f"{name}\t"
            f"{status}\t"
            f"{target}"
        )


def command_capabilities(gmp):
    configs_response = gmp.get_scan_configs(
        filter_string="rows=-1"
    )

    scanners_response = gmp.get_scanners(
        filter_string="rows=-1"
    )

    port_lists_response = gmp.get_port_lists(
        filter_string="rows=-1"
    )

    configs = configs_response.xpath("config")
    scanners = scanners_response.xpath("scanner")
    port_lists = port_lists_response.xpath("port_list")

    print(f"SCAN_CONFIG_COUNT={len(configs)}")

    found_full_and_fast = False

    for config in configs:
        config_id = config.get("id", "-")
        name = text_value(config, "name")

        print(
            f"CONFIG\t{config_id}\t{name}"
        )

        if name == "Full and fast":
            found_full_and_fast = True

    print(f"SCANNER_COUNT={len(scanners)}")

    found_openvas = False

    for scanner in scanners:
        scanner_id = scanner.get("id", "-")
        name = text_value(scanner, "name")

        print(
            f"SCANNER\t{scanner_id}\t{name}"
        )

        if name == "OpenVAS Default":
            found_openvas = True

    print(f"PORT_LIST_COUNT={len(port_lists)}")

    found_port_list = False

    for port_list in port_lists:
        port_list_id = port_list.get("id", "-")
        name = text_value(port_list, "name")

        print(
            f"PORT_LIST\t{port_list_id}\t{name}"
        )

        if name == "All TCP and Nmap top 100 UDP":
            found_port_list = True

    print()
    print(
        "FULL_AND_FAST="
        + ("VISIBLE" if found_full_and_fast else "MISSING")
    )
    print(
        "OPENVAS_DEFAULT="
        + ("VISIBLE" if found_openvas else "MISSING")
    )
    print(
        "FULL_TCP_TOP100_UDP="
        + ("VISIBLE" if found_port_list else "MISSING")
    )

    if not all(
        (
            found_full_and_fast,
            found_openvas,
            found_port_list,
        )
    ):
        raise RuntimeError(
            "Required Greenbone shared resources are not visible"
        )


def command_pilot_target(gmp):
    pilot_name = "HIMP Pilot - unbound107"
    pilot_host = "10.10.37.7"

    port_list_name = (
        "All TCP and Nmap top 100 UDP"
    )

    targets_response = gmp.get_targets(
        filter_string="rows=-1"
    )

    existing = []

    for target in targets_response.xpath("target"):
        name = text_value(target, "name")

        if name == pilot_name:
            existing.append(target)

    if len(existing) > 1:
        raise RuntimeError(
            "Multiple pilot targets already exist"
        )

    if existing:
        target = existing[0]
        target_id = target.get("id", "-")
        hosts = text_value(target, "hosts")

        print("PILOT_TARGET=EXISTS")
        print(f"TARGET_ID={target_id}")
        print(f"TARGET_NAME={pilot_name}")
        print(f"TARGET_HOSTS={hosts}")

        if pilot_host not in {
            item.strip()
            for item in hosts.split(",")
        }:
            raise RuntimeError(
                "Existing pilot target has unexpected hosts"
            )

        return

    port_lists_response = gmp.get_port_lists(
        filter_string="rows=-1"
    )

    matches = []

    for port_list in port_lists_response.xpath(
        "port_list"
    ):
        name = text_value(
            port_list,
            "name",
        )

        if name == port_list_name:
            matches.append(port_list)

    if len(matches) != 1:
        raise RuntimeError(
            "Required port list was not uniquely resolved"
        )

    port_list_id = matches[0].get("id")

    if not port_list_id:
        raise RuntimeError(
            "Required port list has no UUID"
        )

    response = gmp.create_target(
        pilot_name,
        hosts=[pilot_host],
        comment=(
            "HIMP Phase 16.3.1 controlled pilot target. "
            "No scan task is created by this command."
        ),
        port_list_id=port_list_id,
    )

    target_id = response.get("id")

    if not target_id:
        raise RuntimeError(
            "Greenbone did not return a target UUID"
        )

    print("PILOT_TARGET=CREATED")
    print(f"TARGET_ID={target_id}")
    print(f"TARGET_NAME={pilot_name}")
    print(f"TARGET_HOSTS={pilot_host}")
    print(f"PORT_LIST={port_list_name}")


def command_pilot_task(gmp):
    task_name = (
        "HIMP Pilot - unbound107 - Full and Fast"
    )

    target_name = "HIMP Pilot - unbound107"
    config_name = "Full and fast"
    scanner_name = "OpenVAS Default"

    tasks_response = gmp.get_tasks(
        filter_string="rows=-1",
        details=True,
    )

    matches = []

    for task in tasks_response.xpath("task"):
        name = text_value(task, "name")

        if name == task_name:
            matches.append(task)

    if len(matches) > 1:
        raise RuntimeError(
            "Multiple pilot tasks already exist"
        )

    if matches:
        task = matches[0]

        print("PILOT_TASK=EXISTS")
        print(
            "TASK_ID="
            + task.get("id", "-")
        )
        print(
            "TASK_NAME="
            + task_name
        )
        print(
            "TARGET="
            + text_value(
                task,
                "target/name",
            )
        )
        print(
            "STATUS="
            + text_value(
                task,
                "status",
            )
        )

        return

    targets_response = gmp.get_targets(
        filter_string="rows=-1"
    )

    target_matches = [
        target
        for target in targets_response.xpath("target")
        if text_value(target, "name") == target_name
    ]

    if len(target_matches) != 1:
        raise RuntimeError(
            "Pilot target was not uniquely resolved"
        )

    target_id = target_matches[0].get("id")

    configs_response = gmp.get_scan_configs(
        filter_string="rows=-1"
    )

    config_matches = [
        config
        for config in configs_response.xpath("config")
        if text_value(config, "name") == config_name
    ]

    if len(config_matches) != 1:
        raise RuntimeError(
            "Full and fast config was not uniquely resolved"
        )

    config_id = config_matches[0].get("id")

    scanners_response = gmp.get_scanners(
        filter_string="rows=-1"
    )

    scanner_matches = [
        scanner
        for scanner in scanners_response.xpath("scanner")
        if text_value(scanner, "name") == scanner_name
    ]

    if len(scanner_matches) != 1:
        raise RuntimeError(
            "OpenVAS Default scanner was not uniquely resolved"
        )

    scanner_id = scanner_matches[0].get("id")

    if not all(
        (
            target_id,
            config_id,
            scanner_id,
        )
    ):
        raise RuntimeError(
            "Required Greenbone UUID is missing"
        )

    response = gmp.create_task(
        task_name,
        config_id,
        target_id,
        scanner_id,
        comment=(
            "HIMP Phase 16.3.1 controlled pilot task. "
            "This command does not start the scan."
        ),
    )

    task_id = response.get("id")

    if not task_id:
        raise RuntimeError(
            "Greenbone did not return a task UUID"
        )

    print("PILOT_TASK=CREATED")
    print(f"TASK_ID={task_id}")
    print(f"TASK_NAME={task_name}")
    print(f"TARGET={target_name}")
    print(f"CONFIG={config_name}")
    print(f"SCANNER={scanner_name}")
    print("SCAN_STARTED=NO")


def command_pilot_start(gmp):
    task_id = "b37162e2-40b3-4a73-8f5e-672d766c93be"

    expected_task_name = (
        "HIMP Pilot - unbound107 - Full and Fast"
    )
    expected_target_name = (
        "HIMP Pilot - unbound107"
    )

    response = gmp.get_task(task_id)

    task = response.find("task")

    if task is None:
        raise RuntimeError(
            "Pilot task was not returned by Greenbone"
        )

    task_name = text_value(
        task,
        "name",
    )

    target_name = text_value(
        task,
        "target/name",
    )

    status = text_value(
        task,
        "status",
    )

    if task_name != expected_task_name:
        raise RuntimeError(
            "Pilot task name does not match expected contract"
        )

    if target_name != expected_target_name:
        raise RuntimeError(
            "Pilot target does not match expected contract"
        )

    blocked_statuses = {
        "Requested",
        "Queued",
        "Running",
        "Stop Requested",
        "Delete Requested",
    }

    if status in blocked_statuses:
        print("PILOT_SCAN=ALREADY_ACTIVE")
        print(f"TASK_ID={task_id}")
        print(f"STATUS={status}")
        return

    start_response = gmp.start_task(
        task_id
    )

    report_id = (
        start_response.get("report_id")
        or start_response.get("id")
        or "-"
    )

    print("PILOT_SCAN=START_REQUESTED")
    print(f"TASK_ID={task_id}")
    print(f"TASK_NAME={task_name}")
    print(f"TARGET={target_name}")
    print(f"PREVIOUS_STATUS={status}")
    print(f"REPORT_ID={report_id}")


def command_report(gmp, report_id):
    response = gmp.get_report(
        report_id,
        filter_string="rows=-1 min_qod=0",
        details=True,
        ignore_pagination=True,
    )

    print(
        response.getroottree().getroot()
        if False
        else ""
    )

    from lxml import etree

    print(
        etree.tostring(
            response,
            encoding="unicode",
            pretty_print=False,
        )
    )




def command_host_start(gmp, hostname, address):
    """
    Start exactly one canonical HIMP-owned Greenbone task.

    The caller supplies inventory hostname and IPv4 address.
    The task UUID is resolved internally and is never accepted
    from the caller.
    """

    import ipaddress
    import re

    hostname = hostname.strip().lower()
    address = address.strip()

    if not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?",
        hostname,
    ):
        raise RuntimeError(
            "Invalid inventory hostname"
        )

    try:
        parsed_address = ipaddress.ip_address(
            address
        )
    except ValueError as exc:
        raise RuntimeError(
            "Invalid inventory IP address"
        ) from exc

    if parsed_address.version != 4:
        raise RuntimeError(
            "Only IPv4 inventory targets are supported"
        )

    if (
        hostname == "vulnscanner.server.arpa"
        or address == "10.10.37.62"
    ):
        raise RuntimeError(
            "Greenbone scanner self-target is excluded"
        )

    manifest_path = Path(
        "/etc/himp-greenbone/scan-hosts.tsv"
    )

    if not manifest_path.is_file():
        raise RuntimeError(
            "Canonical fleet manifest is missing"
        )

    manifest_matches = []

    for raw_line in manifest_path.read_text().splitlines():
        if not raw_line.strip():
            continue

        parts = raw_line.split("\t", 1)

        if len(parts) != 2:
            raise RuntimeError(
                "Canonical fleet manifest contains "
                "an invalid row"
            )

        manifest_hostname = parts[0].strip().lower()
        manifest_address = parts[1].strip()

        if (
            manifest_hostname == hostname
            or manifest_address == address
        ):
            manifest_matches.append(
                (
                    manifest_hostname,
                    manifest_address,
                )
            )

    if manifest_matches != [
        (
            hostname,
            address,
        )
    ]:
        raise RuntimeError(
            "Requested host does not uniquely match "
            "the canonical fleet manifest"
        )

    target_name = f"HIMP - {hostname}"
    task_name = (
        f"HIMP - {hostname} - Full and Fast"
    )

    targets_response = gmp.get_targets(
        filter_string="rows=-1"
    )

    targets = [
        target
        for target in targets_response.xpath("target")
        if text_value(
            target,
            "name",
        ) == target_name
    ]

    if len(targets) != 1:
        raise RuntimeError(
            f"Target {target_name} was not uniquely resolved"
        )

    target = targets[0]

    target_hosts = text_value(
        target,
        "hosts",
    )

    if target_hosts != address:
        raise RuntimeError(
            f"Target {target_name} has "
            f"unexpected address {target_hosts}"
        )

    tasks_response = gmp.get_tasks(
        filter_string="rows=-1",
        details=True,
    )

    tasks = [
        task
        for task in tasks_response.xpath("task")
        if text_value(
            task,
            "name",
        ) == task_name
    ]

    if len(tasks) != 1:
        raise RuntimeError(
            f"Task {task_name} was not uniquely resolved"
        )

    task = tasks[0]
    task_id = task.get("id")

    if not task_id:
        raise RuntimeError(
            "Resolved Greenbone task is missing its UUID"
        )

    actual_target = text_value(
        task,
        "target/name",
    )

    if actual_target != target_name:
        raise RuntimeError(
            f"Task {task_name} target mismatch: "
            f"{actual_target}"
        )

    status = text_value(
        task,
        "status",
    )

    blocked_statuses = {
        "Requested",
        "Queued",
        "Running",
        "Stop Requested",
        "Delete Requested",
    }

    if status in blocked_statuses:
        print("HOST_SCAN=ALREADY_ACTIVE")
        print(f"HOSTNAME={hostname}")
        print(f"ADDRESS={address}")
        print(f"TASK_ID={task_id}")
        print(f"TASK_NAME={task_name}")
        print(f"TARGET={target_name}")
        print(f"STATUS={status}")
        print("SCAN_STARTED=NO")
        print("HOST_START=PASS")
        return

    allowed_statuses = {
        "New",
        "Done",
        "Stopped",
        "Interrupted",
    }

    if status not in allowed_statuses:
        raise RuntimeError(
            f"Task {task_name} is not startable: {status}"
        )

    start_response = gmp.start_task(
        task_id
    )

    report_id = (
        start_response.get("report_id")
        or start_response.get("id")
        or "-"
    )

    print("HOST_SCAN=START_REQUESTED")
    print(f"HOSTNAME={hostname}")
    print(f"ADDRESS={address}")
    print(f"TASK_ID={task_id}")
    print(f"TASK_NAME={task_name}")
    print(f"TARGET={target_name}")
    print(f"PREVIOUS_STATUS={status}")
    print(f"REPORT_ID={report_id}")
    print("SCAN_STARTED=YES")
    print("HOST_START=PASS")


def ensure_admin_visibility(
    gmp,
    permission_name,
    resource_type,
    resource_id,
    resource_name,
):
    """
    Ensure the Greenbone Admin role has one bounded read permission
    for a HIMP-managed resource.
    """

    admin_role_id = (
        "7a8cb5b4-b74d-11e2-8187-406186ea4fc5"
    )

    if permission_name not in {
        "get_targets",
        "get_tasks",
        "get_reports",
    }:
        raise RuntimeError(
            "Unsupported Admin visibility permission"
        )

    if resource_type not in {
        "target",
        "task",
        "report",
    }:
        raise RuntimeError(
            "Unsupported Admin visibility resource type"
        )

    if not resource_id:
        raise RuntimeError(
            "Admin visibility resource UUID is missing"
        )

    permissions_response = gmp.get_permissions(
        filter_string="rows=-1"
    )

    for permission in permissions_response.xpath(
        "permission"
    ):
        existing_name = text_value(
            permission,
            "name",
        )

        subject_id = permission.xpath(
            "string(subject/@id)"
        )

        subject_type = text_value(
            permission,
            "subject/type",
        )

        existing_resource_id = permission.xpath(
            "string(resource/@id)"
        )

        existing_resource_type = text_value(
            permission,
            "resource/type",
        )

        if (
            existing_name == permission_name
            and subject_id == admin_role_id
            and subject_type == "role"
            and existing_resource_id == resource_id
            and existing_resource_type == resource_type
        ):
            print(
                "ADMIN_VISIBILITY_EXISTING\t"
                f"{permission_name}\t"
                f"{resource_type}\t"
                f"{resource_id}\t"
                f"{resource_name}"
            )

            return False

    response = gmp.create_permission(
        permission_name,
        admin_role_id,
        "role",
        resource_id=resource_id,
        resource_type=resource_type,
        comment=(
            "HIMP read-only Admin visibility "
            "for Greenbone-managed fleet resources."
        ),
    )

    permission_id = response.get("id")

    if not permission_id:
        raise RuntimeError(
            "Greenbone did not return a permission UUID"
        )

    print(
        "ADMIN_VISIBILITY_CREATED\t"
        f"{permission_name}\t"
        f"{resource_type}\t"
        f"{resource_id}\t"
        f"{permission_id}\t"
        f"{resource_name}"
    )

    return True


def command_host_reconcile(gmp, hostname, address):
    """
    Ensure exactly one HIMP Greenbone target and task exist
    for one explicitly supplied inventory host.

    This command never starts a scan.
    """

    import ipaddress
    import re

    hostname = hostname.strip().lower()
    address = address.strip()

    if not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?",
        hostname,
    ):
        raise RuntimeError(
            "Invalid inventory hostname"
        )

    try:
        parsed_address = ipaddress.ip_address(
            address
        )
    except ValueError as exc:
        raise RuntimeError(
            "Invalid inventory IP address"
        ) from exc

    if parsed_address.version != 4:
        raise RuntimeError(
            "Only IPv4 inventory targets are supported"
        )

    # The scanner must not automatically create a target
    # for itself.
    if (
        hostname == "vulnscanner.server.arpa"
        or address == "10.10.37.62"
    ):
        raise RuntimeError(
            "Greenbone scanner self-target is excluded"
        )

    config_name = "Full and fast"
    scanner_name = "OpenVAS Default"
    port_list_name = (
        "All TCP and Nmap top 100 UDP"
    )

    configs_response = gmp.get_scan_configs(
        filter_string="rows=-1"
    )

    configs = [
        item
        for item
        in configs_response.xpath("config")
        if text_value(item, "name") == config_name
    ]

    if len(configs) != 1:
        raise RuntimeError(
            "Full and fast config was not uniquely resolved"
        )

    config_id = configs[0].get("id")

    scanners_response = gmp.get_scanners(
        filter_string="rows=-1"
    )

    scanners = [
        item
        for item
        in scanners_response.xpath("scanner")
        if text_value(item, "name") == scanner_name
    ]

    if len(scanners) != 1:
        raise RuntimeError(
            "OpenVAS Default scanner was not uniquely resolved"
        )

    scanner_id = scanners[0].get("id")

    port_lists_response = gmp.get_port_lists(
        filter_string="rows=-1"
    )

    port_lists = [
        item
        for item
        in port_lists_response.xpath("port_list")
        if text_value(item, "name") == port_list_name
    ]

    if len(port_lists) != 1:
        raise RuntimeError(
            "Fleet port list was not uniquely resolved"
        )

    port_list_id = port_lists[0].get("id")

    target_name = f"HIMP - {hostname}"
    task_name = (
        f"HIMP - {hostname} - Full and Fast"
    )

    targets_response = gmp.get_targets(
        filter_string="rows=-1"
    )

    existing_targets = [
        target
        for target
        in targets_response.xpath("target")
        if text_value(
            target,
            "name",
        ) == target_name
    ]

    if len(existing_targets) > 1:
        raise RuntimeError(
            f"Multiple targets named {target_name}"
        )

    target_created = False

    if existing_targets:
        target = existing_targets[0]

        existing_hosts = text_value(
            target,
            "hosts",
        )

        if existing_hosts != address:
            raise RuntimeError(
                f"Target {target_name} has "
                f"unexpected address {existing_hosts}"
            )

        target_id = target.get("id")

        print(
            "TARGET_EXISTING\t"
            f"{hostname}\t"
            f"{address}\t"
            f"{target_id}"
        )

    else:
        response = gmp.create_target(
            target_name,
            hosts=[address],
            port_list_id=port_list_id,
            alive_test=AliveTest.CONSIDER_ALIVE,
            comment=(
                "HIMP Phase 16.4 inventory-managed "
                "vulnerability target."
            ),
        )

        target_id = response.get("id")

        if not target_id:
            raise RuntimeError(
                "Greenbone did not return a target UUID"
            )

        target_created = True

        print(
            "TARGET_CREATED\t"
            f"{hostname}\t"
            f"{address}\t"
            f"{target_id}"
        )

    tasks_response = gmp.get_tasks(
        filter_string="rows=-1"
    )

    existing_tasks = [
        task
        for task
        in tasks_response.xpath("task")
        if text_value(
            task,
            "name",
        ) == task_name
    ]

    if len(existing_tasks) > 1:
        raise RuntimeError(
            f"Multiple tasks named {task_name}"
        )

    task_created = False

    if existing_tasks:
        task = existing_tasks[0]

        existing_target = text_value(
            task,
            "target/name",
        )

        if existing_target != target_name:
            raise RuntimeError(
                f"Task {task_name} is attached "
                f"to unexpected target {existing_target}"
            )

        task_id = task.get("id")

        print(
            "TASK_EXISTING\t"
            f"{hostname}\t"
            f"{task_id}"
        )

    else:
        response = gmp.create_task(
            task_name,
            config_id,
            target_id,
            scanner_id,
            comment=(
                "HIMP Phase 16.4 inventory-managed "
                "Full and fast task. "
                "Creation does not start the scan."
            ),
        )

        task_id = response.get("id")

        if not task_id:
            raise RuntimeError(
                "Greenbone did not return a task UUID"
            )

        task_created = True

        print(
            "TASK_CREATED\t"
            f"{hostname}\t"
            f"{task_id}"
        )

    target_visibility_created = (
        ensure_admin_visibility(
            gmp,
            "get_targets",
            "target",
            target_id,
            target_name,
        )
    )

    task_visibility_created = (
        ensure_admin_visibility(
            gmp,
            "get_tasks",
            "task",
            task_id,
            task_name,
        )
    )

    manifest_path = Path(
        "/etc/himp-greenbone/scan-hosts.tsv"
    )

    if not manifest_path.is_file():
        raise RuntimeError(
            "Canonical fleet manifest is missing"
        )

    manifest_rows = []

    for raw_line in manifest_path.read_text().splitlines():
        if not raw_line.strip():
            continue

        parts = raw_line.split("\t", 1)

        if len(parts) != 2:
            raise RuntimeError(
                "Canonical fleet manifest contains "
                "an invalid row"
            )

        existing_hostname = parts[0].strip().lower()
        existing_address = parts[1].strip()

        if (
            existing_hostname == hostname
            and existing_address != address
        ):
            raise RuntimeError(
                f"Manifest hostname {hostname} is "
                f"already mapped to {existing_address}"
            )

        if (
            existing_address == address
            and existing_hostname != hostname
        ):
            raise RuntimeError(
                f"Manifest address {address} is "
                f"already mapped to {existing_hostname}"
            )

        manifest_rows.append(
            (
                existing_hostname,
                existing_address,
            )
        )

    matching_rows = [
        row
        for row in manifest_rows
        if row == (hostname, address)
    ]

    if len(matching_rows) > 1:
        raise RuntimeError(
            f"Manifest contains duplicate entry for "
            f"{hostname} {address}"
        )

    manifest_updated = False

    if not matching_rows:
        manifest_rows.append(
            (
                hostname,
                address,
            )
        )

        manifest_rows.sort(
            key=lambda item: (
                item[0].lower(),
                item[1],
            )
        )

        manifest_path.write_text(
            "".join(
                f"{row_hostname}\t{row_address}\n"
                for row_hostname, row_address
                in manifest_rows
            )
        )

        manifest_updated = True

    print(
        "TARGET_CREATED="
        + ("YES" if target_created else "NO")
    )

    print(
        "TASK_CREATED="
        + ("YES" if task_created else "NO")
    )

    print(
        "MANIFEST_UPDATED="
        + ("YES" if manifest_updated else "NO")
    )

    print(
        "TARGET_ADMIN_VISIBILITY="
        + (
            "CREATED"
            if target_visibility_created
            else "EXISTING"
        )
    )

    print(
        "TASK_ADMIN_VISIBILITY="
        + (
            "CREATED"
            if task_visibility_created
            else "EXISTING"
        )
    )

    print("SCAN_STARTED=NO")
    print("HOST_RECONCILE=PASS")



def command_fleet_reconcile(gmp):
    from pathlib import Path

    manifest_path = Path(
        "/etc/himp-greenbone/scan-hosts.tsv"
    )

    if not manifest_path.is_file():
        raise RuntimeError(
            "Canonical fleet manifest is missing"
        )

    rows = []

    for line in manifest_path.read_text().splitlines():
        if not line.strip():
            continue

        hostname, address = line.split(
            "\t",
            1,
        )

        rows.append(
            (
                hostname.strip(),
                address.strip(),
            )
        )

    if len(rows) != 45:
        raise RuntimeError(
            "Canonical fleet manifest must contain "
            "exactly 45 hosts"
        )

    config_name = "Full and fast"
    scanner_name = "OpenVAS Default"
    port_list_name = (
        "All TCP and Nmap top 100 UDP"
    )

    configs_response = gmp.get_scan_configs(
        filter_string="rows=-1"
    )

    configs = [
        item
        for item
        in configs_response.xpath("config")
        if text_value(item, "name") == config_name
    ]

    if len(configs) != 1:
        raise RuntimeError(
            "Full and fast config was not uniquely "
            "resolved"
        )

    config_id = configs[0].get("id")

    scanners_response = gmp.get_scanners(
        filter_string="rows=-1"
    )

    scanners = [
        item
        for item
        in scanners_response.xpath("scanner")
        if text_value(item, "name") == scanner_name
    ]

    if len(scanners) != 1:
        raise RuntimeError(
            "OpenVAS Default scanner was not "
            "uniquely resolved"
        )

    scanner_id = scanners[0].get("id")

    port_lists_response = gmp.get_port_lists(
        filter_string="rows=-1"
    )

    port_lists = [
        item
        for item
        in port_lists_response.xpath("port_list")
        if text_value(item, "name") == port_list_name
    ]

    if len(port_lists) != 1:
        raise RuntimeError(
            "Fleet port list was not uniquely "
            "resolved"
        )

    port_list_id = port_lists[0].get("id")

    targets_response = gmp.get_targets(
        filter_string="rows=-1"
    )

    target_by_name = {}

    for target in targets_response.xpath("target"):
        target_by_name.setdefault(
            text_value(target, "name"),
            [],
        ).append(target)

    tasks_response = gmp.get_tasks(
        filter_string="rows=-1"
    )

    task_by_name = {}

    for task in tasks_response.xpath("task"):
        task_by_name.setdefault(
            text_value(task, "name"),
            [],
        ).append(task)

    targets_created = 0
    targets_existing = 0

    tasks_created = 0
    tasks_existing = 0

    for hostname, address in rows:

        if hostname == "unbound107":
            target_name = (
                "HIMP Pilot - unbound107"
            )

            task_name = (
                "HIMP Pilot - unbound107 - "
                "Full and Fast"
            )

        else:
            target_name = (
                f"HIMP - {hostname}"
            )

            task_name = (
                f"HIMP - {hostname} - "
                f"Full and Fast"
            )

        existing_targets = target_by_name.get(
            target_name,
            [],
        )

        if len(existing_targets) > 1:
            raise RuntimeError(
                f"Multiple targets named "
                f"{target_name}"
            )

        if existing_targets:
            target = existing_targets[0]

            existing_hosts = text_value(
                target,
                "hosts",
            )

            if existing_hosts != address:
                raise RuntimeError(
                    f"Target {target_name} has "
                    f"unexpected address "
                    f"{existing_hosts}"
                )

            target_id = target.get("id")

            targets_existing += 1

        else:
            response = gmp.create_target(
                target_name,
                hosts=[address],
                port_list_id=port_list_id,
                alive_test=AliveTest.CONSIDER_ALIVE,
                comment=(
                    "HIMP Phase 16.4 canonical "
                    "fleet vulnerability target. "
                    "Generated only from the fixed "
                    "HIMP scan manifest."
                ),
            )

            target_id = response.get("id")

            if not target_id:
                raise RuntimeError(
                    f"Greenbone did not return "
                    f"a target UUID for {hostname}"
                )

            targets_created += 1

            print(
                f"TARGET_CREATED\t"
                f"{hostname}\t"
                f"{address}\t"
                f"{target_id}"
            )

        existing_tasks = task_by_name.get(
            task_name,
            [],
        )

        if len(existing_tasks) > 1:
            raise RuntimeError(
                f"Multiple tasks named "
                f"{task_name}"
            )

        if existing_tasks:
            task = existing_tasks[0]

            existing_target = text_value(
                task,
                "target/name",
            )

            if existing_target != target_name:
                raise RuntimeError(
                    f"Task {task_name} is attached "
                    f"to unexpected target "
                    f"{existing_target}"
                )

            tasks_existing += 1

        else:
            response = gmp.create_task(
                task_name,
                config_id,
                target_id,
                scanner_id,
                comment=(
                    "HIMP Phase 16.4 canonical "
                    "fleet Full and fast task. "
                    "Task creation does not start "
                    "the scan."
                ),
            )

            task_id = response.get("id")

            if not task_id:
                raise RuntimeError(
                    f"Greenbone did not return "
                    f"a task UUID for {hostname}"
                )

            tasks_created += 1

            print(
                f"TASK_CREATED\t"
                f"{hostname}\t"
                f"{task_id}"
            )

    print(
        f"FLEET_HOST_COUNT={len(rows)}"
    )

    print(
        f"TARGETS_CREATED={targets_created}"
    )

    print(
        f"TARGETS_EXISTING={targets_existing}"
    )

    print(
        f"TASKS_CREATED={tasks_created}"
    )

    print(
        f"TASKS_EXISTING={tasks_existing}"
    )

    print(
        "SCAN_STARTED=NO"
    )

    print(
        "FLEET_RECONCILE=PASS"
    )



def command_fleet_start_batch1(gmp):
    batch = (
        (
            "unbound108",
            "HIMP - unbound108 - Full and Fast",
            "HIMP - unbound108",
        ),
        (
            "unbound1007",
            "HIMP - unbound1007 - Full and Fast",
            "HIMP - unbound1007",
        ),
        (
            "unbound1008",
            "HIMP - unbound1008 - Full and Fast",
            "HIMP - unbound1008",
        ),
        (
            "unbound37100",
            "HIMP - unbound37100 - Full and Fast",
            "HIMP - unbound37100",
        ),
    )

    response = gmp.get_tasks(
        filter_string="rows=-1"
    )

    tasks = response.xpath("task")

    by_name = {}

    for task in tasks:
        by_name.setdefault(
            text_value(task, "name"),
            [],
        ).append(task)

    resolved = []

    for (
        hostname,
        task_name,
        target_name,
    ) in batch:

        matches = by_name.get(
            task_name,
            [],
        )

        if len(matches) != 1:
            raise RuntimeError(
                f"Task {task_name} was not "
                f"uniquely resolved"
            )

        task = matches[0]

        task_id = task.get("id")

        actual_target = text_value(
            task,
            "target/name",
        )

        status = text_value(
            task,
            "status",
        )

        if actual_target != target_name:
            raise RuntimeError(
                f"Task {task_name} target "
                f"contract mismatch: "
                f"{actual_target}"
            )

        if status not in {
            "New",
            "Done",
        }:
            raise RuntimeError(
                f"Task {task_name} is not idle: "
                f"{status}"
            )

        resolved.append(
            (
                hostname,
                task_id,
                task_name,
                target_name,
                status,
            )
        )

    print(
        f"BATCH_HOST_COUNT={len(resolved)}"
    )

    for (
        hostname,
        task_id,
        task_name,
        target_name,
        status,
    ) in resolved:

        start_response = gmp.start_task(
            task_id
        )

        report_id = (
            start_response.get("report_id")
            or start_response.get("id")
            or "-"
        )

        print(
            f"SCAN_START_REQUESTED\t"
            f"{hostname}\t"
            f"{task_id}\t"
            f"{status}\t"
            f"{report_id}"
        )

    print(
        "FLEET_BATCH1_START=PASS"
    )



def command_fleet_admin_visibility(gmp):
    admin_role_id = (
        "7a8cb5b4-b74d-11e2-8187-406186ea4fc5"
    )

    resources = []

    targets_response = gmp.get_targets(
        filter_string="rows=-1"
    )

    for target in targets_response.xpath("target"):
        name = text_value(
            target,
            "name",
        )

        if not (
            name.startswith("HIMP - ")
            or name == "HIMP Pilot - unbound107"
        ):
            continue

        resources.append(
            (
                "get_targets",
                "target",
                target.get("id"),
                name,
            )
        )

    tasks_response = gmp.get_tasks(
        filter_string="rows=-1"
    )

    himp_task_ids = set()

    for task in tasks_response.xpath("task"):
        name = text_value(
            task,
            "name",
        )

        if not (
            name.startswith("HIMP - ")
            or name
            == "HIMP Pilot - unbound107 - Full and Fast"
        ):
            continue

        task_id = task.get("id")

        himp_task_ids.add(
            task_id
        )

        resources.append(
            (
                "get_tasks",
                "task",
                task_id,
                name,
            )
        )

    reports_response = gmp.get_reports(
        filter_string="rows=-1",
        details=False,
    )

    for report in reports_response.xpath("report"):
        task_id = report.xpath(
            "string(task/@id)"
        )

        if task_id not in himp_task_ids:
            continue

        resources.append(
            (
                "get_reports",
                "report",
                report.get("id"),
                (
                    text_value(
                        report,
                        "task/name",
                    )
                    or report.get("id")
                ),
            )
        )

    permissions_response = gmp.get_permissions(
        filter_string="rows=-1"
    )

    existing = set()

    for permission in permissions_response.xpath("permission"):
        name = text_value(
            permission,
            "name",
        )

        subject_id = permission.xpath(
            "string(subject/@id)"
        )

        subject_type = text_value(
            permission,
            "subject/type",
        )

        resource_id = permission.xpath(
            "string(resource/@id)"
        )

        resource_type = text_value(
            permission,
            "resource/type",
        )

        if (
            subject_id == admin_role_id
            and subject_type == "role"
            and name in {
                "get_targets",
                "get_tasks",
                "get_reports",
            }
        ):
            existing.add(
                (
                    name,
                    resource_type,
                    resource_id,
                )
            )

    created = 0
    already_present = 0

    print(
        f"VISIBILITY_RESOURCE_COUNT="
        f"{len(resources)}"
    )

    for (
        permission,
        resource_type,
        resource_id,
        resource_name,
    ) in resources:

        key = (
            permission,
            resource_type,
            resource_id,
        )

        if key in existing:
            already_present += 1

            print(
                f"PERMISSION_EXISTING\t"
                f"{permission}\t"
                f"{resource_type}\t"
                f"{resource_id}\t"
                f"{resource_name}"
            )

            continue

        response = gmp.create_permission(
            permission,
            admin_role_id,
            "role",
            resource_id=resource_id,
            resource_type=resource_type,
            comment=(
                "HIMP read-only Admin visibility "
                "for Greenbone-managed fleet "
                "resources."
            ),
        )

        permission_id = (
            response.get("id")
            or "-"
        )

        created += 1

        print(
            f"PERMISSION_CREATED\t"
            f"{permission}\t"
            f"{resource_type}\t"
            f"{resource_id}\t"
            f"{permission_id}\t"
            f"{resource_name}"
        )

    print(
        f"PERMISSIONS_CREATED={created}"
    )

    print(
        f"PERMISSIONS_EXISTING={already_present}"
    )

    print(
        "FLEET_ADMIN_VISIBILITY=PASS"
    )



def command_fleet_start_batch2(gmp):
    batch = (
        (
            "dns1009",
            "HIMP - dns1009 - Full and Fast",
            "HIMP - dns1009",
        ),
        (
            "dns1011",
            "HIMP - dns1011 - Full and Fast",
            "HIMP - dns1011",
        ),
        (
            "dns1012",
            "HIMP - dns1012 - Full and Fast",
            "HIMP - dns1012",
        ),
        (
            "dns1013",
            "HIMP - dns1013 - Full and Fast",
            "HIMP - dns1013",
        ),
    )

    response = gmp.get_tasks(
        filter_string="rows=-1"
    )

    by_name = {}

    for task in response.xpath("task"):
        by_name.setdefault(
            text_value(task, "name"),
            [],
        ).append(task)

    resolved = []

    for hostname, task_name, target_name in batch:
        matches = by_name.get(
            task_name,
            [],
        )

        if len(matches) != 1:
            raise RuntimeError(
                f"Task {task_name} was not uniquely resolved"
            )

        task = matches[0]

        task_id = task.get("id")

        actual_target = text_value(
            task,
            "target/name",
        )

        status = text_value(
            task,
            "status",
        )

        if actual_target != target_name:
            raise RuntimeError(
                f"Task {task_name} target mismatch: "
                f"{actual_target}"
            )

        if status not in {
            "New",
            "Done",
        }:
            raise RuntimeError(
                f"Task {task_name} is not idle: "
                f"{status}"
            )

        resolved.append(
            (
                hostname,
                task_id,
                task_name,
                status,
            )
        )

    print(
        f"BATCH_HOST_COUNT={len(resolved)}"
    )

    for (
        hostname,
        task_id,
        task_name,
        status,
    ) in resolved:

        response = gmp.start_task(
            task_id
        )

        report_id = (
            response.get("report_id")
            or response.get("id")
            or "-"
        )

        print(
            f"SCAN_START_REQUESTED\t"
            f"{hostname}\t"
            f"{task_id}\t"
            f"{status}\t"
            f"{report_id}"
        )

    print(
        "FLEET_BATCH2_START=PASS"
    )



def command_fleet_start_pending(gmp):
    manifest_path = Path(
        "/etc/himp-greenbone/scan-hosts.tsv"
    )

    if not manifest_path.is_file():
        raise RuntimeError(
            "Canonical scan manifest is missing"
        )

    canonical_hosts = set()

    for line in manifest_path.read_text().splitlines():
        if not line.strip():
            continue

        hostname, _address = line.split(
            "\t",
            1,
        )

        canonical_hosts.add(
            hostname.strip()
        )

    tasks_response = gmp.get_tasks(
        filter_string="rows=-1",
        details=True,
    )

    reports_response = gmp.get_reports(
        filter_string="rows=-1",
        details=False,
    )

    task_ids_with_reports = set()

    for report in reports_response.xpath("report"):
        task_id = report.xpath(
            "string(task/@id)"
        )

        if task_id:
            task_ids_with_reports.add(
                task_id
            )

    candidates = []

    for task in tasks_response.xpath("task"):
        task_id = task.get("id")

        name = text_value(
            task,
            "name",
        )

        status = text_value(
            task,
            "status",
        )

        target_name = text_value(
            task,
            "target/name",
        )

        if name == (
            "HIMP Pilot - unbound107 - "
            "Full and Fast"
        ):
            hostname = "unbound107"

        elif (
            name.startswith("HIMP - ")
            and name.endswith(
                " - Full and Fast"
            )
        ):
            hostname = name[
                len("HIMP - "):
                -len(" - Full and Fast")
            ]

        else:
            continue

        if hostname not in canonical_hosts:
            raise RuntimeError(
                f"Task {name} is not represented "
                f"in the canonical fleet manifest"
            )

        expected_target = (
            "HIMP Pilot - unbound107"
            if hostname == "unbound107"
            else f"HIMP - {hostname}"
        )

        if target_name != expected_target:
            raise RuntimeError(
                f"Task {name} target mismatch: "
                f"{target_name}"
            )

        # Never rerun anything that already has a report.
        if task_id in task_ids_with_reports:
            continue

        # Only untouched Greenbone tasks are eligible.
        if status != "New":
            raise RuntimeError(
                f"Never-scanned task {name} has "
                f"unexpected state {status}"
            )

        candidates.append(
            (
                hostname,
                task_id,
                name,
            )
        )

    candidates.sort(
        key=lambda item: item[0].lower()
    )

    print(
        f"PENDING_SCAN_COUNT={len(candidates)}"
    )

    for hostname, task_id, name in candidates:
        response = gmp.start_task(
            task_id
        )

        report_id = (
            response.get("report_id")
            or response.get("id")
            or "-"
        )

        print(
            f"SCAN_START_REQUESTED\t"
            f"{hostname}\t"
            f"{task_id}\t"
            f"{report_id}"
        )

    print(
        f"SCANS_START_REQUESTED={len(candidates)}"
    )

    print(
        "FLEET_START_PENDING=PASS"
    )



def command_fleet_resume_incomplete(gmp):
    manifest_path = Path(
        "/etc/himp-greenbone/scan-hosts.tsv"
    )

    if not manifest_path.is_file():
        raise RuntimeError(
            "Canonical scan manifest is missing"
        )

    canonical_hosts = set()

    for line in manifest_path.read_text().splitlines():
        if not line.strip():
            continue

        hostname, _address = line.split(
            "\t",
            1,
        )

        canonical_hosts.add(
            hostname.strip()
        )

    response = gmp.get_tasks(
        filter_string="rows=-1",
        details=True,
    )

    candidates = []

    for task in response.xpath("task"):
        task_id = task.get("id")

        name = text_value(
            task,
            "name",
        )

        status = text_value(
            task,
            "status",
        )

        target_name = text_value(
            task,
            "target/name",
        )

        if name == (
            "HIMP Pilot - unbound107 - "
            "Full and Fast"
        ):
            hostname = "unbound107"

        elif (
            name.startswith("HIMP - ")
            and name.endswith(
                " - Full and Fast"
            )
        ):
            hostname = name[
                len("HIMP - "):
                -len(" - Full and Fast")
            ]

        else:
            continue

        if hostname not in canonical_hosts:
            raise RuntimeError(
                f"Task {name} is outside "
                f"the canonical fleet manifest"
            )

        expected_target = (
            "HIMP Pilot - unbound107"
            if hostname == "unbound107"
            else f"HIMP - {hostname}"
        )

        if target_name != expected_target:
            raise RuntimeError(
                f"Task {name} target mismatch: "
                f"{target_name}"
            )

        if status not in {
            "Stopped",
            "Interrupted",
        }:
            continue

        candidates.append(
            (
                hostname,
                task_id,
                name,
                status,
            )
        )

    candidates.sort(
        key=lambda item: item[0].lower()
    )

    print(
        f"RECOVERY_TASK_COUNT={len(candidates)}"
    )

    stopped = sum(
        1
        for item in candidates
        if item[3] == "Stopped"
    )

    interrupted = sum(
        1
        for item in candidates
        if item[3] == "Interrupted"
    )

    print(
        f"STOPPED_TASKS={stopped}"
    )

    print(
        f"INTERRUPTED_TASKS={interrupted}"
    )

    for (
        hostname,
        task_id,
        name,
        previous_status,
    ) in candidates:

        response = gmp.start_task(
            task_id
        )

        report_id = (
            response.get("report_id")
            or response.get("id")
            or "-"
        )

        print(
            f"RECOVERY_START_REQUESTED\t"
            f"{hostname}\t"
            f"{task_id}\t"
            f"{previous_status}\t"
            f"{report_id}"
        )

    print(
        f"RECOVERY_REQUESTS="
        f"{len(candidates)}"
    )

    print(
        "FLEET_RESUME_INCOMPLETE=PASS"
    )



def command_completed_reports(gmp):
    """
    Return compact metadata for completed HIMP-owned reports.

    Output is deliberately line-oriented and contains no finding
    payloads. Full report XML remains available only through the
    existing report <uuid> command.
    """

    response = gmp.get_reports(
        filter_string=(
            "rows=-1 "
            "status=Done "
            "sort-reverse=date"
        ),
        details=False,
    )

    completed = []

    for outer in response.xpath("report"):
        report_id = (
            outer.get("id")
            or ""
        ).strip()

        owner = outer.xpath(
            "string(owner/name)"
        ).strip()

        task_id = outer.xpath(
            "string(task/@id)"
        ).strip()

        task_name = outer.xpath(
            "string(task/name)"
        ).strip()

        status = outer.xpath(
            "string(report/scan_run_status)"
        ).strip()

        scan_start = outer.xpath(
            "string(report/scan_start)"
        ).strip()

        scan_end = outer.xpath(
            "string(report/scan_end)"
        ).strip()

        if owner != "himp-integration":
            continue

        if status != "Done":
            continue

        if not report_id:
            continue

        completed.append(
            (
                report_id,
                task_id,
                task_name,
                status,
                scan_start,
                scan_end,
            )
        )

    print(
        f"COMPLETED_REPORT_COUNT="
        f"{len(completed)}"
    )

    for (
        report_id,
        task_id,
        task_name,
        status,
        scan_start,
        scan_end,
    ) in completed:
        values = (
            report_id,
            task_id,
            task_name,
            status,
            scan_start,
            scan_end,
        )

        if any(
            "\t" in value
            or "\n" in value
            for value in values
        ):
            raise RuntimeError(
                "Greenbone report metadata contains "
                "unsupported control characters"
            )

        print(
            "COMPLETED_REPORT\t"
            + "\t".join(values)
        )


def command_reports(gmp):
    response = gmp.get_reports(
        filter_string=(
            "rows=20 "
            "sort-reverse=date"
        ),
        details=False,
    )

    reports = response.xpath("report")

    print(f"REPORT_COUNT={len(reports)}")

    for report in reports:
        report_id = report.get("id", "-")
        task = text_value(report, "task/name")
        scan_start = text_value(
            report,
            "scan_start",
        )
        scan_end = text_value(
            report,
            "scan_end",
        )

        print(
            f"{report_id}\t"
            f"{task}\t"
            f"{scan_start}\t"
            f"{scan_end}"
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only HIMP Greenbone GMP helper"
        )
    )

    parser.add_argument(
        "command",
        choices=(
            "status",
            "capabilities",
            "targets",
            "tasks",
            "reports",
            "completed-reports",
            "report",
            "host-reconcile",
            "host-start",
            "pilot-target",
            "pilot-task",
            "pilot-start",
            "fleet-reconcile",
            "fleet-start-batch1",
            "fleet-start-batch2",
            "fleet-admin-visibility",
            "fleet-start-pending",
            "fleet-resume-incomplete",
        ),
    )

    parser.add_argument(
        "report_id",
        nargs="?",
    )

    parser.add_argument(
        "hostname",
        nargs="?",
    )

    args = parser.parse_args()

    if args.command == "report":
        import uuid

        if not args.report_id:
            parser.error(
                "report requires a report UUID"
            )

        if args.hostname is not None:
            parser.error(
                "report accepts only one UUID"
            )

        try:
            uuid.UUID(
                args.report_id
            )
        except ValueError:
            parser.error(
                "report requires a valid UUID"
            )

    elif args.command in {
        "host-reconcile",
        "host-start",
    }:
        if not args.report_id:
            parser.error(
                f"{args.command} requires hostname"
            )

        if not args.hostname:
            parser.error(
                f"{args.command} requires IPv4 address"
            )

    elif (
        args.report_id is not None
        or args.hostname is not None
    ):
        parser.error(
            "unexpected additional argument"
        )

    if not os.path.exists(SOCKET):
        raise RuntimeError(
            f"GVMD socket not found: {SOCKET}"
        )

    username, password = load_credentials()

    connection = UnixSocketConnection(
        path=SOCKET
    )

    transform = EtreeCheckCommandTransform()

    with GMP(
        connection=connection,
        transform=transform,
    ) as gmp:
        gmp.authenticate(
            username,
            password,
        )

        if args.command == "status":
            command_status(gmp)

        elif args.command == "capabilities":
            command_capabilities(gmp)

        elif args.command == "targets":
            command_targets(gmp)

        elif args.command == "tasks":
            command_tasks(gmp)

        elif args.command == "reports":
            command_reports(gmp)

        elif args.command == "completed-reports":
            command_completed_reports(gmp)

        elif args.command == "report":
            command_report(
                gmp,
                args.report_id,
            )

        elif args.command == "host-reconcile":
            command_host_reconcile(
                gmp,
                args.report_id,
                args.hostname,
            )

        elif args.command == "host-start":
            command_host_start(
                gmp,
                args.report_id,
                args.hostname,
            )

        elif args.command == "pilot-target":
            command_pilot_target(gmp)

        elif args.command == "pilot-task":
            command_pilot_task(gmp)

        elif args.command == "pilot-start":
            command_pilot_start(gmp)

        elif args.command == "fleet-reconcile":
            command_fleet_reconcile(gmp)

        elif args.command == "fleet-start-batch1":
            command_fleet_start_batch1(gmp)

        elif args.command == "fleet-start-batch2":
            command_fleet_start_batch2(gmp)

        elif args.command == "fleet-admin-visibility":
            command_fleet_admin_visibility(gmp)

        elif args.command == "fleet-start-pending":
            command_fleet_start_pending(gmp)

        elif args.command == "fleet-resume-incomplete":
            command_fleet_resume_incomplete(gmp)


if __name__ == "__main__":
    try:
        main()
    except (
        GvmError,
        RuntimeError,
        OSError,
    ) as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
