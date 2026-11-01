from sqlalchemy import delete

from backend.database.models import (
    Anomaly,
    AnomalyFixtureEvidence,
    Application,
    ApplicationEvent,
    Feedback,
    Interviewer,
    JobRequisition,
)


def create_ground_truth(session, applications, interviews, offers, requisitions, seed: int) -> None:
    if seed != 20261022:
        raise ValueError("Anomaly fixtures require deterministic seed 20261022")

    ordered_applications = sorted(applications, key=lambda row: row.id)
    ordered_interviews = sorted(interviews, key=lambda row: row.id)
    ordered_offers = sorted(offers, key=lambda row: row.id)
    offers_by_application = {offer.application_id: offer for offer in offers}

    duplicate_application = ordered_applications[0]
    duplicate_requisition = session.get(JobRequisition, duplicate_application.requisition_id)

    missing_feedback_interview = next(
        interview for interview in ordered_interviews
        if interview.application_id not in offers_by_application
    )
    missing_feedback_application = session.get(Application, missing_feedback_interview.application_id)
    missing_feedback_interview.status = "Completed"
    missing_feedback_application.status = "Interview Completed"
    session.execute(delete(Feedback).where(Feedback.interview_id == missing_feedback_interview.id))
    session.add(ApplicationEvent(
        application_id=missing_feedback_application.id,
        from_status="Interview Scheduled",
        to_status="Interview Completed",
        changed_by="anomaly-fixture",
    ))

    unavailable_interview = ordered_interviews[0]
    unavailable_interviewer = session.get(Interviewer, unavailable_interview.interviewer_id)
    unavailable_interviewer.active = False

    outside_band_offer = ordered_offers[0]
    outside_band_application = session.get(Application, outside_band_offer.application_id)
    outside_band_requisition = session.get(JobRequisition, outside_band_application.requisition_id)
    outside_band_offer.salary = outside_band_requisition.max_salary + 5000
    outside_band_offer.status = "Pending Approval"
    outside_band_offer.approved_by = None
    outside_band_offer.released_at = None

    closed_requisition_application = next(
        application for application in ordered_applications
        if application.status not in {"Rejected", "Withdrawn"}
    )
    closed_requisition = session.get(JobRequisition, closed_requisition_application.requisition_id)
    closed_requisition.status = "Closed"

    cases = [
        (
            "ANOM-00001", "Unavailable interviewer", unavailable_interview.id,
            "Scheduling must be rejected", "positive", "High",
            "The linked interviewer is inactive.",
        ),
        (
            "ANOM-00002", "Duplicate application", duplicate_application.id,
            "Second application must be rejected", "positive", "Medium",
            "A duplicate attempt is represented without inserting a second application row.",
        ),
        (
            "ANOM-00003", "Missing interview feedback", missing_feedback_application.id,
            "Stage transition must be blocked", "positive", "High",
            "The application is at Interview Completed while its completed interview has no feedback.",
        ),
        (
            "ANOM-00004", "Offer salary outside band", outside_band_offer.id,
            "Offer approval must be rejected", "positive", "High",
            "The pending offer salary exceeds the requisition maximum.",
        ),
        (
            "ANOM-00005", "Closed requisition with active applications", closed_requisition.id,
            "Exception must be reported", "positive", "Medium",
            "The closed requisition retains an active application.",
        ),
    ]
    for row in cases:
        session.add(Anomaly(
            issue_id=row[0], issue_type=row[1], entity_id=row[2],
            expected_outcome=row[3], ground_truth=row[4], severity=row[5],
            description=row[6],
        ))
    session.flush()
    session.add_all([
        AnomalyFixtureEvidence(
            issue_id="ANOM-00001",
            interview_id=unavailable_interview.id,
            interviewer_id=unavailable_interview.interviewer_id,
            expected_result="inactive interviewer",
            details="Scheduling must reject the interview because the assigned interviewer is inactive.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00002",
            requisition_id=duplicate_requisition.id,
            candidate_id=duplicate_application.candidate_id,
            application_id=duplicate_application.id,
            expected_result="duplicate attempt rejected",
            details="The existing unique application pair is referenced; no duplicate row is inserted.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00003",
            application_id=missing_feedback_application.id,
            interview_id=missing_feedback_interview.id,
            expected_result="completed interview feedback missing",
            details="The application is advanced while the completed interview has no feedback row.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00004",
            requisition_id=outside_band_requisition.id,
            application_id=outside_band_application.id,
            offer_id=outside_band_offer.id,
            expected_result="salary outside approved band",
            details="The pending offer salary is above the requisition maximum salary.",
        ),
        AnomalyFixtureEvidence(
            issue_id="ANOM-00005",
            requisition_id=closed_requisition.id,
            application_id=closed_requisition_application.id,
            expected_result="closed requisition has active application",
            details="The requisition is closed while the linked application remains active.",
        ),
    ])
