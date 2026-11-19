from types import SimpleNamespace

import pytest

from himp.commands import automation_run


@pytest.mark.parametrize(
    ("result", "exit_code", "message"),
    [
        ({"success": False}, 1, "Automation task failed."),
        ({"success": True, "skipped": True}, 0, "Automation task skipped."),
        ({"success": True}, 0, "Automation task completed successfully."),
    ],
)
def test_automation_run_reports_task_outcome(monkeypatch, capsys, result, exit_code, message):
    automation = SimpleNamespace(
        run=lambda task: {"task": task, "executed_at": "now", "result": result}
    )
    monkeypatch.setattr(automation_run, "HIMP", lambda: SimpleNamespace(automation=automation))

    assert automation_run.run(SimpleNamespace(task_id="test")) == exit_code
    output = capsys.readouterr()
    assert message in (output.err if exit_code else output.out)
