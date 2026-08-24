import pytest

from himp.commands import scheduler_run


@pytest.fixture(autouse=True)
def isolate_scheduler_greenbone_ingestion(
    monkeypatch,
    request,
):
    if (
        request.node.path.name
        == "test_scheduler_vulnerability_ingest.py"
    ):
        return

    monkeypatch.setattr(
        scheduler_run,
        "_run_vulnerability_ingest",
        lambda: {
            "success": True,
            "discovered": 0,
            "imported": 0,
            "remaining": 0,
        },
    )
