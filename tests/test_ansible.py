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


@pytest.mark.parametrize("outcome", ["success", "failure", "timeout"])
def test_extra_vars_file_is_private_and_removed_after_execution(monkeypatch, outcome):
    import json
    import stat
    from pathlib import Path
    from types import SimpleNamespace

    supplied = {"dashboard": ["fixture"], "secret_marker": "fixture-only"}
    path = None

    def fake_run(command, **options):
        nonlocal path
        assert command[-2] == "--extra-vars"
        assert command[-1].startswith("@")
        path = Path(command[-1][1:])
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert json.loads(path.read_text()) == supplied
        assert all("fixture-only" not in arg for arg in command)
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, options["timeout"])
        return SimpleNamespace(returncode=int(outcome == "failure"), stdout="", stderr="")

    monkeypatch.setattr(ansible.subprocess, "run", fake_run)
    if outcome == "timeout":
        with pytest.raises(ansible.AnsiblePlaybookTimeoutError):
            ansible.run_playbook("site.yml", timeout=3, extra_vars=supplied)
    else:
        assert ansible.run_playbook("site.yml", extra_vars=supplied).success == (outcome == "success")
    assert path is not None and not path.exists()
