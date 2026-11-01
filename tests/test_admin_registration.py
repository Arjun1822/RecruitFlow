import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.api import main as api_main
from backend.api.dependencies import get_db
from backend.api.main import app
from backend.authentication import auth_service
from backend.authentication.auth_service import register_admin
from backend.database.connection import make_session
from backend.database.models import AuditLog, User


def _client(session, host):
    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app, base_url=f"http://{host}", client=(host, 50000))


def test_first_registration_and_login(mysql_database_url, monkeypatch):
    session = make_session(mysql_database_url)
    monkeypatch.setattr(auth_service, "ADMIN_REGISTRATION_ENABLED", True)
    monkeypatch.setattr(api_main, "ADMIN_REGISTRATION_ENABLED", True)
    username = f"first-{secrets.token_hex(4)}"
    password = f"StrongAdmin!{secrets.token_urlsafe(12)}"
    client = _client(session, "127.0.0.1")
    try:
        response = client.post("/api/auth/register-admin", json={
            "username": username, "password": password, "password_confirmation": password,
        })
        assert response.status_code == 201
        assert "password_hash" not in response.text
        assert client.post("/api/auth/login", json={"username": username, "password": password}).status_code == 200
        session.expire_all()
        created_user = session.scalar(select(User).where(User.username == username))
        assert created_user.role == "System Administrator"
        assert session.scalar(select(AuditLog).where(AuditLog.action == "REGISTER_ADMIN")) is not None
    finally:
        app.dependency_overrides.clear()
        engine = session.get_bind(); session.close(); engine.dispose()


def test_duplicate_registration_is_rejected(mysql_database_url, monkeypatch):
    session = make_session(mysql_database_url)
    monkeypatch.setattr(auth_service, "ADMIN_REGISTRATION_ENABLED", True)
    monkeypatch.setattr(api_main, "ADMIN_REGISTRATION_ENABLED", True)
    client = _client(session, "127.0.0.1")
    password = f"StrongAdmin!{secrets.token_urlsafe(12)}"
    try:
        payload = {"username": "only-admin", "password": password, "password_confirmation": password}
        assert client.post("/api/auth/register-admin", json=payload).status_code == 201
        assert client.post("/api/auth/register-admin", json=payload).status_code == 409
        assert session.query(User).filter(User.role == "System Administrator").count() == 1
    finally:
        app.dependency_overrides.clear()
        engine = session.get_bind(); session.close(); engine.dispose()


def test_remote_registration_is_rejected(mysql_database_url, monkeypatch):
    session = make_session(mysql_database_url)
    monkeypatch.setattr(auth_service, "ADMIN_REGISTRATION_ENABLED", True)
    monkeypatch.setattr(api_main, "ADMIN_REGISTRATION_ENABLED", True)
    client = _client(session, "192.0.2.10")
    try:
        response = client.post("/api/auth/register-admin", json={
            "username": "remote-admin",
            "password": f"StrongAdmin!{secrets.token_urlsafe(12)}",
            "password_confirmation": "different-password",
        }, headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 403
        assert session.query(User).count() == 0
    finally:
        app.dependency_overrides.clear()
        engine = session.get_bind(); session.close(); engine.dispose()


def test_concurrent_registration_creates_one_administrator(mysql_database_url, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr(auth_service, "ADMIN_REGISTRATION_ENABLED", True)
    username = f"concurrent-{secrets.token_hex(4)}"
    password = f"StrongAdmin!{secrets.token_urlsafe(12)}"

    def attempt():
        session = make_session(mysql_database_url)
        try:
            return register_admin(session, username, password)
        except ValueError:
            return None
        finally:
            engine = session.get_bind(); session.close(); engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1


@pytest.mark.parametrize("enabled, environment", [(False, "development"), (True, "production")])
def test_registration_disabled_by_default_and_in_production(mysql_database_url, monkeypatch, enabled, environment):
    session = make_session(mysql_database_url)
    monkeypatch.setattr(auth_service, "ADMIN_REGISTRATION_ENABLED", enabled and environment != "production")
    monkeypatch.setattr(api_main, "ADMIN_REGISTRATION_ENABLED", enabled and environment != "production")
    monkeypatch.setattr(api_main, "RMS_ENV", environment)
    client = _client(session, "127.0.0.1")
    try:
        response = client.post("/api/auth/register-admin", json={
            "username": "blocked-admin",
            "password": f"StrongAdmin!{secrets.token_urlsafe(12)}",
            "password_confirmation": f"StrongAdmin!{secrets.token_urlsafe(12)}",
        })
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine = session.get_bind(); session.close(); engine.dispose()
