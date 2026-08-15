import subprocess

import pytest

from himp.lib import ansible


def test_run_playbook_success(monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = "PLAY RECAP\\nok=1"
        stderr = ""

    monkeypatch.setattr(
        ansible.subprocess,
        "run",
        lambda *args, **kwargs: FakeResult(),
    )

    result = ansible.run_playbook(
        "site.yml",
    )

    assert result.success is True
    assert result.return_code == 0
    assert result.stdout == "PLAY RECAP\\nok=1"
    assert result.stderr == ""
    assert result.elapsed >= 0


def test_run_playbook_failure(monkeypatch):
    class FakeResult:
        returncode = 2
        stdout = "PLAY RECAP"
        stderr = "fatal: testhost"

    monkeypatch.setattr(
        ansible.subprocess,
        "run",
        lambda *args, **kwargs: FakeResult(),
    )

    result = ansible.run_playbook(
        "site.yml",
    )

    assert result.success is False
    assert result.return_code == 2
    assert result.stdout == "PLAY RECAP"
    assert result.stderr == "fatal: testhost"
    assert result.elapsed >= 0


def test_run_playbook_timeout_is_identifiable(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=kwargs["timeout"],
        )

    monkeypatch.setattr(
        ansible.subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(
        ansible.AnsiblePlaybookTimeoutError,
        match="Ansible playbook timed out",
    ):
        ansible.run_playbook(
            "site.yml",
            timeout=30,
        )
