from himp.commands import report


class Args:
    limit = None


class FakeResult:
    def __init__(
        self,
        success,
        elapsed,
    ):
        self.success = success
        self.elapsed = elapsed


def test_report_command_handles_successful_result(
    monkeypatch,
):
    calls = []

    def fake_run_playbook(
        playbook,
        limit,
    ):
        calls.append(
            (
                playbook,
                limit,
            )
        )

        return FakeResult(
            success=True,
            elapsed=12.5,
        )

    monkeypatch.setattr(
        report,
        "run_playbook",
        fake_run_playbook,
    )

    result = report.run(Args())

    assert result is None
    assert calls == [
        (
            report.config.report_playbook,
            None,
        )
    ]


def test_report_command_handles_failed_result(
    monkeypatch,
):
    calls = []

    def fake_run_playbook(
        playbook,
        limit,
    ):
        calls.append(
            (
                playbook,
                limit,
            )
        )

        return FakeResult(
            success=False,
            elapsed=8.25,
        )

    monkeypatch.setattr(
        report,
        "run_playbook",
        fake_run_playbook,
    )

    result = report.run(Args())

    assert result is None
    assert calls == [
        (
            report.config.report_playbook,
            None,
        )
    ]
