from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.api import main as api_main
from backend.api.dependencies import get_db
from backend.api.main import app
from backend.authentication.auth_service import hash_password
from backend.database.connection import make_session
from backend.database.models import (
    Department,
    Interviewer,
    JobRequisition,
    Offer,
    ScreeningRule,
    User,
)


def test_authenticated_api_recruitment_workflow(mysql_database_url, tmp_path):
    session = make_session(mysql_database_url)
    upload_root = tmp_path / "private_uploads"
    original_upload_dir = api_main.PRIVATE_UPLOAD_DIR
    department = Department(name="API Acceptance", description="Isolated API workflow")
    interviewer = Interviewer(
        name="API Interviewer",
        email="api-interviewer@example.test",
        active=True,
    )
    inactive_interviewer = Interviewer(
        name="Inactive Interviewer",
        email="inactive-interviewer@example.test",
        active=False,
    )
    session.add_all([department, interviewer, inactive_interviewer])
    session.flush()
    interviewer.department_id = department.id
    inactive_interviewer.department_id = department.id
    requisition = JobRequisition(
        id="REQ-2026-API-001",
        department_id=department.id,
        title="API Acceptance Engineer",
        openings=1,
        min_salary=90000,
        max_salary=120000,
        location="Remote",
        status="Approved",
        requested_by="recruiter",
        approved_by="approver",
    )
    session.add(requisition)
    session.add(ScreeningRule(requisition_id=requisition.id, required_skills="Python"))
    session.add_all(
        [
            User(
                username="api-recruiter",
                password_hash=hash_password("RecruiterPass!2026"),
                role="Business Requester",
                active=True,
            ),
            User(
                username="api-owner",
                password_hash=hash_password("ProcessOwnerPass!2026"),
                role="Process Owner",
                active=True,
            ),
            User(
                username="api-approver",
                password_hash=hash_password("ApproverPass!2026"),
                role="Approver",
                active=True,
            ),
        ]
    )
    session.commit()

    def override_db():
        yield session

    api_main.PRIVATE_UPLOAD_DIR = upload_root
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    def login(username, password):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        token = response.json().get("token")
        assert isinstance(token, str) and token
        return {"Authorization": f"Bearer {token}"}

    def assert_object_response(response, expected_status=200):
        assert response.status_code == expected_status, response.text
        body = response.json()
        assert isinstance(body, dict)
        return body

    try:
        recruiter = login("api-recruiter", "RecruiterPass!2026")
        owner = login("api-owner", "ProcessOwnerPass!2026")
        approver = login("api-approver", "ApproverPass!2026")

        candidate = assert_object_response(
            client.post(
                "/api/candidates",
                headers=recruiter,
                json={
                    "first_name": "API",
                    "last_name": "Candidate",
                    "email": "api-candidate@example.test",
                    "phone": "555-0198",
                    "education": "BSc",
                    "years_experience": 5,
                    "location": "Remote",
                },
            )
        )
        candidate_id = candidate["id"]

        resume = assert_object_response(
            client.post(
                f"/api/candidates/{candidate_id}/resumes/upload",
                headers=recruiter,
                files={"file": ("resume.pdf", b"%PDF-1.7 API workflow", "application/pdf")},
            )
        )
        assert {"id", "candidate_id", "filename", "storage_path", "version"} <= resume.keys()
        downloaded = client.get(
            f"/api/candidates/{candidate_id}/resumes/{resume['id']}/download",
            headers=recruiter,
        )
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-")

        application = assert_object_response(
            client.post(
                "/api/applications",
                headers=recruiter,
                json={"requisition_id": requisition.id, "candidate_id": candidate_id},
            )
        )
        application_id = application["id"]
        duplicate = client.post(
            "/api/applications",
            headers=recruiter,
            json={"requisition_id": requisition.id, "candidate_id": candidate_id},
        )
        assert duplicate.status_code in {400, 409}

        invalid_stage = client.put(
            f"/api/applications/{application_id}/stage",
            headers=recruiter,
            json={"status": "Hired"},
        )
        assert invalid_stage.status_code == 400
        assert_object_response(
            client.put(
                f"/api/applications/{application_id}/stage",
                headers=owner,
                json={"status": "Screening"},
            )
        )
        screening = assert_object_response(
            client.post(
                "/api/screening/evaluate",
                headers=owner,
                json={"application_id": application_id},
            )
        )
        assert {"score", "matched_skills", "missing_skills", "rule_version"} <= screening.keys()

        for status in ("Shortlisted", "Interview Scheduled"):
            assert_object_response(
                client.put(
                    f"/api/applications/{application_id}/stage",
                    headers=owner,
                    json={"status": status},
                )
            )

        start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        interview_payload = {
            "application_id": application_id,
            "interviewer_id": interviewer.id,
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=1)).isoformat(),
            "round_number": 1,
        }
        interview = assert_object_response(
            client.post("/api/interviews", headers=owner, json=interview_payload)
        )
        interview_id = interview["id"]
        conflict_payload = {
            **interview_payload,
            "starts_at": (start + timedelta(minutes=15)).isoformat(),
            "ends_at": (start + timedelta(hours=1, minutes=15)).isoformat(),
        }
        assert client.post("/api/interviews", headers=owner, json=conflict_payload).status_code == 400
        inactive_payload = {
            **interview_payload,
            "interviewer_id": inactive_interviewer.id,
            "starts_at": (start + timedelta(days=1)).isoformat(),
            "ends_at": (start + timedelta(days=1, hours=1)).isoformat(),
        }
        assert client.post("/api/interviews", headers=owner, json=inactive_payload).status_code == 400
        assert client.put(
            f"/api/applications/{application_id}/stage",
            headers=owner,
            json={"status": "Interview Completed"},
        ).status_code == 400
        assert_object_response(
            client.put(
                f"/api/interviews/{interview_id}",
                headers=owner,
                json={"status": "Completed"},
            )
        )
        feedback = assert_object_response(
            client.post(
                "/api/feedback",
                headers=owner,
                json={
                    "interview_id": interview_id,
                    "interviewer_id": interviewer.id,
                    "technical_rating": 5,
                    "problem_solving_rating": 4,
                    "communication_rating": 5,
                    "role_skills_rating": 4,
                    "recommendation": "Strong Hire",
                },
            )
        )
        assert feedback["interview_id"] == interview_id

        for status in ("Interview Completed", "Selected", "Offer Pending"):
            assert_object_response(
                client.put(
                    f"/api/applications/{application_id}/stage",
                    headers=owner,
                    json={"status": status},
                )
            )

        outside = assert_object_response(
            client.post(
                "/api/offers",
                headers=owner,
                json={"application_id": application_id, "salary": 130000},
            )
        )
        assert {"id", "application_id", "salary", "status"} <= outside.keys()
        assert client.put(
            f"/api/offers/{outside['id']}/approve", headers=approver
        ).status_code == 400
        session.delete(session.get(Offer, outside["id"]))
        session.commit()

        offer = assert_object_response(
            client.post(
                "/api/offers",
                headers=owner,
                json={"application_id": application_id, "salary": 100000},
            )
        )
        assert {"id", "application_id", "salary", "status"} <= offer.keys()
        assert client.put(
            f"/api/offers/{offer['id']}/approve", headers=recruiter
        ).status_code == 403
        approved = assert_object_response(
            client.put(f"/api/offers/{offer['id']}/approve", headers=approver)
        )
        assert approved["status"] == "Approved"
        released = assert_object_response(
            client.put(f"/api/offers/{offer['id']}/release", headers=owner)
        )
        assert released["status"] == "Released"
        accepted = assert_object_response(
            client.put(
                f"/api/offers/{offer['id']}/status",
                headers=owner,
                json={"status": "Accepted"},
            )
        )
        assert accepted["status"] == "Accepted"

        analytics = assert_object_response(client.get("/api/analytics/overview", headers=owner))
        metrics = analytics["metrics"]
        assert metrics["offers_accepted"] >= 1
        assert metrics["average_time_to_hire_days"] >= 0
        validation = client.get("/api/validation", headers=owner)
        assert validation.status_code == 200
        assert all(
            {"check", "passed", "severity", "affected_ids"} <= row.keys()
            for row in validation.json()
        )
    finally:
        app.dependency_overrides.clear()
        api_main.PRIVATE_UPLOAD_DIR = original_upload_dir
        session.bind.dispose()
        session.close()
