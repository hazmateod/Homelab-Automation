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
    assert "Back to Dashboard" in source


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
