import os
import stat
import subprocess
from pathlib import Path


HELPER = Path(
    "scripts/greenbone/himp_greenbone.py"
)
LAUNCHER = Path(
    "scripts/greenbone/himp-greenbone"
)
INSTALLER = Path(
    "scripts/greenbone/install.sh"
)
SUDOERS = Path(
    "config/greenbone/himp-greenbone.sudoers"
)


def _mode(path):
    return stat.S_IMODE(
        path.stat().st_mode
    )


def test_greenbone_managed_sources_exist():
    assert HELPER.is_file()
    assert LAUNCHER.is_file()
    assert INSTALLER.is_file()
    assert SUDOERS.is_file()


def test_greenbone_source_modes_are_bounded():
    assert _mode(HELPER) == 0o755
    assert _mode(LAUNCHER) == 0o755
    assert _mode(INSTALLER) == 0o755
    assert _mode(SUDOERS) == 0o644


def test_greenbone_launcher_exposes_constrained_host_start():
    source = LAUNCHER.read_text()

    assert "host-start)" in source

    assert (
        "Usage: himp-greenbone "
        "host-start <hostname> <IPv4>"
        in source
    )

    assert (
        '*[!a-zA-Z0-9.-]*'
        in source
    )

    assert (
        '*[!0-9.]*'
        in source
    )

    assert (
        "host-start \\\n"
        '          "$2" \\\n'
        '          "$3"'
        in source
    )


def test_greenbone_launcher_does_not_accept_task_uuid():
    source = LAUNCHER.read_text()

    host_start = source.split(
        "host-start)",
        1,
    )[1].split(
        ";;",
        1,
    )[0]

    assert "task" not in host_start.lower()
    assert "uuid" not in host_start.lower()


def test_greenbone_helper_host_start_is_manifest_bounded():
    source = HELPER.read_text()

    assert (
        "def command_host_start("
        in source
    )

    assert (
        '"/etc/himp-greenbone/scan-hosts.tsv"'
        in source
    )

    assert (
        "Requested host does not uniquely match "
        in source
    )

    assert (
        "the canonical fleet manifest"
        in source
    )

    assert (
        'target_name = f"HIMP - {hostname}"'
        in source
    )

    assert (
        'f"HIMP - {hostname} - Full and Fast"'
        in source
    )

    assert (
        "Greenbone scanner self-target is excluded"
        in source
    )

    assert (
        "gmp.start_task("
        in source
    )


def test_greenbone_helper_rejects_active_scan_states():
    source = HELPER.read_text()

    for status in (
        '"Requested"',
        '"Queued"',
        '"Running"',
        '"Stop Requested"',
        '"Delete Requested"',
    ):
        assert status in source

    assert (
        'print("HOST_SCAN=ALREADY_ACTIVE")'
        in source
    )

    assert (
        'print("SCAN_STARTED=NO")'
        in source
    )


def test_greenbone_sudoers_limits_host_start_arguments():
    source = SUDOERS.read_text()

    line = (
        "himp-greenbone ALL=(root) NOPASSWD: "
        "/usr/local/sbin/himp-greenbone "
        "host-start * *"
    )

    assert line in source

    assert (
        "/usr/local/sbin/himp-greenbone "
        "host-start * * *"
        not in source
    )

    assert (
        "/usr/local/sbin/himp-greenbone *"
        not in source
    )


def test_greenbone_sudoers_parses():
    result = subprocess.run(
        [
            "visudo",
            "-cf",
            str(SUDOERS),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stderr
        or result.stdout
    )


def test_greenbone_installer_enforces_production_modes():
    source = INSTALLER.read_text()

    assert (
        'HELPER_TARGET="/opt/himp-greenbone/'
        'himp_greenbone.py"'
        in source
    )

    assert (
        'LAUNCHER_TARGET="/usr/local/sbin/'
        'himp-greenbone"'
        in source
    )

    assert (
        'SUDOERS_TARGET="/etc/sudoers.d/'
        'himp-greenbone"'
        in source
    )

    assert "-m 0755" in source
    assert "-m 0440" in source

    assert (
        'visudo -cf "$SUDOERS_SOURCE"'
        in source
    )

    assert (
        'visudo -cf "$SUDOERS_TARGET"'
        in source
    )

    assert (
        'echo "GREENBONE_HELPER_INSTALL=PASS"'
        in source
    )


def test_greenbone_installer_requires_root():
    source = INSTALLER.read_text()

    assert (
        'if [[ "$EUID" -ne 0 ]]'
        in source
    )

    assert (
        "installer must run as root"
        in source
    )


def test_greenbone_installer_is_syntax_valid():
    result = subprocess.run(
        [
            "bash",
            "-n",
            str(INSTALLER),
        ],
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stderr
        or result.stdout
    )
