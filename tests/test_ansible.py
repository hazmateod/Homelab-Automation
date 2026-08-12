import subprocess

from himp.lib import ansible


def test_run_playbook_success(monkeypatch):
    class FakeResult:
        returncode = 0

    monkeypatch.setattr(
        ansible.subprocess,
        "run",
        lambda *args, **kwargs: FakeResult(),
    )

    success, elapsed = ansible.run_playbook(
        "site.yml",
    )

    assert success is True
    assert elapsed >= 0


def test_run_playbook_failure(monkeypatch):
    class FakeResult:
        returncode = 2

    monkeypatch.setattr(
        ansible.subprocess,
        "run",
        lambda *args, **kwargs: FakeResult(),
    )

    success, elapsed = ansible.run_playbook(
        "site.yml",
    )

    assert success is False
    assert elapsed >= 0


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

    result = ansible.run_playbook(
        "site.yml",
        timeout=30,
    )

    assert result[0] is False
    assert result[1] >= 0
