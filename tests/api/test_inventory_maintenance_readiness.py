from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from himp.api import dependencies, inventory


def test_inventory_recovery_requires_admin_and_explicit_attestation(monkeypatch):
    app = FastAPI()
    app.include_router(inventory.router)
    session = SimpleNamespace(role="operator", username="operator")
    monkeypatch.setattr(dependencies, "require_session", lambda request: session)
    calls = []
    monkeypatch.setattr(inventory.service, "reconcile_maintenance", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(inventory.service, "record_verified_move", lambda *args, **kwargs: calls.append(args))

    payload = {
        "host_id": "id", "expected_incarnation": 1, "plan_id": "plan",
        "expected_ip": "192.0.2.1", "expected_user": "himp-automation",
        "plan_host": "prior-name", "note": "Verified host state", "confirm_drained": True,
    }
    with TestClient(app) as client:
        path = "/inventory/hosts/desktop/reconcile-maintenance"
        assert client.post(path, json=payload).status_code == 403
        assert client.post("/inventory/hosts/desktop/verified-move", json={
            "host_id": "id", "expected_incarnation": 1, "expected_ip": "192.0.2.1",
            "expected_user": "himp-automation", "continuity_verified": True,
        }).status_code == 403
        assert not calls

        session.role = "admin"
        assert client.post(path, json={**payload, "confirm_drained": False}).status_code == 422
        assert not calls
        assert client.post(path, json=payload).status_code == 200
        assert calls == [(
            ("desktop", "id", 1, "plan", "prior-name", "Verified host state"),
            {"endpoint": ("192.0.2.1", "himp-automation")},
        )]
