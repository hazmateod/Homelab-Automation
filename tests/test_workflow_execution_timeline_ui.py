from pathlib import Path


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
