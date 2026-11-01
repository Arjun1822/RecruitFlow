import os
from sqlalchemy.engine import make_url

import pytest
from sqlalchemy import delete, select

from backend.database.models import Base
from backend.database.models import (
    Anomaly,
    AnomalyFixtureEvidence,
    Application,
    Feedback,
    Interview,
    Interviewer,
    JobRequisition,
    Offer,
)
ANOMALY_DATABASE_NAME = "recruitment_anomaly_test"
REJECTED_DATABASE_NAMES = {"rms", "rms_challenge"}


def _database_identity(url: str) -> tuple[str, str, int, str]:
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise ValueError("Database URL must be a valid SQLAlchemy URL") from exc
    if parsed.drivername != "mysql+pymysql" or not parsed.host or not parsed.database:
        raise ValueError("Database URL must include a MySQL scheme, host, and database")
    try:
        port = parsed.port or 3306
    except ValueError as exc:
        raise ValueError("Database URL must use a valid port") from exc
    return (
        parsed.drivername.lower(),
        parsed.host.lower(),
        port,
        parsed.database,
    )


def _clear_anomaly_database(session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(delete(table))
    session.commit()


@pytest.fixture(scope="module")
def anomaly_fixture_database_url():
    url = os.getenv("ANOMALY_FIXTURE_DATABASE_URL")
    if not url:
        pytest.fail("ANOMALY_FIXTURE_DATABASE_URL is required; no fallback is allowed")
    database_name = _database_identity(url)[3]
    if database_name != ANOMALY_DATABASE_NAME:
        raise ValueError(
            "ANOMALY_FIXTURE_DATABASE_URL must target exactly "
            f"{ANOMALY_DATABASE_NAME}"
        )
    anomaly_identity = _database_identity(url)
    rejected_urls = [os.getenv("DATABASE_URL"), os.getenv("MYSQL_TEST_URL")]
    for rejected_url in rejected_urls:
        if rejected_url and _database_identity(rejected_url) == anomaly_identity:
            raise ValueError("Anomaly fixture URL must not target an application or shared test database")
    if database_name in REJECTED_DATABASE_NAMES:
        raise ValueError("Anomaly fixture URL targets a protected database")
    return url


@pytest.fixture(autouse=True)
def isolate_anomaly_database(anomaly_fixture_database_url):
    from backend.database.connection import make_session

    session = None
    engine = None
    try:
        session = make_session(anomaly_fixture_database_url)
        engine = session.get_bind()
        _clear_anomaly_database(session)
        yield
    finally:
        try:
            if session is not None:
                try:
                    session.rollback()
                finally:
                    try:
                        _clear_anomaly_database(session)
                    finally:
                        session.close()
        finally:
            if engine is not None:
                engine.dispose()


def _seed_anomaly_database(anomaly_fixture_database_url):
    from backend.data_generator.generator import generate_dataset
    from backend.database.connection import make_session

    generate_dataset(
        "full",
        seed=20261022,
        export=False,
        database_url=anomaly_fixture_database_url,
    )
    session = make_session(anomaly_fixture_database_url)
    return session


def test_seeded_anomaly_fixtures_are_genuine_and_labelled(anomaly_fixture_database_url):
    from backend.validation.validator import validate

    session = _seed_anomaly_database(anomaly_fixture_database_url)
    try:
        anomalies = session.scalars(select(Anomaly).order_by(Anomaly.issue_id)).all()
        evidence = {
            row.issue_id: row
            for row in session.scalars(select(AnomalyFixtureEvidence)).all()
        }
        assert len(anomalies) == 5
        assert all(row.ground_truth == "positive" for row in anomalies)
        assert {row.issue_id for row in anomalies} == set(evidence)
        assert len(evidence) == 5

        unavailable = evidence["ANOM-00001"]
        assert unavailable.interview_id is not None
        assert unavailable.interviewer_id is not None
        unavailable_interview = session.get(Interview, unavailable.interview_id)
        unavailable_interviewer = session.get(Interviewer, unavailable.interviewer_id)
        assert unavailable_interview is not None
        assert unavailable_interview.interviewer_id == unavailable.interviewer_id
        assert unavailable_interviewer is not None
        assert not unavailable_interviewer.active

        duplicate = evidence["ANOM-00002"]
        assert duplicate.requisition_id is not None
        assert duplicate.candidate_id is not None
        assert duplicate.application_id is not None
        duplicate_application = session.get(Application, duplicate.application_id)
        assert duplicate_application is not None
        assert duplicate_application.requisition_id == duplicate.requisition_id
        assert duplicate_application.candidate_id == duplicate.candidate_id
        assert session.query(Application).filter_by(
            requisition_id=duplicate.requisition_id,
            candidate_id=duplicate.candidate_id,
        ).count() == 1
        assert duplicate.expected_result == "duplicate attempt rejected"

        missing_feedback = evidence["ANOM-00003"]
        assert missing_feedback.application_id is not None
        assert missing_feedback.interview_id is not None
        missing_application = session.get(Application, missing_feedback.application_id)
        interview = session.get(Interview, missing_feedback.interview_id)
        assert missing_application is not None
        assert interview is not None
        assert interview.application_id == missing_application.id
        assert interview.status == "Completed"
        assert session.scalar(
            select(Feedback.id).where(Feedback.interview_id == interview.id)
        ) is None

        outside_band = evidence["ANOM-00004"]
        assert outside_band.offer_id is not None
        assert outside_band.application_id is not None
        assert outside_band.requisition_id is not None
        offer = session.get(Offer, outside_band.offer_id)
        application = session.get(Application, offer.application_id)
        requisition = session.get(JobRequisition, application.requisition_id)
        assert offer is not None
        assert application is not None
        assert requisition is not None
        assert offer.application_id == outside_band.application_id
        assert application.requisition_id == outside_band.requisition_id
        assert offer.salary > requisition.max_salary or offer.salary < requisition.min_salary

        closed = evidence["ANOM-00005"]
        assert closed.requisition_id is not None
        assert closed.application_id is not None
        requisition = session.get(JobRequisition, closed.requisition_id)
        closed_application = session.get(Application, closed.application_id)
        assert requisition is not None
        assert closed_application is not None
        assert closed_application.requisition_id == requisition.id
        assert requisition.status == "Closed"
        assert session.scalar(select(Application.id).where(
            Application.requisition_id == requisition.id,
            Application.status.not_in(["Rejected", "Withdrawn"]),
        )) is not None

        results = validate(session, expected_counts={
            "job_requisitions": 100,
            "candidates": 2000,
            "applications": 3000,
            "interviews": 600,
            "offers": 150,
        })
        assert all(item["passed"] for item in results)
    finally:
        engine = session.get_bind()
        session.close()
        engine.dispose()


def test_unlabelled_data_quality_violation_fails_validation(anomaly_fixture_database_url):
    from backend.validation.validator import validate

    session = _seed_anomaly_database(anomaly_fixture_database_url)
    try:
        labelled_offer_id = session.scalar(select(AnomalyFixtureEvidence.offer_id).where(
            AnomalyFixtureEvidence.issue_id == "ANOM-00004"
        ))
        unlabelled_offer = session.scalar(
            select(Offer).where(Offer.id != labelled_offer_id)
        )
        assert unlabelled_offer is not None
        positive_fixture_offer_ids = set(session.scalars(select(
            AnomalyFixtureEvidence.offer_id
        )).all())
        assert unlabelled_offer.id not in positive_fixture_offer_ids
        application = session.get(Application, unlabelled_offer.application_id)
        requisition = session.get(JobRequisition, application.requisition_id)
        unlabelled_offer.salary = requisition.max_salary + 5000
        session.flush()

        results = validate(session, expected_counts={
            "job_requisitions": 100,
            "candidates": 2000,
            "applications": 3000,
            "interviews": 600,
            "offers": 150,
        })
        result_by_name = {item["check"]: item for item in results}
        assert not result_by_name["Offer salary bands"]["passed"]
        assert not result_by_name["Unlabelled data-quality violations"]["passed"]
    finally:
        session.close()
