from fastapi import HTTPException
from fastapi.testclient import TestClient

from himp.api.dependencies import require_admin
from himp.api import server


class FakeUserManagementService:
    def __init__(self):
        self.users = [
            {
                "username": "admin",
                "role": "admin",
                "active": True,
                "display_name": "Administrator",
            },
        ]
        self.created = []

    def list_users(self):
        return list(self.users)

    def create_user(
        self,
        username,
        password,
        role,
        display_name="",
        password_change_required=False,
    ):
        result = {
            "username": username.strip().lower(),
            "role": role,
            "active": True,
            "display_name": display_name,
        }
        self.created.append({
            "username": username,
            "password": password,
            "role": role,
            "display_name": display_name,
            "password_change_required": password_change_required,
        })
        self.users.append(result)
        return result


def test_list_users_requires_admin():
    server.app.dependency_overrides[require_admin] = (
        lambda: (_ for _ in ()).throw(
            HTTPException(
                status_code=403,
                detail="Administrator access required",
            )
        )
    )

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/users")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Administrator access required"
    }


def test_list_users_returns_users(monkeypatch):
    service = FakeUserManagementService()

    monkeypatch.setattr(
        server.himp,
        "user_management",
        service,
    )

    from himp.api import users

    monkeypatch.setattr(
        users,
        "user_management",
        service,
    )

    server.app.dependency_overrides[require_admin] = (
        lambda: {"username": "admin", "role": "admin"}
    )

    try:
        with TestClient(server.app) as client:
            response = client.get("/api/users")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {
                "username": "admin",
                "role": "admin",
                "active": True,
                "display_name": "Administrator",
            }
        ]
    }


def test_create_user_returns_created_user(monkeypatch):
    service = FakeUserManagementService()

    from himp.api import users

    monkeypatch.setattr(
        users,
        "user_management",
        service,
    )

    server.app.dependency_overrides[require_admin] = (
        lambda: {"username": "admin", "role": "admin"}
    )

    try:
        with TestClient(server.app) as client:
            response = client.post(
                "/api/users",
                json={
                    "username": " Operator1 ",
                    "password": "valid-password",
                    "role": "operator",
                    "display_name": "Operator One",
                    "password_change_required": True,
                },
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "username": "operator1",
        "role": "operator",
        "active": True,
        "display_name": "Operator One",
    }

    assert service.created == [
        {
            "username": " Operator1 ",
            "password": "valid-password",
            "role": "operator",
            "display_name": "Operator One",
            "password_change_required": True,
        }
    ]


def test_create_user_returns_bad_request_for_service_validation_error(
    monkeypatch,
):
    class RejectingService:
        def create_user(self, **kwargs):
            raise ValueError("Invalid user role: invalid")

    from himp.api import users

    monkeypatch.setattr(
        users,
        "user_management",
        RejectingService(),
    )

    server.app.dependency_overrides[require_admin] = (
        lambda: {"username": "admin", "role": "admin"}
    )

    try:
        with TestClient(server.app) as client:
            response = client.post(
                "/api/users",
                json={
                    "username": "operator1",
                    "password": "valid-password",
                    "role": "invalid",
                },
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid user role: invalid"
    }
