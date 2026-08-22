from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_server_exposes_authenticated_workflow_history_page():
    source = (
        ROOT / "himp/api/server.py"
    ).read_text()

    assert (
        '"/workflows/{workflow_id}/history"'
        in source
    )
    assert (
        'name="workflow_history.html"'
        in source
    )
    assert (
        "workflow_history_service.history("
        in source
    )
    assert (
        "dependencies=[Depends(require_page_session)]"
        in source
    )


def test_workflow_history_page_uses_canonical_layout():
    source = (
        ROOT / "templates/workflow_history.html"
    ).read_text()

    assert '{% extends "base.html" %}' in source
    assert "Workflow History" in source
    assert "Persisted Workflow Runs" in source
    assert "View Run" in source
    assert "Back to Workflows" in source


def test_workflow_history_links_runs_to_timeline():
    source = (
        ROOT / "templates/workflow_history.html"
    ).read_text()

    assert (
        '/workflows/{{ workflow.id }}/history/'
        '{{ run.workflow_execution_id }}'
        in source
    )


def test_workflow_history_exposes_replay_lineage():
    source = (
        ROOT / "templates/workflow_history.html"
    ).read_text()

    assert (
        "run.replay_of_workflow_execution_id"
        in source
    )
    assert "Replay of" in source


def test_workflow_timeline_returns_to_workflow_history_not_global_history():
    source = (
        ROOT
        / "templates/workflow_execution_timeline.html"
    ).read_text()

    assert (
        'href="/workflows/{{ '
        'workflow_run.workflow.id }}/history"'
        in source
    )
    assert "Workflow History" in source
    assert 'href="/history"' not in source


def test_workflow_timeline_exposes_replay_source_navigation():
    source = (
        ROOT
        / "templates/workflow_execution_timeline.html"
    ).read_text()

    assert (
        "workflow_run.replay_of_workflow_execution_id"
        in source
    )
    assert "Replay of" in source



def test_server_exposes_authenticated_workflows_page():
    source = (
        ROOT / "himp/api/server.py"
    ).read_text()

    assert '"/workflows"' in source
    assert 'name="workflows.html"' in source
    assert "workflow_service.list_workflows()" in source
    assert "workflow_history_service.history(" in source


def test_workflows_page_uses_canonical_layout():
    source = (
        ROOT / "templates/workflows.html"
    ).read_text()

    assert '{% extends "base.html" %}' in source
    assert "<h1>Workflows</h1>" in source
    assert "Workflow Orchestration" in source
    assert "View History" in source
    assert "View Latest Run" in source


def test_workflows_page_links_to_history_and_latest_run():
    source = (
        ROOT / "templates/workflows.html"
    ).read_text()

    assert (
        'href="/workflows/{{ workflow.id }}/history"'
        in source
    )

    assert (
        '/workflows/{{ workflow.id }}/history/'
        '{{ workflow.latest.workflow_execution_id }}'
        in source
    )


def test_sidebar_exposes_workflows_navigation():
    source = (
        ROOT / "templates/layout/sidebar.html"
    ).read_text()

    assert 'href="/workflows"' in source
    assert "Workflows" in source


def test_automation_execution_detail_resolves_workflow_navigation():
    source = (
        ROOT / "himp/api/server.py"
    ).read_text()

    assert 'context["workflow_navigation"]' in source
    assert '"origin_workflow_execution_id"' in source
    assert '"retry_source_workflow_execution_id"' in source
    assert '"retry_of_execution_id"' in source


def test_automation_execution_detail_exposes_originating_workflow_run():
    source = (
        ROOT
        / "templates/automation_execution_details.html"
    ).read_text()

    assert "Execution Provenance" in source
    assert "Originating Workflow Run" in source


def test_automation_execution_detail_exposes_retry_source_workflow_run():
    source = (
        ROOT
        / "templates/automation_execution_details.html"
    ).read_text()

    assert "Retry Source Workflow Run" in source


def test_automation_execution_detail_links_to_retry_source_execution():
    source = (
        ROOT
        / "templates/automation_execution_details.html"
    ).read_text()

    assert "Retry Of Automation Execution" in source
    assert (
        "workflow_navigation.retry_of_execution_id"
        in source
    )
