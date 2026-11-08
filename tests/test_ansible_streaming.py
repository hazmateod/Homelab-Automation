"""Phase 17.1 streaming Ansible runner lifecycle tests."""

import subprocess
import sys
import time

import pytest

from himp.lib import ansible


def install_fake_ansible(monkeypatch, code):
    """Replace ansible-playbook with a synthetic Python process."""
    original_popen = subprocess.Popen

    def fake_popen(cmd, **kwargs):
        assert cmd[0] == "ansible-playbook"

        return original_popen(
            [sys.executable, "-u", "-c", code],
            **kwargs,
        )

    monkeypatch.setattr(
        ansible.subprocess,
        "Popen",
        fake_popen,
    )


def test_streaming_success(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        (
            "import sys,time;"
            "print('TASK [start]',flush=True);"
            "time.sleep(0.05);"
            "print('PLAY RECAP',flush=True);"
            "print('host1 : ok=2 changed=1 "
            "unreachable=0 failed=0 skipped=0',flush=True);"
            "print('warning',file=sys.stderr,flush=True)"
        ),
    )

    events = []

    result = ansible.run_playbook_streaming(
        "site.yml",
        limit="host1",
        timeout=5,
        on_output=events.append,
    )

    assert result.success is True
    assert result.return_code == 0
    assert "PLAY RECAP" in result.stdout
    assert result.stderr == "warning"
    assert events[0] == "TASK [start]"
    assert "PLAY RECAP" in events


def test_streaming_nonzero_exit(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        "import sys;print('failed',flush=True);sys.exit(2)",
    )

    result = ansible.run_playbook_streaming(
        "site.yml",
        timeout=5,
    )

    assert result.success is False
    assert result.return_code == 2
    assert result.stdout == "failed"


def test_streaming_timeout(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        "import time;print('started',flush=True);time.sleep(30)",
    )

    started = time.monotonic()

    with pytest.raises(
        ansible.AnsiblePlaybookTimeoutError,
        match="Ansible playbook timed out",
    ):
        ansible.run_playbook_streaming(
            "site.yml",
            timeout=0.3,
        )

    assert time.monotonic() - started < 5


def test_streaming_callback_exception(monkeypatch):
    install_fake_ansible(
        monkeypatch,
        "import time;print('started',flush=True);time.sleep(30)",
    )

    def failing_callback(line):
        raise ValueError("callback failure")

    started = time.monotonic()

    with pytest.raises(
        ValueError,
        match="callback failure",
    ):
        ansible.run_playbook_streaming(
            "site.yml",
            timeout=5,
            on_output=failing_callback,
        )

    assert time.monotonic() - started < 5


def test_streaming_timeout_terminates_child_processes(
    monkeypatch,
    tmp_path,
):
    """Timeout must terminate the process group, including children."""
    import os

    pid_file = tmp_path / "child.pid"

    child_code = (
        "import os,time;"
        f"open({str(pid_file)!r},'w').write(str(os.getpid()));"
        "time.sleep(30)"
    )

    parent_code = (
        "import subprocess,sys,time;"
        f"subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
        "print('child started',flush=True);"
        "time.sleep(30)"
    )

    install_fake_ansible(
        monkeypatch,
        parent_code,
    )

    with pytest.raises(
        ansible.AnsiblePlaybookTimeoutError,
    ):
        ansible.run_playbook_streaming(
            "site.yml",
            timeout=1,
        )

    assert pid_file.exists()

    child_pid = int(pid_file.read_text())

    # Linux may retain a terminated child briefly as a zombie.
    # A zombie is not an executing process.
    status_path = f"/proc/{child_pid}/status"

    deadline = time.monotonic() + 3

    while time.monotonic() < deadline:
        if not os.path.exists(status_path):
            break

        status = open(status_path).read()

        if "State:\tZ" in status:
            break

        time.sleep(0.05)
    else:
        pytest.fail(
            "Child process survived streaming timeout"
        )
