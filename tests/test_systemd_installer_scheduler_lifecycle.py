from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/systemd/install.sh"


def source():
    return INSTALLER.read_text()


def test_scheduler_timer_enablement_is_conditional():
    text = source()

    assert 'SCHEDULER_TIMER_PREEXISTING=false' in text
    assert 'SCHEDULER_TIMER_PREEXISTING=true' in text
    assert 'if [[ "$SCHEDULER_TIMER_PREEXISTING" == "false" ]]; then' in text
    assert "systemctl enable himp-scheduler.timer" in text


def test_existing_timer_state_is_preserved():
    text = source()

    assert (
        "Existing scheduler timer: preserving enabled/disabled state."
        in text
    )


def test_scheduler_timer_start_requires_explicit_opt_in():
    text = source()

    assert (
        '${HIMP_START_SCHEDULER_TIMER:-0}'
        in text
    )

    assert (
        '== "1"'
        in text
    )

    assert (
        "Starting scheduler timer by explicit request"
        in text
    )


def test_normal_installer_does_not_restart_scheduler_timer():
    text = source()

    assert (
        "systemctl restart himp-scheduler.timer"
        not in text
    )


def test_normal_installer_preserves_active_scheduler_timer():
    text = source()

    assert (
        "systemctl is-active --quiet "
        "himp-scheduler.timer"
        in text
    )

    assert (
        "already active; leaving it running"
        in text
    )


def test_normal_deployment_documents_unchanged_runtime_state():
    text = source()

    assert (
        "Scheduler timer runtime state left unchanged."
        in text
    )


def test_inactive_scheduler_status_is_nonfatal():
    text = source()

    assert (
        "systemctl status \\\n"
        "    himp-scheduler.timer \\\n"
        "    --no-pager || true"
        in text
    )


def test_scheduler_installer_timer_states(tmp_path):
    """Exercise fresh and existing installations with fake systemctl."""
    import os
    import subprocess

    for scenario in ("fresh", "enabled", "disabled"):
        root = tmp_path / scenario
        project = root / "project"
        target = root / "systemd"
        fake_bin = root / "bin"
        log = root / "systemctl.log"

        (project / "scripts/systemd").mkdir(
            parents=True
        )
        (project / "systemd").mkdir()
        target.mkdir()
        fake_bin.mkdir()

        installer = project / "scripts/systemd/install.sh"
        installer.write_bytes(INSTALLER.read_bytes())

        units = (
            "himp.service",
            "himp-inventory-sync.service",
            "himp-scheduled-updates.service",
            "himp-scheduler.service",
            "himp-scheduler.timer",
        )

        for unit in units:
            (project / "systemd" / unit).write_text(
                f"[Unit]\\nDescription={unit}\\n"
            )

        if scenario != "fresh":
            (target / "himp-scheduler.timer").write_text(
                "[Unit]\\nDescription=existing\\n"
            )

        fake_systemctl = fake_bin / "systemctl"
        fake_systemctl.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "%s\\n" "$*" >> "{log}"\n'
            "exit 0\n"
        )
        fake_systemctl.chmod(0o755)

        env = os.environ.copy()
        env["SYSTEMD_TARGET_ROOT"] = str(target)
        env["PATH"] = f"{fake_bin}:{env['PATH']}"

        result = subprocess.run(
            ["bash", str(installer)],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr

        calls = log.read_text().splitlines()

        scheduler_enables = [
            call for call in calls
            if call == "enable himp-scheduler.timer"
        ]

        scheduler_starts = [
            call for call in calls
            if call in (
                "start himp-scheduler.timer",
                "restart himp-scheduler.timer",
            )
        ]

        if scenario == "fresh":
            assert len(scheduler_enables) == 1
        else:
            assert scheduler_enables == []

        assert scheduler_starts == []
