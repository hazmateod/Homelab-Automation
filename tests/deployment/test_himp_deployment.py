import os
import shutil
import subprocess
from pathlib import Path


DEPLOYMENT_SCRIPT = Path("scripts/deploy/himp.sh")
SYSTEMD_INSTALLER = Path("scripts/systemd/install.sh")

DEPLOY_DIRS = [
    "himp",
    "plugins",
    "playbooks",
    "inventory",
    "roles",
    "templates",
    "static",
    "config",
]

DEPLOY_FILES = [
    "ansible.cfg",
    "requirements.txt",
    "requirements-dev.txt",
]

SYSTEMD_UNITS = [
    "himp.service",
    "himp-inventory-sync.service",
    "himp-scheduled-updates.service",
    "himp-scheduler.service",
    "himp-scheduler.timer",
]


def _write_fake_systemctl(bin_dir, log_file):
    systemctl = bin_dir / "systemctl"
    systemctl.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        f'printf "%s\\n" "$*" >> "{log_file}"\n'
        "exit 0\n"
    )
    systemctl.chmod(0o755)


def _make_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    for directory in DEPLOY_DIRS:
        (project / directory).mkdir(parents=True)

    for filename in DEPLOY_FILES:
        (project / filename).write_text(f"fixture-{filename}\n")

    (project / "himp" / "marker.txt").write_text("version-1\n")

    (project / "scripts" / "deploy").mkdir(parents=True)
    (project / "scripts" / "systemd").mkdir(parents=True)
    (project / "systemd").mkdir(parents=True)

    shutil.copy2(
        DEPLOYMENT_SCRIPT,
        project / DEPLOYMENT_SCRIPT,
    )
    shutil.copy2(
        SYSTEMD_INSTALLER,
        project / SYSTEMD_INSTALLER,
    )

    for unit in SYSTEMD_UNITS:
        shutil.copy2(
            Path("systemd") / unit,
            project / "systemd" / unit,
        )

    subprocess.run(
        ["git", "init", "-q"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "HIMP Deployment Test"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "himp-test@example.invalid"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial deployment fixture"],
        cwd=project,
        check=True,
    )

    return project


def _run_deployment(
    project,
    deploy_root,
    systemd_root,
    bin_dir,
    *,
    check=True,
):
    env = os.environ.copy()
    env["DEPLOY_ROOT"] = str(deploy_root)
    env["SYSTEMD_TARGET_ROOT"] = str(systemd_root)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    return subprocess.run(
        ["bash", str(project / DEPLOYMENT_SCRIPT)],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def _prepare_environment(tmp_path):
    project = _make_project(tmp_path)
    deploy_root = tmp_path / "deploy"
    systemd_root = tmp_path / "systemd-target"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "systemctl.log"

    deploy_root.mkdir()
    systemd_root.mkdir()
    bin_dir.mkdir()

    _write_fake_systemctl(bin_dir, log_file)

    return (
        project,
        deploy_root,
        systemd_root,
        bin_dir,
        log_file,
    )


def _clear_log(log_file):
    log_file.write_text("")


def _log_lines(log_file):
    return [
        line.strip()
        for line in log_file.read_text().splitlines()
        if line.strip()
    ]


def test_unchanged_deployment_does_not_restart_himp(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    _clear_log(log_file)

    result = _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    assert "No HIMP changes detected; restart not required." in (
        result.stdout
    )
    assert "restart himp" not in _log_lines(log_file)
    assert "daemon-reload" not in _log_lines(log_file)


def test_dirty_working_tree_is_rejected(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    dirty_file = project / "himp" / "dirty.py"
    dirty_file.write_text("dirty = True\n")

    result = _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
        check=False,
    )

    assert result.returncode != 0
    assert "Deployment source contains uncommitted changes." in result.stdout
    assert not (deploy_root / ".himp-release").exists()


def test_successful_deployment_records_source_revision(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    expected_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    release_marker = deploy_root / ".himp-release"

    assert release_marker.exists()
    assert release_marker.read_text() == f"{expected_revision}\n"


def test_application_change_restarts_himp(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    _clear_log(log_file)

    (project / "himp" / "marker.txt").write_text("version-2\n")
    subprocess.run(
        ["git", "add", "himp/marker.txt"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "change application"],
        cwd=project,
        check=True,
    )

    result = _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    assert "Application changed: true" in result.stdout
    assert "restart himp" in _log_lines(log_file)


def test_himp_service_change_restarts_himp(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    _clear_log(log_file)

    service = project / "systemd" / "himp.service"
    service.write_text(
        service.read_text() + "\n# deployment regression test\n"
    )
    subprocess.run(
        ["git", "add", "systemd/himp.service"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "change himp service"],
        cwd=project,
        check=True,
    )

    result = _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    assert "HIMP service changed: true" in result.stdout
    assert "restart himp" in _log_lines(log_file)


def test_runtime_data_is_preserved(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    runtime_data = deploy_root / "data" / "runtime.db"
    runtime_data.parent.mkdir(parents=True)
    runtime_data.write_text("runtime-state\n")

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    assert runtime_data.exists()
    assert runtime_data.read_text() == "runtime-state\n"


def test_reports_are_preserved(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    report = deploy_root / "reports" / "runtime-report.json"
    report.parent.mkdir(parents=True)
    report.write_text('{"status": "preserved"}\n')

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    assert report.exists()
    assert report.read_text() == '{"status": "preserved"}\n'


def test_systemd_units_are_installed_into_configured_target(tmp_path):
    project, deploy_root, systemd_root, bin_dir, log_file = (
        _prepare_environment(tmp_path)
    )

    _run_deployment(
        project,
        deploy_root,
        systemd_root,
        bin_dir,
    )

    for unit in SYSTEMD_UNITS:
        target = systemd_root / unit
        assert target.exists()
        assert target.read_text() == (
            (project / "systemd" / unit).read_text()
        )
