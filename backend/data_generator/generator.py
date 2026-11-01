import argparse
import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import delete, select

from backend.config import SEED
from backend.database.connection import make_session
from backend.database.models import (
    Anomaly,
    AnomalyFixtureEvidence,
    Application,
    ApplicationEvent,
    ApprovalHistory,
    AuditLog,
    Candidate,
    CandidateSkill,
    Department,
    Feedback,
    Interview,
    Interviewer,
    JobRequisition,
    Offer,
    ResumeArtifact,
    ScreeningRule,
    Skill,
)
from .anomaly_generator import create_ground_truth
from .export_data import export_database
from .master_data import DEPARTMENTS, LOCATIONS, ROLES, SKILLS


def generate_dataset(size="starter", seed=SEED, export=True, database_url=None):
    counts = {"starter": (10, 100, 150, 40, 12), "full": (100, 2000, 3000, 600, 150)}
    req_n, cand_n, app_n, int_n, offer_n = counts[size]
    random.seed(seed)
    fake = Faker()
    fake.seed_instance(seed)
    generated_at = datetime(2026, 1, 1, 0, 0, 0)
    session = None
    engine = None
    database_committed = False
    try:
        session = make_session(database_url) if database_url else make_session()
        engine = session.get_bind()
        for model in [
            AuditLog, ApprovalHistory, ApplicationEvent, Feedback, Interview, Offer,
            ScreeningRule, CandidateSkill, ResumeArtifact, Application, Candidate,
            JobRequisition, Interviewer, Skill, Department,
        ]:
            session.execute(delete(model))
        session.execute(delete(AnomalyFixtureEvidence))
        session.execute(delete(Anomaly))
        session.commit()

        departments = [Department(name=n, description=f"{n} department") for n in DEPARTMENTS]
        skills = [Skill(name=n) for n in SKILLS]
        session.add_all(departments + skills)
        session.flush()
        dept_map = {d.name: d for d in departments}
        skill_map = {s.name: s for s in skills}
        reqs = []
        for i in range(1, req_n + 1):
            dept = random.choice(DEPARTMENTS)
            min_exp = random.randint(0, 8)
            reqs.append(JobRequisition(
                id=f"REQ-2026-{i:06d}", department_id=dept_map[dept].id,
                title=random.choice(ROLES[dept]), openings=random.randint(1, 8),
                min_experience=min_exp, max_experience=min_exp + random.randint(2, 8),
                min_salary=random.randrange(40000, 100001, 5000), max_salary=0,
                location=random.choice(LOCATIONS), status=random.choice(["Approved", "Approved", "Closed"]),
                requested_by="requester@example.com", approved_by="approver@example.com",
                effective_from=generated_at, created_at=generated_at, updated_at=generated_at,
            ))
            reqs[-1].max_salary = reqs[-1].min_salary + random.randrange(20000, 80001, 5000)
        session.add_all(reqs)
        session.flush()
        session.add_all([
            ScreeningRule(requisition_id=r.id, required_skills=",".join(random.sample(SKILLS, 2)),
                          preferred_skills=",".join(random.sample(SKILLS, 2)))
            for r in reqs
        ])

        candidates = [
            Candidate(
                id=f"CAND-{i:06d}", first_name=fake.first_name(), last_name=fake.last_name(),
                email=f"candidate{i:06d}@example.test", phone=f"+91-90000-{i:05d}",
                education=random.choice(["B.Tech", "MBA", "B.Sc", "MCA"]),
                years_experience=random.randint(0, 15), location=random.choice(LOCATIONS),
            )
            for i in range(1, cand_n + 1)
        ]
        session.add_all(candidates)
        session.flush()
        session.add_all([
            CandidateSkill(candidate_id=c.id, skill_id=skill_map[s].id,
                           proficiency=random.choice(["Beginner", "Intermediate", "Advanced"]))
            for c in candidates for s in random.sample(SKILLS, random.randint(2, 5))
        ])
        session.add_all([
            ResumeArtifact(candidate_id=c.id, filename=f"{c.id}.pdf", storage_path=f"resumes/{c.id}.pdf")
            for c in candidates
        ])

        apps = []
        used = set()
        eligible_reqs = [r for r in reqs if r.status == "Approved"]
        while len(apps) < app_n:
            r = random.choice(eligible_reqs)
            c = random.choice(candidates)
            pair = (r.id, c.id)
            if pair in used:
                continue
            used.add(pair)
            apps.append(Application(
                id=f"APP-{r.id}-{c.id}", requisition_id=r.id, candidate_id=c.id,
                status=random.choice(["Applied", "Screening", "Shortlisted", "Rejected", "Withdrawn", "Selected"]),
                applied_at=generated_at - timedelta(days=random.randint(1, 180)),
                screening_score=round(random.uniform(35, 98), 2),
                created_at=generated_at, updated_at=generated_at,
            ))
        session.add_all(apps)
        session.flush()
        session.add_all([
            ApplicationEvent(application_id=a.id, from_status=None, to_status="Applied", changed_by="seed")
            for a in apps
        ])

        interviewers = [
            Interviewer(name=fake.name(), email=f"interviewer{i:04d}@example.test",
                        department_id=random.choice(departments).id)
            for i in range(max(20, min(100, int_n // 3 + 1)))
        ]
        session.add_all(interviewers)
        session.flush()
        interviews = []
        for i in range(1, int_n + 1):
            a = random.choice(apps)
            person = interviewers[(i - 1) % len(interviewers)]
            start = generated_at + timedelta(days=(i - 1) // len(interviewers), hours=9)
            interviews.append(Interview(
                id=f"INT-2026-{i:06d}", application_id=a.id, interviewer_id=person.id,
                round_number=random.randint(1, 3), starts_at=start, ends_at=start + timedelta(hours=1),
                status=random.choice(["Scheduled", "Completed", "Cancelled"]),
            ))
        session.add_all(interviews)
        session.flush()
        for iv in interviews:
            if iv.status == "Completed":
                ratings = [random.randint(1, 5) for _ in range(4)]
                session.add(Feedback(
                    id=f"FB-{iv.id}-{iv.interviewer_id}", interview_id=iv.id,
                    interviewer_id=iv.interviewer_id, technical_rating=ratings[0],
                    problem_solving_rating=ratings[1], communication_rating=ratings[2],
                    role_skills_rating=ratings[3], overall_rating=round(sum(ratings) / 4, 2),
                    recommendation=random.choice(["Strong Hire", "Hire", "Hold", "Reject"]),
                    strengths="Structured thinking", weaknesses="Needs domain context",
                    comments="Synthetic evaluation",
                ))

        offers = []
        for i in range(1, min(offer_n, len(apps)) + 1):
            a = apps[i - 1]
            r = next(x for x in reqs if x.id == a.requisition_id)
            a.status = "Offer Pending"
            a.updated_at = generated_at
            offer_status = random.choice(["Pending Approval", "Accepted", "Rejected"])
            offers.append(Offer(
                id=f"OFF-2026-{i:06d}", application_id=a.id,
                salary=random.uniform(r.min_salary, r.max_salary), status=offer_status,
                approved_by="approver@example.com" if offer_status == "Accepted" else None,
                released_at=generated_at if offer_status == "Accepted" else None,
                expires_at=generated_at + timedelta(days=30),
            ))
        session.add_all(offers)
        session.flush()
        session.add_all([
            ApprovalHistory(entity_type="Requisition", entity_id=r.id, decision="Approved",
                            approver="approver@example.com", decided_at=generated_at)
            for r in reqs if r.status == "Approved"
        ])
        session.add(AuditLog(actor="seed", action="CREATE", entity_type="Dataset",
                             entity_id="seed", details=f"seed={seed}", occurred_at=generated_at))
        if apps and interviews and offers:
            create_ground_truth(session, apps, interviews, offers, reqs, seed)

        for model in [
            Department, JobRequisition, Candidate, ResumeArtifact, Skill, ScreeningRule,
            Interviewer, Interview, Feedback, Offer, Application,
        ]:
            for record in session.scalars(select(model)):
                record.created_at = generated_at
                record.updated_at = generated_at
                if isinstance(record, ResumeArtifact):
                    record.uploaded_at = generated_at
        for record in session.scalars(select(ApplicationEvent)):
            record.changed_at = generated_at
        for record in session.scalars(select(ApprovalHistory)):
            record.decided_at = generated_at

        session.commit()
        database_committed = True
        result = {
            "requisitions": len(reqs), "candidates": len(candidates),
            "applications": len(apps), "interviews": len(interviews), "offers": len(offers),
        }
        if export:
            try:
                export_database(session)
            except Exception as exc:
                raise RuntimeError(
                    "Dataset database commit succeeded, but export generation failed; "
                    "database records remain committed."
                ) from exc
        return result
    except Exception:
        if session is not None and not database_committed:
            session.rollback()
        raise
    finally:
        try:
            if session is not None:
                session.close()
        finally:
            if engine is not None:
                engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print(generate_dataset(args.size, args.seed))
