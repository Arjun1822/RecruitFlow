from datetime import datetime, timedelta, timezone

import pytest

from backend.analytics.metrics import calculate_metrics
from backend.authentication.auth_service import has_permission
from backend.database.connection import make_session
from backend.database.models import (
    Application, ApplicationEvent, Candidate, Department, Feedback, Interview,
    Interviewer, JobRequisition, Offer, ScreeningRule, User,
)
from backend.services.application_service import apply_candidate, transition_application
from backend.services.interview_service import reschedule_interview, schedule_interview, update_interview_status
from backend.services.offer_service import approve_offer, create_offer, release_offer, update_offer_status
from backend.services.screening_service import screen_application
from backend.validation.validator import validate


def _fixture(url):
    session = make_session(url)
    department = Department(name="Engineering", description="Test department")
    session.add(department)
    session.flush()
    requisition = JobRequisition(
        id="REQ-2026-TEST01", department_id=department.id, title="Platform Engineer",
        openings=1, min_salary=90000, max_salary=120000, location="Remote",
        status="Approved", requested_by="requester", approved_by="approver",
    )
    candidate = Candidate(
        id="CAND-TEST01", first_name="Ada", last_name="Example",
        email="ada@example.test", phone="555-0100", education="B.Sc",
        years_experience=5, location="Remote",
    )
    interviewer = Interviewer(name="Reviewer", email="reviewer@example.test", department_id=department.id)
    session.add_all([requisition, candidate, interviewer])
    session.flush()
    session.add(ScreeningRule(requisition_id=requisition.id, required_skills="", preferred_skills=""))
    session.commit()
    return session, requisition, candidate, interviewer


def test_complete_recruitment_workflow_with_hired_metrics(mysql_database_url):
    session, requisition, candidate, interviewer = _fixture(mysql_database_url)
    process_owner = User(username="owner", role="Process Owner", active=True)
    approver = User(username="approver", role="Approver", active=True)

    application = apply_candidate(session, requisition.id, candidate.id, process_owner)
    with pytest.raises(ValueError, match="already applied"):
        apply_candidate(session, requisition.id, candidate.id, process_owner)
    requisition.status = "Closed"
    session.flush()
    closed_checks = validate(session)
    assert not next(item for item in closed_checks if item["check"] == "Closed requisitions with active applications")["passed"]
    requisition.status = "Approved"
    session.commit()
    transition_application(session, application.id, "Screening", process_owner)
    screening = screen_application(session, application.id)
    assert screening["score"] == 30.0
    transition_application(session, application.id, "Shortlisted", process_owner)
    transition_application(session, application.id, "Interview Scheduled", process_owner)

    start = datetime.now(timezone.utc) + timedelta(days=1)
    interview = schedule_interview(
        session, "INT-2026-TEST01", application.id, interviewer.id,
        start, start + timedelta(hours=1), actor=process_owner,
    )
    with pytest.raises(ValueError, match="unavailable"):
        schedule_interview(
            session, "INT-2026-CONFLICT", application.id, interviewer.id,
            start + timedelta(minutes=15), start + timedelta(hours=1, minutes=15),
            actor=process_owner,
        )
    interview = reschedule_interview(
        session, interview.id, start + timedelta(days=1),
        start + timedelta(days=1, hours=1), actor=process_owner,
    )
    assert interview.status == "Rescheduled"
    update_interview_status(session, interview.id, "Completed", process_owner)
    with pytest.raises(ValueError, match="feedback"):
        transition_application(session, application.id, "Interview Completed", process_owner)
    session.add(Feedback(
        id=f"FB-{interview.id}-{interviewer.id}", interview_id=interview.id,
        interviewer_id=interviewer.id, technical_rating=5, problem_solving_rating=4,
        communication_rating=5, role_skills_rating=4, overall_rating=4.5,
        recommendation="Strong Hire", comments="Excellent",
    ))
    session.commit()
    transition_application(session, application.id, "Interview Completed", process_owner)
    transition_application(session, application.id, "Selected", process_owner)
    transition_application(session, application.id, "Offer Pending", process_owner)
    invalid_offer = create_offer(session, "OFF-2026-OUTSIDE", application.id, 130000, process_owner)
    with pytest.raises(ValueError, match="outside"):
        approve_offer(session, invalid_offer.id, approver.username, approver)
    session.delete(invalid_offer)
    session.commit()
    offer = create_offer(session, "OFF-2026-TEST01", application.id, 100000, process_owner)
    approve_offer(session, offer.id, approver.username, approver)
    release_offer(session, offer.id, process_owner)
    update_offer_status(session, offer.id, "Accepted", process_owner)

    metrics = calculate_metrics(session)
    assert session.get(Application, application.id).status == "Hired"
    assert metrics["offers_accepted"] == 1
    assert metrics["average_time_to_hire_days"] >= 0
    assert session.query(ApplicationEvent).filter_by(application_id=application.id).count() >= 7
    session.close()


def test_required_role_permissions_cover_allowed_and_forbidden_operations():
    roles = {
        "Business Requester": {"manage_requisitions", "manage_candidates", "manage_applications"},
        "Process Owner": {"manage_interviews", "manage_feedback", "manage_offers"},
        "Approver": {"approve_requisitions", "approve_offers"},
        "Operations Analyst": {"view_analytics", "view_exceptions"},
        "System Administrator": {"*"},
    }
    for role, permissions in roles.items():
        user = User(username=role, role=role, active=True)
        for permission in permissions:
            assert has_permission(user, permission)
        if "*" not in permissions:
            assert not has_permission(user, "approve_offers" if "approve_offers" not in permissions else "manage_interviews")
