"""Safely repair stale anomaly labels in an existing challenge database.

This module never initializes a schema or resets data.  ``--dry-run`` only
reads and reports the planned changes.  ``--apply`` performs one transaction
after all preconditions have been checked.
"""

import argparse
from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.config import DATABASE_URL
from backend.database.connection import make_engine
from backend.database.models import (
    Anomaly,
    AnomalyFixtureEvidence,
    Application,
    ApplicationEvent,
    AuditLog,
    Candidate,
    Feedback,
    Interview,
    Interviewer,
    JobRequisition,
    Offer,
)

EXPECTED_COUNTS = {
    "job_requisitions": 100,
    "candidates": 2000,
    "applications": 3000,
    "interviews": 600,
    "offers": 150,
}
EXPECTED_ISSUES = {
    "ANOM-00001": "Unavailable interviewer",
    "ANOM-00002": "Duplicate application",
    "ANOM-00003": "Missing interview feedback",
    "ANOM-00004": "Offer salary outside band",
    "ANOM-00005": "Closed requisition with active applications",
}
REPAIR_TIMESTAMP = datetime(2026, 1, 1, 0, 0, 0)
TARGET_CLOSED_REQUISITION_ID = "REQ-2026-000051"
TARGET_LABELLED_APPLICATION_ID = "APP-REQ-2026-000051-CAND-000002"
TARGET_ACTIVE_APPLICATION_COUNT = 27
TARGET_REJECTION_COUNT = 26
VALID_TRANSITIONS = {
    "Applied": {"Screening", "Withdrawn", "Rejected"},
    "Screening": {"Shortlisted", "Rejected", "Withdrawn"},
    "Shortlisted": {"Interview Scheduled", "Rejected", "Withdrawn"},
    "Interview Scheduled": {"Interview Completed", "Withdrawn"},
    "Interview Completed": {"Selected", "Rejected", "Withdrawn"},
    "Selected": {"Offer Pending", "Rejected"},
    "Offer Pending": {"Offer Released", "Rejected"},
    "Offer Released": {"Hired", "Withdrawn"},
    "Hired": set(),
    "Rejected": set(),
    "Withdrawn": set(),
}
INACTIVE_INTERVIEWER_ID = 66
INACTIVE_INTERVIEW_ID = "INT-2026-000466"
MISSING_FEEDBACK_INTERVIEW_ID = "INT-2026-000015"
MISSING_FEEDBACK_APPLICATION_ID = "APP-REQ-2026-000087-CAND-000998"
OUTSIDE_BAND_OFFER_ID = "OFF-2026-000001"


def _require_challenge_database(database_url: str) -> None:
    parsed = make_url(database_url)
    if parsed.drivername != "mysql+pymysql":
        raise RuntimeError("Anomaly repair requires mysql+pymysql://")
    if not parsed.host or not parsed.port:
        raise RuntimeError("Anomaly repair requires an explicit database host and port")
    if parsed.database != "rms_challenge":
        raise RuntimeError("Anomaly repair is restricted to the rms_challenge database")


def _assert_schema(session: Session) -> None:
    tables = set(inspect(session.bind).get_table_names())
    required = set(EXPECTED_COUNTS) | {
        "anomalies",
        "anomaly_fixture_evidence",
        "application_events",
        "audit_logs",
        "feedback",
        "interviewers",
    }
    missing = sorted(required - tables)
    if missing:
        raise RuntimeError(f"Required schema tables are missing: {', '.join(missing)}")


def _assert_preconditions(session: Session) -> JobRequisition:
    _assert_schema(session)
    count_failures = []
    for table, expected in EXPECTED_COUNTS.items():
        model = {
            "job_requisitions": JobRequisition,
            "candidates": Candidate,
            "applications": Application,
            "interviews": Interview,
            "offers": Offer,
        }[table]
        actual = session.scalar(select(func.count()).select_from(model))
        if actual != expected:
            count_failures.append(f"{table}={actual}, expected={expected}")
    if count_failures:
        raise RuntimeError("Baseline counts differ: " + "; ".join(count_failures))

    if session.scalar(select(AnomalyFixtureEvidence.id).limit(1)) is not None:
        raise RuntimeError("Refusing to repair because anomaly fixture evidence already exists")

    anomalies = session.scalars(select(Anomaly)).all()
    if {row.issue_id: row.issue_type for row in anomalies} != EXPECTED_ISSUES:
        raise RuntimeError("Existing anomaly labels do not match the required five issue IDs/types")
    if any(row.ground_truth != "positive" for row in anomalies):
        raise RuntimeError("All five existing anomaly labels must have positive ground truth")
    duplicate_application = session.get(Application, next(
        row.entity_id for row in anomalies if row.issue_id == "ANOM-00002"
    ))
    if not duplicate_application:
        raise RuntimeError("ANOM-00002 must reference an existing application")

    interviewer = session.get(Interviewer, INACTIVE_INTERVIEWER_ID)
    interview = session.get(Interview, INACTIVE_INTERVIEW_ID)
    if not interviewer or interviewer.active is not True:
        raise RuntimeError("Interviewer 66 must be active before repair")
    if not interview or interview.interviewer_id != INACTIVE_INTERVIEWER_ID or interview.status != "Scheduled":
        raise RuntimeError("INT-2026-000466 must be scheduled with interviewer 66")

    missing_feedback_interview = session.get(Interview, MISSING_FEEDBACK_INTERVIEW_ID)
    missing_feedback_application = session.get(Application, MISSING_FEEDBACK_APPLICATION_ID)
    if (
        not missing_feedback_interview
        or missing_feedback_interview.status != "Scheduled"
        or missing_feedback_interview.application_id != MISSING_FEEDBACK_APPLICATION_ID
        or not missing_feedback_application
        or missing_feedback_application.status != "Shortlisted"
        or session.scalar(
            select(Feedback.id).where(Feedback.interview_id == MISSING_FEEDBACK_INTERVIEW_ID)
        ) is not None
    ):
        raise RuntimeError("Missing-feedback fixture preconditions are not satisfied")
    transitions = session.scalars(
        select(ApplicationEvent).where(
            ApplicationEvent.application_id == MISSING_FEEDBACK_APPLICATION_ID,
            ApplicationEvent.to_status.in_(["Interview Scheduled", "Interview Completed"]),
        )
    ).all()
    if transitions:
        raise RuntimeError("Missing-feedback lifecycle events already exist")

    offer = session.get(Offer, OUTSIDE_BAND_OFFER_ID)
    if not offer:
        raise RuntimeError("OFF-2026-000001 does not exist")
    offer_application = session.get(Application, offer.application_id)
    offer_requisition = (
        session.get(JobRequisition, offer_application.requisition_id)
        if offer_application else None
    )
    if (
        not offer_application
        or not offer_requisition
        or not offer_requisition.min_salary <= offer.salary <= offer_requisition.max_salary
        or offer.status != "Accepted"
        or not offer.approved_by
        or offer.released_at is None
    ):
        raise RuntimeError("Offer salary fixture preconditions are not satisfied")

    closed_requisition = session.get(JobRequisition, TARGET_CLOSED_REQUISITION_ID)
    if not closed_requisition or closed_requisition.status == "Closed":
        raise RuntimeError("REQ-2026-000051 must exist and be non-closed before repair")
    active_applications = session.scalars(select(Application).where(
        Application.requisition_id == TARGET_CLOSED_REQUISITION_ID,
        Application.status.not_in(["Rejected", "Withdrawn"]),
    ).order_by(Application.id)).all()
    if len(active_applications) != TARGET_ACTIVE_APPLICATION_COUNT:
        raise RuntimeError(
            f"{TARGET_CLOSED_REQUISITION_ID} must have exactly "
            f"{TARGET_ACTIVE_APPLICATION_COUNT} active applications"
        )
    labelled_application = session.get(Application, TARGET_LABELLED_APPLICATION_ID)
    if (
        not labelled_application
        or labelled_application.requisition_id != TARGET_CLOSED_REQUISITION_ID
        or labelled_application.status in {"Rejected", "Withdrawn"}
    ):
        raise RuntimeError(
            f"{TARGET_LABELLED_APPLICATION_ID} must be the labelled active application"
        )
    if sum(application.id != TARGET_LABELLED_APPLICATION_ID for application in active_applications) != TARGET_REJECTION_COUNT:
        raise RuntimeError(
            f"Exactly {TARGET_REJECTION_COUNT} non-evidence applications must transition"
        )
    active_offers = session.scalars(
        select(Offer.id).join(Application, Offer.application_id == Application.id).where(
            Application.requisition_id == TARGET_CLOSED_REQUISITION_ID,
            Application.status.not_in(["Rejected", "Withdrawn"]),
        )
    ).all()
    if active_offers:
        raise RuntimeError(
            f"{TARGET_CLOSED_REQUISITION_ID} has active applications with offers: {active_offers}"
        )
    invalid_transitions = [
        f"{application.id}: {application.status}->Rejected"
        for application in active_applications
        if application.id != TARGET_LABELLED_APPLICATION_ID
        and "Rejected" not in VALID_TRANSITIONS.get(application.status, set())
    ]
    if invalid_transitions:
        raise RuntimeError("Invalid target transitions: " + "; ".join(invalid_transitions))
    return closed_requisition


def _planned_changes(session: Session, closed_requisition: JobRequisition) -> list[str]:
    anomalies = {row.issue_id: row for row in session.scalars(select(Anomaly)).all()}
    duplicate_application = session.get(Application, anomalies["ANOM-00002"].entity_id)
    closed_application = session.get(Application, TARGET_LABELLED_APPLICATION_ID)
    active_count = session.scalar(select(func.count()).select_from(Application).where(
        Application.requisition_id == closed_requisition.id,
        Application.status.not_in(["Rejected", "Withdrawn"]),
    ))
    active_applications = session.scalars(select(Application).where(
        Application.requisition_id == closed_requisition.id,
        Application.status.not_in(["Rejected", "Withdrawn"]),
    ).order_by(Application.id)).all()
    transitions = [
        f"{application.id}: {application.status} -> Rejected"
        for application in active_applications[1:]
    ]
    offer = session.get(Offer, OUTSIDE_BAND_OFFER_ID)
    return [
        f"ANOM-00001 entity_id: {anomalies['ANOM-00001'].entity_id} -> {INACTIVE_INTERVIEW_ID}; "
        "interviewer 66 active: True -> False",
        f"ANOM-00002 entity_id: {anomalies['ANOM-00002'].entity_id} -> {duplicate_application.id}; "
        f"evidence pair: ({duplicate_application.requisition_id}, {duplicate_application.candidate_id}); "
        "no duplicate application row will be inserted",
        f"ANOM-00003 entity_id: {anomalies['ANOM-00003'].entity_id} -> {MISSING_FEEDBACK_APPLICATION_ID}; "
        f"interview {MISSING_FEEDBACK_INTERVIEW_ID}: Scheduled -> Completed; "
        f"application: Shortlisted -> Interview Scheduled -> Interview Completed",
        f"ANOM-00004 entity_id: {anomalies['ANOM-00004'].entity_id} -> {OUTSIDE_BAND_OFFER_ID}; "
        f"salary: {offer.salary} -> {offer_requisition_max(session, offer) + 5000}; "
        "status: Accepted -> Pending Approval; approved_by/released_at -> NULL",
        f"ANOM-00005 entity_id: {anomalies['ANOM-00005'].entity_id} -> {closed_requisition.id}; "
        f"requisition status: {closed_requisition.status} -> Closed; "
        f"evidence application: {closed_application.id}; active applications affected: {active_count}; "
        f"{active_count - 1} active applications transition to Rejected",
        "Closed-requisition lifecycle transitions: " + "; ".join(transitions),
        "Evidence inserts: ANOM-00001(INT-2026-000466, interviewer=66), "
        f"ANOM-00002({duplicate_application.id}), "
        f"ANOM-00003({MISSING_FEEDBACK_APPLICATION_ID}, {MISSING_FEEDBACK_INTERVIEW_ID}), "
        f"ANOM-00004({OUTSIDE_BAND_OFFER_ID}), "
        f"ANOM-00005({closed_requisition.id}, {closed_application.id})",
        f"Lifecycle inserts: {MISSING_FEEDBACK_APPLICATION_ID} "
        "Shortlisted->Interview Scheduled, Interview Scheduled->Interview Completed",
        f"Audit inserts: five anomaly-repair entries plus {len(transitions)} application status-change entries",
    ]


def offer_requisition_max(session: Session, offer: Offer) -> float:
    application = session.get(Application, offer.application_id)
    requisition = session.get(JobRequisition, application.requisition_id) if application else None
    if not requisition:
        raise RuntimeError("Offer application or requisition is missing")
    return requisition.max_salary


def _apply_changes(session: Session, closed_requisition: JobRequisition) -> None:
    anomalies = {row.issue_id: row for row in session.scalars(select(Anomaly)).all()}
    duplicate_application = session.get(Application, anomalies["ANOM-00002"].entity_id)
    unavailable_interview = session.get(Interview, INACTIVE_INTERVIEW_ID)
    unavailable_interviewer = session.get(Interviewer, INACTIVE_INTERVIEWER_ID)
    missing_feedback_interview = session.get(Interview, MISSING_FEEDBACK_INTERVIEW_ID)
    missing_feedback_application = session.get(Application, MISSING_FEEDBACK_APPLICATION_ID)
    offer = session.get(Offer, OUTSIDE_BAND_OFFER_ID)
    offer_application = session.get(Application, offer.application_id)
    offer_requisition = session.get(JobRequisition, offer_application.requisition_id)
    closed_application = session.get(Application, TARGET_LABELLED_APPLICATION_ID)
    active_applications = session.scalars(select(Application).where(
        Application.requisition_id == closed_requisition.id,
        Application.status.not_in(["Rejected", "Withdrawn"]),
    ).order_by(Application.id)).all()
    for application in active_applications:
        if application.id == closed_application.id:
            continue
        if "Rejected" not in VALID_TRANSITIONS.get(application.status, set()):
            raise RuntimeError(
                f"Invalid closed-requisition transition: {application.id} "
                f"{application.status} -> Rejected"
            )
        old_status = application.status
        application.status = "Rejected"
        session.add(ApplicationEvent(
            application_id=application.id,
            from_status=old_status,
            to_status="Rejected",
            changed_by="anomaly-repair",
            changed_at=REPAIR_TIMESTAMP,
        ))
        session.add(AuditLog(
            actor="anomaly-repair",
            action="STATUS_CHANGE",
            entity_type="Application",
            entity_id=application.id,
            details=f"{old_status}->Rejected (ANOM-00005 cleanup)",
            occurred_at=REPAIR_TIMESTAMP,
        ))

    unavailable_interviewer.active = False
    missing_feedback_interview.status = "Completed"
    missing_feedback_application.status = "Interview Scheduled"
    session.add(ApplicationEvent(
        application_id=missing_feedback_application.id,
        from_status="Shortlisted",
        to_status="Interview Scheduled",
        changed_by="anomaly-repair",
        changed_at=REPAIR_TIMESTAMP,
    ))
    missing_feedback_application.status = "Interview Completed"
    session.add(ApplicationEvent(
        application_id=missing_feedback_application.id,
        from_status="Interview Scheduled",
        to_status="Interview Completed",
        changed_by="anomaly-repair",
        changed_at=REPAIR_TIMESTAMP,
    ))
    offer.salary = offer_requisition.max_salary + 5000
    offer.status = "Pending Approval"
    offer.approved_by = None
    offer.released_at = None
    closed_requisition.status = "Closed"

    anomalies["ANOM-00001"].entity_id = unavailable_interview.id
    anomalies["ANOM-00002"].entity_id = duplicate_application.id
    anomalies["ANOM-00003"].entity_id = missing_feedback_application.id
    anomalies["ANOM-00004"].entity_id = offer.id
    anomalies["ANOM-00005"].entity_id = closed_requisition.id

    session.add_all([
        AnomalyFixtureEvidence(
            issue_id="ANOM-00001", interview_id=unavailable_interview.id,
            interviewer_id=unavailable_interviewer.id,
            expected_result="inactive interviewer",
            details="The linked interviewer is inactive.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00002", requisition_id=duplicate_application.requisition_id,
            candidate_id=duplicate_application.candidate_id,
            application_id=duplicate_application.id,
            expected_result="duplicate attempt rejected",
            details="The unique application pair rejects a second attempt without a duplicate row.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00003", application_id=missing_feedback_application.id,
            interview_id=missing_feedback_interview.id,
            expected_result="completed interview feedback missing",
            details="The completed interview has no feedback row.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00004", requisition_id=offer_requisition.id,
            application_id=offer_application.id, offer_id=offer.id,
            expected_result="salary outside approved band",
            details="The pending offer salary exceeds the requisition maximum.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00005", requisition_id=closed_requisition.id,
            application_id=closed_application.id,
            expected_result="closed requisition has active application",
            details="Only this application is exempted from the closed-requisition check.",
        ),
    ])
    session.add_all([
        AuditLog(
            actor="anomaly-repair", action="ANOMALY_FIXTURE",
            entity_type=entity_type, entity_id=entity_id,
            details=details, occurred_at=REPAIR_TIMESTAMP,
        )
        for entity_type, entity_id, details in [
            ("Interview", unavailable_interview.id, "ANOM-00001: interviewer 66 deactivated"),
            ("Application", missing_feedback_application.id, "ANOM-00003: completed without feedback"),
            ("Offer", offer.id, "ANOM-00004: salary moved outside requisition band"),
            ("JobRequisition", closed_requisition.id, "ANOM-00005: closed with linked active application"),
            ("Application", duplicate_application.id, "ANOM-00002: duplicate attempt rejected"),
        ]
    ])


def _verify_conditions(session: Session) -> list[str]:
    evidence = {row.issue_id: row for row in session.scalars(select(AnomalyFixtureEvidence)).all()}
    failures: list[str] = []
    if len(evidence) != 5 or set(evidence) != set(EXPECTED_ISSUES):
        failures.append("exactly five evidence rows linked to the five issue IDs")

    fixture_audit_keys = {
        ("Interview", INACTIVE_INTERVIEW_ID, "ANOM-00001: interviewer 66 deactivated"),
        ("Application", MISSING_FEEDBACK_APPLICATION_ID, "ANOM-00003: completed without feedback"),
        ("Offer", OUTSIDE_BAND_OFFER_ID, "ANOM-00004: salary moved outside requisition band"),
        ("JobRequisition", TARGET_CLOSED_REQUISITION_ID,
         "ANOM-00005: closed with linked active application"),
    }
    duplicate_fixture = evidence.get("ANOM-00002")
    if duplicate_fixture:
        fixture_audit_keys.add((
            "Application",
            duplicate_fixture.application_id,
            "ANOM-00002: duplicate attempt rejected",
        ))
    fixture_audits = session.scalars(select(AuditLog).where(
        AuditLog.actor == "anomaly-repair",
        AuditLog.action == "ANOMALY_FIXTURE",
        AuditLog.details.in_([details for _, _, details in fixture_audit_keys]),
    )).all()
    actual_fixture_audits = {
        (row.entity_type, row.entity_id, row.details)
        for row in fixture_audits
        if (row.entity_type, row.entity_id, row.details) in fixture_audit_keys
    }
    if len(fixture_audits) != 5 or actual_fixture_audits != fixture_audit_keys:
        failures.append("exactly five repair fixture audit entries")

    row = evidence.get("ANOM-00001")
    interviewer = session.get(Interviewer, row.interviewer_id) if row else None
    if not row or row.interview_id != INACTIVE_INTERVIEW_ID or not interviewer or interviewer.active:
        failures.append("unavailable interviewer condition")

    row = evidence.get("ANOM-00002")
    if not row or row.expected_result != "duplicate attempt rejected":
        failures.append("duplicate attempt evidence")
    elif session.scalar(select(Application.id).where(
        Application.requisition_id == row.requisition_id,
        Application.candidate_id == row.candidate_id,
    )) is None:
        failures.append("duplicate attempt application pair")
    elif session.scalar(select(func.count()).select_from(Application).where(
        Application.requisition_id == row.requisition_id,
        Application.candidate_id == row.candidate_id,
    )) != 1:
        failures.append("duplicate attempt pair cardinality")

    row = evidence.get("ANOM-00003")
    interview = session.get(Interview, row.interview_id) if row else None
    if (
        not row or not interview or interview.status != "Completed"
        or session.scalar(select(Feedback.id).where(Feedback.interview_id == interview.id)) is not None
    ):
        failures.append("missing feedback condition")

    row = evidence.get("ANOM-00004")
    offer = session.get(Offer, row.offer_id) if row else None
    application = session.get(Application, offer.application_id) if offer else None
    requisition = session.get(JobRequisition, application.requisition_id) if application else None
    if not offer or not requisition or requisition.min_salary <= offer.salary <= requisition.max_salary:
        failures.append("salary outside band condition")

    row = evidence.get("ANOM-00005")
    requisition = session.get(JobRequisition, row.requisition_id) if row else None
    active_application = session.scalar(select(Application.id).where(
        Application.id == (row.application_id if row else None),
        Application.status.not_in(["Rejected", "Withdrawn"]),
    ))
    if not requisition or requisition.status != "Closed" or not active_application:
        failures.append("closed requisition active application condition")
    remaining_active = session.scalars(select(Application.id).where(
        Application.requisition_id == (row.requisition_id if row else None),
        Application.status.not_in(["Rejected", "Withdrawn"]),
    )).all()
    if row and set(remaining_active) != {row.application_id}:
        failures.append("unlabelled active applications under closed requisition")

    rejection_events = session.scalars(select(ApplicationEvent).where(
        ApplicationEvent.application_id.in_(
            select(Application.id).where(
                Application.requisition_id == TARGET_CLOSED_REQUISITION_ID,
                Application.id != TARGET_LABELLED_APPLICATION_ID,
                Application.status == "Rejected",
            )
        ),
        ApplicationEvent.to_status == "Rejected",
        ApplicationEvent.changed_by == "anomaly-repair",
        ApplicationEvent.changed_at == REPAIR_TIMESTAMP,
    )).all()
    rejection_audits = session.scalars(select(AuditLog).where(
        AuditLog.actor == "anomaly-repair",
        AuditLog.action == "STATUS_CHANGE",
        AuditLog.entity_type == "Application",
        AuditLog.entity_id.in_({event.application_id for event in rejection_events}),
        AuditLog.details.like("% (ANOM-00005 cleanup)"),
        AuditLog.occurred_at == REPAIR_TIMESTAMP,
    )).all()
    rejection_event_ids = {event.application_id for event in rejection_events}
    rejection_audit_ids = {audit.entity_id for audit in rejection_audits}
    if (
        len(rejection_events) != TARGET_REJECTION_COUNT
        or len(rejection_audits) != TARGET_REJECTION_COUNT
        or rejection_event_ids != rejection_audit_ids
        or len(rejection_event_ids) != TARGET_REJECTION_COUNT
    ):
        failures.append("exactly one rejection event and audit entry per transitioned application")
    reconciliation_violations = []
    for offer in session.scalars(select(Offer)).all():
        application = session.get(Application, offer.application_id)
        if application and application.status not in {"Offer Pending", "Offer Released", "Hired"}:
            reconciliation_violations.append(offer.id)
    if reconciliation_violations:
        failures.append(
            "offer reconciliation violations: " + ", ".join(reconciliation_violations)
        )
    return failures


def repair(dry_run: bool) -> dict[str, Any]:
    _require_challenge_database(DATABASE_URL)
    engine = None
    session = None
    try:
        engine = make_engine(DATABASE_URL)
        session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
        closed_requisition = _assert_preconditions(session)
        plan = _planned_changes(session, closed_requisition)
        if dry_run:
            session.rollback()
            return {"mode": "dry-run", "changes": plan, "committed": False}

        session.rollback()
        with session.begin():
            closed_requisition = _assert_preconditions(session)
            _apply_changes(session, closed_requisition)
            session.flush()
            failures = _verify_conditions(session)
            if failures:
                raise RuntimeError("Post-change verification failed: " + "; ".join(failures))
        return {"mode": "apply", "changes": plan, "committed": True}
    except Exception:
        if session is not None:
            session.rollback()
        raise
    finally:
        try:
            if session is not None:
                session.close()
        finally:
            if engine is not None:
                engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair stale challenge anomaly fixtures safely")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    modes.add_argument("--apply", action="store_true", help="Apply one verified transaction")
    args = parser.parse_args()
    result = repair(dry_run=args.dry_run)
    print(f"Mode: {result['mode']}")
    for change in result["changes"]:
        print(f"- {change}")
    print(f"Database committed: {result['committed']}")


if __name__ == "__main__":
    main()
