import argparse
import json
from pathlib import Path
import pandas as pd
from sqlalchemy import inspect, select, text
from backend.config import EXPORT_DIR
from backend.database.connection import SessionLocal, init_db
from backend.database.models import (
    Anomaly, AnomalyFixtureEvidence, Application, ApplicationEvent, Candidate, Feedback,
    Interview, Interviewer, JobRequisition, Offer
)

ALLOWED_APPLICATION_STATUSES = {"Applied", "Screening", "Shortlisted", "Interview Scheduled",
                                "Interview Completed", "Selected", "Offer Pending", "Offer Released",
                                "Hired", "Rejected", "Withdrawn"}
ALLOWED_OFFER_STATUSES = {"Pending Approval", "Approved", "Released", "Accepted", "Rejected", "Expired", "Withdrawn"}
ALLOWED_INTERVIEW_STATUSES = {"Scheduled", "Completed", "Cancelled", "Rescheduled"}
ALLOWED_RECOMMENDATIONS = {"Strong Hire", "Hire", "Hold", "Reject"}
VALID_TRANSITIONS = {
    "Applied": {"Screening", "Withdrawn", "Rejected"}, "Screening": {"Shortlisted", "Rejected", "Withdrawn"},
    "Shortlisted": {"Interview Scheduled", "Rejected", "Withdrawn"},
    "Interview Scheduled": {"Interview Completed", "Withdrawn"},
    "Interview Completed": {"Selected", "Rejected", "Withdrawn"}, "Selected": {"Offer Pending", "Rejected"},
    "Offer Pending": {"Offer Released", "Rejected"}, "Offer Released": {"Hired", "Withdrawn"},
    "Hired": set(), "Rejected": set(), "Withdrawn": set()
}

def validate(session=None, expected_counts=None):
    own = session is None
    if own:
        init_db()
        session = SessionLocal()
    checks = []

    def check(name, passed, severity="High", ids=""):
        checks.append({"check": name, "passed": bool(passed), "severity": severity, "affected_ids": ids})

    inspector = inspect(session.bind)
    quote = session.bind.dialect.identifier_preparer.quote
    for table in inspector.get_table_names():
        pk = inspector.get_pk_constraint(table)["constrained_columns"]
        duplicate = session.execute(text(
            f'SELECT {", ".join(quote(column) for column in pk)}, COUNT(*) n '
            f'FROM {quote(table)} GROUP BY {", ".join(quote(column) for column in pk)} HAVING n > 1'
        )).all() if pk else []
        check(f"Primary-key uniqueness: {table}", not duplicate, "Critical", str(duplicate))

    fk_errors = []
    for table in inspector.get_table_names():
        for foreign_key in inspector.get_foreign_keys(table):
            parent = foreign_key["referred_table"]
            pairs = zip(foreign_key["constrained_columns"], foreign_key["referred_columns"])
            join = " AND ".join(
                f"child.{quote(child)} = parent.{quote(parent_column)}"
                for child, parent_column in pairs
            )
            nullable = " AND ".join(f"child.{quote(child)} IS NOT NULL" for child in foreign_key["constrained_columns"])
            fk_errors.extend(session.execute(text(
                f"SELECT child.{quote(foreign_key['constrained_columns'][0])} "
                f"FROM {quote(table)} child LEFT JOIN {quote(parent)} parent ON {join} "
                f"WHERE {nullable} AND parent.{quote(foreign_key['referred_columns'][0])} IS NULL LIMIT 20"
            )).all())
    check("Foreign-key integrity", not fk_errors, "Critical", str(fk_errors))

    for table in inspector.get_table_names():
        nullable = [c["name"] for c in inspector.get_columns(table) if not c["nullable"] and not c["default"]]
        missing = []
        if nullable:
            missing = session.execute(text(
                f'SELECT * FROM {quote(table)} WHERE '
                + " OR ".join(f'{quote(c)} IS NULL' for c in nullable)
                + " LIMIT 20"
            )).all()
        check(f"Mandatory fields: {table}", not missing, "High", str(missing))

    apps = session.scalars(select(Application)).all()
    invalid_apps = [a.id for a in apps if a.status not in ALLOWED_APPLICATION_STATUSES or a.id != f"APP-{a.requisition_id}-{a.candidate_id}"]
    check("Application enumerations and derived IDs", not invalid_apps, "High", ",".join(invalid_apps[:20]))
    invalid_offers = [o.id for o in session.scalars(select(Offer)) if o.status not in ALLOWED_OFFER_STATUSES]
    check("Offer status enumeration", not invalid_offers, "High", ",".join(invalid_offers[:20]))
    invalid_interviews = [i.id for i in session.scalars(select(Interview)) if i.status not in ALLOWED_INTERVIEW_STATUSES or i.ends_at <= i.starts_at]
    check("Interview enumerations and date ordering", not invalid_interviews, "High", ",".join(invalid_interviews[:20]))
    invalid_feedback = [f.id for f in session.scalars(select(Feedback)) if f.recommendation not in ALLOWED_RECOMMENDATIONS or any(
        rating < 1 or rating > 5 for rating in [f.technical_rating, f.problem_solving_rating, f.communication_rating, f.role_skills_rating])]
    check("Feedback enumerations and rating ranges", not invalid_feedback, "High", ",".join(invalid_feedback[:20]))

    duplicates = session.execute(text(
        f"SELECT {quote('requisition_id')}, {quote('candidate_id')}, COUNT(*) n "
        f"FROM {quote('applications')} GROUP BY {quote('requisition_id')},{quote('candidate_id')} HAVING n > 1"
    )).all()
    check("Duplicate applications", not duplicates, "High", str(duplicates))

    conflicts = session.execute(text(
        f"SELECT a.{quote('id')}, b.{quote('id')} FROM {quote('interviews')} a JOIN {quote('interviews')} b ON a.{quote('interviewer_id')}=b.{quote('interviewer_id')} "
        "AND a.id < b.id AND a.status IN ('Scheduled','Completed') AND b.status IN ('Scheduled','Completed') "
        f"AND a.{quote('starts_at')} < b.{quote('ends_at')} AND b.{quote('starts_at')} < a.{quote('ends_at')}"
    )).all()
    check("Interview scheduling conflicts", not conflicts, "High", str(conflicts))

    excluded_interview_ids = {
        evidence.interview_id for evidence in session.scalars(select(AnomalyFixtureEvidence))
        if evidence.issue_id == "ANOM-00003" and evidence.interview_id
    }
    completed_without_feedback = session.execute(text(
        f"SELECT i.{quote('id')} FROM {quote('interviews')} i LEFT JOIN {quote('feedback')} f ON f.{quote('interview_id')}=i.{quote('id')} "
        f"WHERE i.{quote('status')}='Completed' AND f.{quote('id')} IS NULL"
    )).all()
    completed_without_feedback = [
        row for row in completed_without_feedback if row[0] not in excluded_interview_ids
    ]
    check("Missing feedback for completed interviews", not completed_without_feedback, "High", str(completed_without_feedback))

    invalid_events = []
    for event in session.scalars(select(ApplicationEvent)).all():
        if event.from_status is not None and event.to_status not in VALID_TRANSITIONS.get(event.from_status, set()):
            invalid_events.append(event.id)
    check("Lifecycle transition validity", not invalid_events, "High", ",".join(map(str, invalid_events[:20])))

    excluded_offer_ids = {
        evidence.offer_id for evidence in session.scalars(select(AnomalyFixtureEvidence))
        if evidence.issue_id == "ANOM-00004" and evidence.offer_id
    }
    bad_salary = []
    missing_approval = []
    bad_reconciliation = []
    for offer in session.scalars(select(Offer)).all():
        app = session.get(Application, offer.application_id)
        req = session.get(JobRequisition, app.requisition_id) if app else None
        if req and not req.min_salary <= offer.salary <= req.max_salary and offer.id not in excluded_offer_ids:
            bad_salary.append(offer.id)
        if offer.status in {"Approved", "Released", "Accepted"} and not offer.approved_by:
            missing_approval.append(offer.id)
        if app and app.status not in {"Offer Pending", "Offer Released", "Hired"}:
            bad_reconciliation.append(offer.id)
    check("Offer salary bands", not bad_salary, "High", ",".join(bad_salary[:20]))
    check("Offer approval compliance", not missing_approval, "High", ",".join(missing_approval[:20]))
    check("Application and offer reconciliation", not bad_reconciliation, "High", ",".join(bad_reconciliation[:20]))

    excluded_closed_requisition_ids = {
        evidence.requisition_id for evidence in session.scalars(select(AnomalyFixtureEvidence))
        if evidence.issue_id == "ANOM-00005" and evidence.requisition_id
    }
    closed_ids = [r.id for r in session.scalars(select(JobRequisition).where(JobRequisition.status == "Closed"))
                  if r.id not in excluded_closed_requisition_ids and session.scalar(
                      select(Application.id).where(
                          Application.requisition_id == r.id,
                          Application.status.not_in(["Rejected", "Withdrawn"]),
                      )
                  ) is not None]
    check("Closed requisitions with active applications", not closed_ids, "Medium", ",".join(closed_ids))

    if expected_counts:
        count_failures = []
        for table, expected in expected_counts.items():
            actual = session.execute(text(f'SELECT COUNT(*) FROM {quote(table)}')).scalar_one()
            if actual != expected:
                count_failures.append(f"{table}={actual}, expected={expected}")
        check("Expected record counts", not count_failures, "Critical", "; ".join(count_failures))
    else:
        for table in ["departments", "job_requisitions", "candidates", "applications", "interviews", "offers"]:
            count = session.execute(text(f'SELECT COUNT(*) FROM {quote(table)}')).scalar_one()
            check(f"{table} has records", count > 0, "Low")

    ordinary_checks = list(checks)
    expected_anomaly_types = {
        "Unavailable interviewer",
        "Duplicate application",
        "Missing interview feedback",
        "Offer salary outside band",
        "Closed requisition with active applications",
    }
    anomalies = session.scalars(select(Anomaly)).all()
    evidence = {row.issue_id: row for row in session.scalars(select(AnomalyFixtureEvidence)).all()}
    anomaly_failures = []
    if len(anomalies) != 5 or {row.issue_type for row in anomalies} != expected_anomaly_types:
        anomaly_failures.append("expected five anomaly labels")
    anomaly_ids = {row.issue_id for row in anomalies}
    if (
        any(row.ground_truth != "positive" or row.issue_id not in evidence for row in anomalies)
        or set(evidence) != anomaly_ids
    ):
        anomaly_failures.append("positive labels must have evidence")

    def evidence_condition(issue_type):
        row = next((item for item in anomalies if item.issue_type == issue_type), None)
        fixture = evidence.get(row.issue_id) if row else None
        if not fixture:
            return False
        if issue_type == "Unavailable interviewer":
            interviewer = session.get(Interviewer, fixture.interviewer_id)
            return bool(interviewer and not interviewer.active)
        if issue_type == "Duplicate application":
            count = session.execute(text(
                f"SELECT COUNT(*) FROM {quote('applications')} WHERE "
                f"{quote('requisition_id')} = :requisition_id AND {quote('candidate_id')} = :candidate_id"
            ), {"requisition_id": fixture.requisition_id, "candidate_id": fixture.candidate_id}).scalar_one()
            return count == 1 and fixture.expected_result == "duplicate attempt rejected"
        if issue_type == "Missing interview feedback":
            interview = session.get(Interview, fixture.interview_id)
            return bool(
                interview and interview.status == "Completed"
                and session.scalar(select(Feedback.id).where(Feedback.interview_id == interview.id)) is None
            )
        if issue_type == "Offer salary outside band":
            offer = session.get(Offer, fixture.offer_id)
            app = session.get(Application, offer.application_id) if offer else None
            req = session.get(JobRequisition, app.requisition_id) if app else None
            return bool(offer and req and (offer.salary < req.min_salary or offer.salary > req.max_salary))
        if issue_type == "Closed requisition with active applications":
            req = session.get(JobRequisition, fixture.requisition_id)
            active = session.scalar(select(Application.id).where(
                Application.requisition_id == fixture.requisition_id,
                Application.status.not_in(["Rejected", "Withdrawn"]),
            ))
            return bool(req and req.status == "Closed" and active)
        return False

    for anomaly_type in expected_anomaly_types:
        if not evidence_condition(anomaly_type):
            anomaly_failures.append(anomaly_type)
    check("Intentional anomaly fixtures", not anomaly_failures, "High", "; ".join(anomaly_failures))
    check(
        "Unlabelled data-quality violations",
        not any(not item["passed"] for item in ordinary_checks),
        "Critical",
        "; ".join(item["check"] for item in ordinary_checks if not item["passed"]),
    )

    frame = pd.DataFrame(checks)
    EXPORT_DIR.mkdir(exist_ok=True)
    frame.to_csv(EXPORT_DIR / "validation_summary.csv", index=False)
    (EXPORT_DIR / "validation_report.json").write_text(json.dumps({
        "checks": checks, "passed": sum(x["passed"] for x in checks),
        "failed": sum(not x["passed"] for x in checks)
    }, indent=2), encoding="utf-8")
    if own:
        session.close()
    return checks

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", choices=["starter", "full"], default="starter")
    args = parser.parse_args()
    counts = {"job_requisitions": 100, "candidates": 2000, "applications": 3000, "interviews": 600, "offers": 150} if args.size == "full" else None
    results = validate(expected_counts=counts)
    print(results)
