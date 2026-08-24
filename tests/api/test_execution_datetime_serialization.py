import json
from datetime import datetime

from himp.api import execution as execution_api


class FakeExecutionRepository:
    def find(self, execution_id):
        assert execution_id == 20
        return {
            "id": 20,
            "plugin": "detail",
            "success": 0,
            "return_code": 1,
            "elapsed": 0.0,
            "stdout": "",
            "stderr": "",
            "warnings": "[]",
            "artifacts": "[]",
            "executed_at": datetime(
                2026,
                8,
                9,
                23,
                36,
                3,
            ),
        }


def test_execution_detail_serializes_database_datetime(
    monkeypatch,
):
    monkeypatch.setattr(
        execution_api.execution,
        "repository",
        FakeExecutionRepository(),
    )

    response = execution_api.execution_detail(20)
    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["id"] == 20
    assert body["executed_at"] == "2026-08-09T23:36:03"
    assert body["warnings"] == []
    assert body["artifacts"] == []
