from datetime import datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

class JobRequisition(TimestampMixin, Base):
    __tablename__ = "job_requisitions"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    openings: Mapped[int] = mapped_column(Integer, nullable=False)
    min_experience: Mapped[int] = mapped_column(Integer, default=0)
    max_experience: Mapped[int] = mapped_column(Integer, default=20)
    min_salary: Mapped[float] = mapped_column(Float, nullable=False)
    max_salary: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="Draft", index=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime)

class Candidate(TimestampMixin, Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    education: Mapped[str] = mapped_column(String(150), nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)

class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    requisition_id: Mapped[str] = mapped_column(ForeignKey("job_requisitions.id"), index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    status: Mapped[str] = mapped_column(String(35), default="Applied", index=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    screening_score: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (UniqueConstraint("requisition_id", "candidate_id", name="uq_application_pair"),)

class ResumeArtifact(TimestampMixin, Base):
    __tablename__ = "resume_artifacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class Skill(TimestampMixin, Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    proficiency: Mapped[str] = mapped_column(String(20), default="Intermediate")

class ScreeningRule(TimestampMixin, Base):
    __tablename__ = "screening_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    requisition_id: Mapped[str] = mapped_column(ForeignKey("job_requisitions.id"), index=True)
    required_skills: Mapped[str] = mapped_column(Text, default="")
    preferred_skills: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Interviewer(TimestampMixin, Base):
    __tablename__ = "interviewers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("interviewers.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(25), default="Scheduled")

class Feedback(TimestampMixin, Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interviews.id"), index=True)
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("interviewers.id"))
    technical_rating: Mapped[int] = mapped_column(Integer)
    problem_solving_rating: Mapped[int] = mapped_column(Integer)
    communication_rating: Mapped[int] = mapped_column(Integer)
    role_skills_rating: Mapped[int] = mapped_column(Integer)
    overall_rating: Mapped[float] = mapped_column(Float)
    strengths: Mapped[str] = mapped_column(Text, default="")
    weaknesses: Mapped[str] = mapped_column(Text, default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)

class Offer(TimestampMixin, Base):
    __tablename__ = "offers"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), unique=True)
    salary: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(25), default="Pending Approval", index=True)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    released_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

class ApplicationEvent(Base):
    __tablename__ = "application_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(35))
    to_status: Mapped[str] = mapped_column(String(35))
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class ApprovalHistory(Base):
    __tablename__ = "approval_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(60), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    approver: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(60), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

class Anomaly(Base):
    __tablename__ = "anomalies"
    issue_id: Mapped[str] = mapped_column(String(25), primary_key=True)
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(60), nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    ground_truth: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

class AnomalyFixtureEvidence(Base):
    __tablename__ = "anomaly_fixture_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("anomalies.issue_id"), unique=True, index=True)
    requisition_id: Mapped[str | None] = mapped_column(ForeignKey("job_requisitions.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), index=True)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), index=True)
    interview_id: Mapped[str | None] = mapped_column(ForeignKey("interviews.id"), index=True)
    interviewer_id: Mapped[int | None] = mapped_column(ForeignKey("interviewers.id"), index=True)
    offer_id: Mapped[str | None] = mapped_column(ForeignKey("offers.id"), index=True)
    expected_result: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ExceptionResolution(Base):
    __tablename__ = "exception_resolutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("anomalies.issue_id"), index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

Index("ix_interview_window", Interview.interviewer_id, Interview.starts_at, Interview.ends_at)
