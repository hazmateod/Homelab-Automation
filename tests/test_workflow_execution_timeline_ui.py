from pathlib import Path


def test_workflow_timeline_uses_canonical_base_template():
    template = Path(
        "templates/workflow_execution_timeline.html"
    ).read_text()

    assert (
        '{% extends "base.html" %}'
        in template
    )

    assert (
        'layout/base.html'
        not in template
    )


def test_workflow_timeline_template_exists():
    path = Path(
        "templates/workflow_execution_timeline.html"
    )

    assert path.exists()


def test_workflow_timeline_template_exposes_execution_contract():
    template = Path(
        "templates/workflow_execution_timeline.html"
    ).read_text()

    assert "Workflow Execution Timeline" in template
    assert "workflow_run.workflow_execution_id" in template
    assert "workflow_run.status" in template
    assert "workflow_run.started_at" in template
    assert "workflow_run.completed_at" in template
    assert "workflow_run.duration_seconds" in template
    assert "workflow_run.timeline" in template
    assert 'event.type == "task_execution"' in template
    assert 'event.type == "current_task"' in template
    assert 'event.type == "workflow_completed"' in template
    assert "/automation/executions/" in template


def test_dashboard_links_workflow_execution_to_timeline():
    template = Path(
        "templates/dashboard.html"
    ).read_text()

    assert (
        "/workflows/{{ workflow.id }}/history/"
        "{{ workflow.workflow_execution_id }}"
        in template
    )


def test_server_exposes_authenticated_timeline_page():
    source = Path(
        "himp/api/server.py"
    ).read_text()

    assert (
        '"/workflows/{workflow_id}/history/'
        '{workflow_execution_id}"'
        in source
    )

    assert (
        "workflow_execution_timeline_page"
        in source
    )

    assert (
        'name="workflow_execution_timeline.html"'
        in source
    )

    assert "require_page_session" in source



def test_workflow_timeline_exposes_operator_failure_analysis():
    template = Path(
        "templates/workflow_execution_timeline.html"
    ).read_text()

    assert "Failure Analysis" in template
    assert "Failed components" in template
    assert "Return code" in template
    assert "event.failure_analysis.return_code" in template
    assert "Prior successful workflow step" in template
    assert "Successful components before failure" in template
    assert "No persisted target evidence." in template
    assert "No persisted error text." in template
    assert "Raw persisted failure details" in template



def test_workflow_timeline_exposes_safe_retry_replay_controls():
    template = Path(
        "templates/workflow_execution_timeline.html"
    ).read_text()

    assert "Retry Failed Step" in template
    assert "Replay Workflow" in template
    assert "current workflow definition" in template
    assert "Resume is unavailable" in template
    assert "workflow_actions_admin" in template
    assert "retryFailedStep" in template
    assert "replayWorkflow" in template


def test_workflow_retry_replay_api_is_admin_only():
    source = Path(
        "himp/api/workflows.py"
    ).read_text()

    assert (
        "retry_workflow_failed_step"
        in source
    )

    assert (
        "replay_workflow_execution"
        in source
    )

    assert source.count(
        "dependencies=[Depends(require_admin)]"
    ) >= 2
