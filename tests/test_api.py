from fastapi.testclient import TestClient

from backend.api.main import app, serialize_user
from backend.api import main as api_main
from backend.api.dependencies import get_db
from backend.authentication.auth_service import create_access_token, decode_access_token, hash_password
from backend.database.models import Candidate, ResumeArtifact, User
from backend.database.connection import make_session


def test_signed_access_token_round_trip():
    user = User(username="api-test", role="Operations Analyst", active=True)
    token = create_access_token(user)
    claims = decode_access_token(token)
    assert claims["sub"] == "api-test"
    assert claims["role"] == "Operations Analyst"
    assert len(app.routes) >= 20
    assert any(route.path == "/api/candidates/{candidate_id}/resumes" for route in app.routes)
    assert any(route.path == "/api/applications/{application_id}/history" for route in app.routes)


def test_user_serialization_excludes_password_hash():
    user = User(username="api-test", role="Operations Analyst", password_hash="not-for-response")
    assert "password_hash" not in serialize_user(user)


def test_signed_access_token_rejects_tampering():
    user = User(username="api-test", role="Operations Analyst", active=True)
    token = create_access_token(user)
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    try:
        decode_access_token(".".join(parts))
    except ValueError:
        return
    raise AssertionError("Tampered access token was accepted")


def test_private_resume_upload_validation_and_authorized_download(mysql_database_url, tmp_path, monkeypatch):
    session = make_session(mysql_database_url)
    user = User(
        username="uploader", password_hash=hash_password("test-password"),
        role="Business Requester", active=True,
    )
    candidate = Candidate(
        id="CAND-UPLOAD", first_name="Test", last_name="Candidate",
        email="upload@example.test", phone="555-0101", education="BSc",
        years_experience=3, location="Remote",
    )
    session.add_all([user, candidate])
    session.commit()
    token = create_access_token(user)
    upload_root = tmp_path / "private"
    monkeypatch.setattr(api_main, "PRIVATE_UPLOAD_DIR", upload_root)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        invalid = client.post(
            "/api/candidates/CAND-UPLOAD/resumes/upload",
            headers=headers,
            files={"file": ("resume.txt", b"not a pdf", "text/plain")},
        )
        assert invalid.status_code == 400
        response = client.post(
            "/api/candidates/CAND-UPLOAD/resumes/upload",
            headers=headers,
            files={"file": ("resume.pdf", b"%PDF-1.7 test", "application/pdf")},
        )
        assert response.status_code == 200
        resume = response.json()
        assert resume["filename"] == "resume.pdf"
        assert (upload_root / resume["storage_path"]).read_bytes() == b"%PDF-1.7 test"
        download = client.get(
            f"/api/candidates/CAND-UPLOAD/resumes/{resume['id']}/download",
            headers=headers,
        )
        assert download.status_code == 200
        assert download.content.startswith(b"%PDF-")
        unauthorized = User(
            username="approver", password_hash=hash_password("test-password"),
            role="Approver", active=True,
        )
        session.add(unauthorized)
        session.commit()
        denied = client.get(
            f"/api/candidates/CAND-UPLOAD/resumes/{resume['id']}/download",
            headers={"Authorization": f"Bearer {create_access_token(unauthorized)}"},
        )
        assert denied.status_code == 403
        assert b"%PDF-" not in denied.content
    finally:
        app.dependency_overrides.clear()
        engine = session.get_bind(); session.close(); engine.dispose()


def test_approver_cannot_create_system_administrator(mysql_database_url):
    session = make_session(mysql_database_url)
    approver = User(
        username="approver-create-user", password_hash=hash_password("test-password"),
        role="Approver", active=True,
    )
    session.add(approver)
    session.commit()
    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        response = client.post(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {create_access_token(approver)}"},
            json={
                "username": "escalated-admin",
                "password": "test-password-long",
                "role": "System Administrator",
            },
        )
        assert response.status_code == 403
        assert session.query(User).filter(User.username == "escalated-admin").count() == 0
    finally:
        app.dependency_overrides.clear()
        engine = session.get_bind(); session.close(); engine.dispose()
