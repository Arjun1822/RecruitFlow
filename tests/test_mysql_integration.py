import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.database.connection import make_session
from backend.database.models import Application, Candidate, Department, JobRequisition


def test_mysql_connection_crud_foreign_keys_and_transactions(mysql_database_url):
    database_url = mysql_database_url

    session = make_session(database_url)
    engine = session.get_bind()
    department_id = 910001
    requisition_id = "MYSQL-REQ-TEST-001"
    candidate_id = "MYSQL-CAND-TEST-001"
    application_id = "MYSQL-APP-TEST-001"

    def remove_test_records() -> None:
        session.execute(delete(Application).where(Application.id == application_id))
        session.execute(
            delete(JobRequisition).where(JobRequisition.id == requisition_id)
        )
        session.execute(delete(Candidate).where(Candidate.id == candidate_id))
        session.execute(delete(Department).where(Department.id == department_id))
        session.commit()

    try:
        assert engine.connect().exec_driver_sql("SELECT 1").scalar_one() == 1
        remove_test_records()

        # Insert parents first and flush each one before creating its children.
        department = Department(
            id=department_id,
            name="MySQL Integration Department",
            description="Isolated integration-test record",
        )
        session.add(department)
        session.flush()
        assert session.scalar(
            select(Department.id).where(Department.id == department_id)
        ) == department_id

        requisition = JobRequisition(
            id=requisition_id,
            department_id=department_id,
            title="MySQL Integration Engineer",
            openings=1,
            min_experience=1,
            max_experience=10,
            min_salary=50000,
            max_salary=100000,
            location="Remote",
            status="Approved",
            requested_by="mysql-test",
        )
        session.add(requisition)
        session.flush()
        assert session.scalar(
            select(JobRequisition.id).where(JobRequisition.id == requisition_id)
        ) == requisition_id

        candidate = Candidate(
            id=candidate_id,
            first_name="MySQL",
            last_name="Candidate",
            email="mysql.integration.test@example.test",
            phone="+1-555-0199",
            education="BSc",
            years_experience=3,
            location="Remote",
        )
        session.add(candidate)
        session.flush()
        assert session.scalar(
            select(Candidate.id).where(Candidate.id == candidate_id)
        ) == candidate_id

        application = Application(
            id=application_id,
            requisition_id=requisition_id,
            candidate_id=candidate_id,
            status="Applied",
        )
        session.add(application)
        session.flush()
        assert session.scalar(
            select(Application.id).where(Application.id == application_id)
        ) == application_id
        session.commit()

        stored = session.get(Application, application_id)
        assert stored is not None
        stored.status = "Screening"
        session.commit()
        assert session.get(Application, application_id).status == "Screening"

        # An invalid requisition must be rejected while FK checks remain enabled.
        invalid_requisition = Application(
            id="MYSQL-APP-INVALID-REQ",
            requisition_id="MYSQL-REQ-NOT-FOUND",
            candidate_id=candidate_id,
            status="Applied",
        )
        session.add(invalid_requisition)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        # An invalid candidate must also be rejected.
        invalid_candidate = Application(
            id="MYSQL-APP-INVALID-CAND",
            requisition_id=requisition_id,
            candidate_id="MYSQL-CAND-NOT-FOUND",
            status="Applied",
        )
        session.add(invalid_candidate)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        session.execute(delete(Application).where(Application.id == application_id))
        session.commit()
        assert session.get(Application, application_id) is None
    finally:
        remove_test_records()
        session.close()
        engine.dispose()
