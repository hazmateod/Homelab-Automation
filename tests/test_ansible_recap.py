"""Regression tests for Ansible recap parsing."""

from himp.lib.ansible_recap import parse_play_recap


def test_successful_host():
    output = """
PLAY RECAP
dns1010 : ok=5 changed=2 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0
"""
    result = parse_play_recap(output)

    assert result["dns1010"]["status"] == "succeeded"
    assert result["dns1010"]["changed"] == 2


def test_failed_host():
    output = """
PLAY RECAP
wireguard10 : ok=2 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
"""
    result = parse_play_recap(output)

    assert result["wireguard10"]["status"] == "failed"
    assert result["wireguard10"]["failed"] == 1


def test_unreachable_takes_priority():
    output = """
PLAY RECAP
host1 : ok=0 changed=0 unreachable=1 failed=1 skipped=0 rescued=0 ignored=0
"""
    result = parse_play_recap(output)

    assert result["host1"]["status"] == "unreachable"


def test_skipped_host():
    output = """
PLAY RECAP
host1 : ok=0 changed=0 unreachable=0 failed=0 skipped=3 rescued=0 ignored=0
"""
    result = parse_play_recap(output)

    assert result["host1"]["status"] == "skipped"


def test_multiple_hosts():
    output = """
PLAY RECAP
host1 : ok=4 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
host2 : ok=2 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
"""
    result = parse_play_recap(output)

    assert len(result) == 2
    assert result["host1"]["status"] == "succeeded"
    assert result["host2"]["status"] == "failed"


def test_empty_output():
    assert parse_play_recap("") == {}


def test_no_recap():
    assert parse_play_recap("TASK [Update packages]") == {}


def test_missing_optional_counts():
    output = """
PLAY RECAP
host1 : ok=3 changed=1 unreachable=0 failed=0
"""
    result = parse_play_recap(output)

    assert result["host1"]["status"] == "succeeded"
    assert result["host1"]["ignored"] == 0


def test_failure_priority_over_skipped():
    output = """
PLAY RECAP
host1 : ok=0 changed=0 unreachable=0 failed=1 skipped=2
"""
    result = parse_play_recap(output)

    assert result["host1"]["status"] == "failed"
