from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/systemd/install.sh"


def source():
    return INSTALLER.read_text()


def test_scheduler_timer_remains_enabled():
    text = source()

    assert (
        "systemctl enable himp-scheduler.timer"
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
