import secrets

from backend.authentication import auth_service
from backend.authentication.auth_service import authenticate, has_permission, hash_password, register_admin
from backend.database.connection import make_session


def test_authentication_and_permissions(mysql_database_url, monkeypatch):
    session = make_session(mysql_database_url)
    monkeypatch.setattr(auth_service, "ADMIN_REGISTRATION_ENABLED", True)
    username = f"admin-{secrets.token_hex(4)}"
    password = f"TestAdmin!{secrets.token_urlsafe(12)}"
    admin = register_admin(session, username, password)
    assert authenticate(session, username, password).username == username
    assert authenticate(session, username, "wrong-password") is None
    assert has_permission(admin, "anything")
    assert hash_password(secrets.token_urlsafe(16)).startswith("$2")
    engine = session.get_bind(); session.close(); engine.dispose()
