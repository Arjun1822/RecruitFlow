from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Any
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from backend.analytics.metrics import build_analytics_report, calculate_metrics
from backend.config import ADMIN_REGISTRATION_ENABLED, MAX_RESUME_BYTES, PRIVATE_UPLOAD_DIR, RMS_ENV
from backend.api.dependencies import get_current_user, get_db
from backend.authentication.auth_service import (
    admin_registration_available,
    authenticate,
    create_access_token,
    register_admin,
    require_permission,
)
from backend.database.models import (
    Application, ApplicationEvent, Candidate, Department, Feedback, Interview, Interviewer,
    JobRequisition, Offer, ResumeArtifact, User
)
from backend.services.application_service import apply_candidate, transition_application
from backend.services.interview_service import reschedule_interview, schedule_interview, update_interview_status
from backend.services.offer_service import approve_offer, create_offer, release_offer, update_offer_status
from backend.services.requisition_service import set_requisition_status
from backend.services.screening_service import screen_application
from backend.validation.validator import validate

app = FastAPI(title="Recruitment Management API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminRegistrationRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12)
    password_confirmation: str = Field(min_length=12)


class RequisitionCreate(BaseModel):
    department_id: int
    title: str = Field(min_length=1, max_length=150)
    openings: int = Field(default=1, ge=1)
    min_salary: float = Field(ge=0)
    max_salary: float = Field(ge=0)
    location: str = Field(min_length=1)


class CandidateCreate(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str
    phone: str
    education: str
    years_experience: int = Field(ge=0, le=60)
    location: str


class ApplicationCreate(BaseModel):
    requisition_id: str
    candidate_id: str


class StageUpdate(BaseModel):
    status: str


class OfferCreate(BaseModel):
    application_id: str
    salary: float = Field(ge=0)


class StatusUpdate(BaseModel):
    status: str


class InterviewCreate(BaseModel):
    application_id: str
    interviewer_id: int
    starts_at: datetime
    ends_at: datetime
    round_number: int = Field(default=1, ge=1)


class InterviewUpdate(BaseModel):
    status: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    interviewer_id: int | None = None


class FeedbackCreate(BaseModel):
    interview_id: str
    interviewer_id: int
    technical_rating: int = Field(ge=1, le=5)
    problem_solving_rating: int = Field(ge=1, le=5)
    communication_rating: int = Field(ge=1, le=5)
    role_skills_rating: int = Field(ge=1, le=5)
    strengths: str = ""
    weaknesses: str = ""
    comments: str = ""
    recommendation: str


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12)
    role: str


class ResumeCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=500)
    version: int = Field(default=1, ge=1)


def _safe_resume_name(filename: str) -> str:
    name = Path(filename or "").name
    if not name or Path(name).suffix.lower() != ".pdf":
        raise HTTPException(400, "Only PDF resumes are accepted")
    return name


def serialize(row: Any) -> dict[str, Any]:
    result = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        result[column.name] = value.isoformat() if isinstance(value, datetime) else value
    return result


def serialize_user(user: User) -> dict[str, Any]:
    result = serialize(user)
    result.pop("password_hash", None)
    return result


def handle_service_error(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error))
    raise error


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, db=Depends(get_db)):
    user = authenticate(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid, inactive, or locked account")
    return {"token": create_access_token(user), "user": serialize_user(user)}


def _require_local_registration(request: Request) -> None:
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="Administrator registration is local-only")
    if RMS_ENV == "production" or not ADMIN_REGISTRATION_ENABLED:
        raise HTTPException(status_code=404, detail="Administrator registration is unavailable")


@app.get("/api/auth/register-admin/status")
def admin_registration_status(request: Request, db=Depends(get_db)):
    _require_local_registration(request)
    return {"available": admin_registration_available(db)}


@app.post("/api/auth/register-admin", status_code=201)
def register_first_admin(
    payload: AdminRegistrationRequest,
    request: Request,
    db=Depends(get_db),
):
    _require_local_registration(request)
    if payload.password != payload.password_confirmation:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        user = register_admin(db, payload.username, payload.password)
    except PermissionError as error:
        raise HTTPException(status_code=404, detail="Administrator registration is unavailable") from error
    except ValueError as error:
        status = 409 if "no longer available" in str(error) or "already exists" in str(error) else 400
        raise HTTPException(status_code=status, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Administrator registration is temporarily unavailable") from error
    return {"message": "Administrator registered. You can now sign in.", "user": serialize_user(user)}


@app.post("/api/auth/logout")
def logout():
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return serialize_user(user)


@app.get("/api/dashboard/metrics")
def dashboard_metrics(db=Depends(get_db), user=Depends(get_current_user)):
    return calculate_metrics(db)


@app.get("/api/dashboard/application-stats")
def application_stats(db=Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(select(Application.status)).all()
    result: dict[str, int] = {}
    for (status,) in rows:
        result[status] = result.get(status, 0) + 1
    return result


@app.get("/api/dashboard/recruitment-funnel")
def recruitment_funnel(db=Depends(get_db), user=Depends(get_current_user)):
    return {"stages": dashboard_metrics(db, user)}


@app.get("/api/requisitions")
def requisitions(skip: int = 0, limit: int = Query(50, le=100), db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(JobRequisition).offset(skip).limit(limit)).all()]


@app.post("/api/requisitions")
def create_requisition(payload: RequisitionCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_requisitions")
    if payload.max_salary < payload.min_salary:
        raise HTTPException(status_code=400, detail="Invalid salary band")
    next_id = (db.query(JobRequisition).count() or 0) + 1
    row = JobRequisition(id=f"REQ-{datetime.now().year}-{next_id:06d}", requested_by=user.username, status="Draft", **payload.model_dump())
    db.add(row); db.commit()
    return serialize(row)


@app.get("/api/requisitions/{requisition_id}")
def requisition(requisition_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    row = db.get(JobRequisition, requisition_id)
    if not row:
        raise HTTPException(404, "Requisition not found")
    return serialize(row)


@app.put("/api/requisitions/{requisition_id}")
def update_requisition(requisition_id: str, payload: RequisitionCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_requisitions")
    row = db.get(JobRequisition, requisition_id)
    if not row:
        raise HTTPException(404, "Requisition not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return serialize(row)


@app.delete("/api/requisitions/{requisition_id}")
def delete_requisition(requisition_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_requisitions")
    row = db.get(JobRequisition, requisition_id)
    if not row:
        raise HTTPException(404, "Requisition not found")
    db.delete(row); db.commit()
    return {"status": "deleted"}


@app.get("/api/candidates")
def candidates(skip: int = 0, limit: int = Query(50, le=100), db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Candidate).offset(skip).limit(limit)).all()]


@app.post("/api/candidates")
def create_candidate(payload: CandidateCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_candidates")
    next_id = (db.query(Candidate).count() or 0) + 1
    row = Candidate(id=f"CAND-{next_id:06d}", **payload.model_dump())
    db.add(row); db.commit()
    return serialize(row)


@app.get("/api/candidates/{candidate_id}")
def candidate(candidate_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    row = db.get(Candidate, candidate_id)
    if not row:
        raise HTTPException(404, "Candidate not found")
    return serialize(row)


@app.put("/api/candidates/{candidate_id}")
def update_candidate(candidate_id: str, payload: CandidateCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_candidates")
    row = db.get(Candidate, candidate_id)
    if not row:
        raise HTTPException(404, "Candidate not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return serialize(row)


@app.get("/api/candidates/{candidate_id}/resumes")
def candidate_resumes(candidate_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    if not db.get(Candidate, candidate_id):
        raise HTTPException(404, "Candidate not found")
    return [serialize(row) for row in db.scalars(select(ResumeArtifact).where(ResumeArtifact.candidate_id == candidate_id)).all()]


@app.post("/api/candidates/{candidate_id}/resumes")
def upload_resume(candidate_id: str, payload: ResumeCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_candidates")
    if not db.get(Candidate, candidate_id):
        raise HTTPException(404, "Candidate not found")
    row = ResumeArtifact(candidate_id=candidate_id, **payload.model_dump())
    db.add(row)
    db.commit()
    return serialize(row)


@app.post("/api/candidates/{candidate_id}/resumes/upload")
async def upload_resume_file(
    candidate_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    require_permission(user, "manage_candidates")
    if not db.get(Candidate, candidate_id):
        raise HTTPException(404, "Candidate not found")
    filename = _safe_resume_name(file.filename or "")
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(400, "Resume content type must be application/pdf")
    content = await file.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(413, "Resume exceeds the 5 MB size limit")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(400, "Uploaded file is not a valid PDF")
    PRIVATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.pdf"
    destination = PRIVATE_UPLOAD_DIR / stored_name
    with destination.open("wb") as target:
        target.write(content)
    current_version = db.query(ResumeArtifact).filter(ResumeArtifact.candidate_id == candidate_id).count() + 1
    row = ResumeArtifact(
        candidate_id=candidate_id,
        filename=filename,
        storage_path=stored_name,
        version=current_version,
    )
    db.add(row)
    db.commit()
    return serialize(row)


@app.get("/api/candidates/{candidate_id}/resumes/{resume_id}/download")
def download_resume(candidate_id: str, resume_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        require_permission(user, "manage_candidates")
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    resume = db.get(ResumeArtifact, resume_id)
    if not resume or resume.candidate_id != candidate_id:
        raise HTTPException(404, "Resume not found")
    path = (PRIVATE_UPLOAD_DIR / resume.storage_path).resolve()
    root = PRIVATE_UPLOAD_DIR.resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "Resume file is unavailable")
    return FileResponse(path, media_type="application/pdf", filename=resume.filename)


@app.get("/api/applications")
def applications(skip: int = 0, limit: int = Query(50, le=100), db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Application).offset(skip).limit(limit)).all()]


@app.get("/api/applications/{application_id}/history")
def application_history(application_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    if not db.get(Application, application_id):
        raise HTTPException(404, "Application not found")
    return [serialize(row) for row in db.scalars(
        select(ApplicationEvent).where(ApplicationEvent.application_id == application_id).order_by(ApplicationEvent.changed_at)
    ).all()]


@app.post("/api/applications")
def create_application(payload: ApplicationCreate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        return serialize(apply_candidate(db, payload.requisition_id, payload.candidate_id, user))
    except Exception as error:
        handle_service_error(error)


@app.put("/api/applications/{application_id}/stage")
def update_stage(application_id: str, payload: StageUpdate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        transition_application(db, application_id, payload.status, user)
        return serialize(db.get(Application, application_id))
    except Exception as error:
        handle_service_error(error)


@app.post("/api/screening/evaluate")
def screening(payload: dict[str, str], db=Depends(get_db), user=Depends(get_current_user)):
    try:
        return screen_application(db, payload["application_id"])
    except Exception as error:
        handle_service_error(error)


@app.get("/api/screening/results")
def screening_results(db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Application).where(Application.screening_score.is_not(None))).all()]


@app.get("/api/interviews")
def interviews(db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Interview)).all()]


@app.get("/api/interviewers")
def interviewers(db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Interviewer).where(Interviewer.active.is_(True))).all()]


@app.get("/api/interviewers/{interviewer_id}/availability")
def interviewer_availability(
    interviewer_id: int,
    starts_at: datetime = Query(...),
    ends_at: datetime = Query(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    interviewer = db.get(Interviewer, interviewer_id)
    if not interviewer or not interviewer.active:
        raise HTTPException(404, "Interviewer not found")
    if ends_at <= starts_at:
        raise HTTPException(400, "Availability end must be after start")
    bookings = db.scalars(select(Interview).where(
        Interview.interviewer_id == interviewer_id,
        Interview.status.in_(["Scheduled", "Rescheduled"]),
        Interview.starts_at < ends_at,
        Interview.ends_at > starts_at,
    ).order_by(Interview.starts_at)).all()
    return {
        "interviewer": serialize(interviewer),
        "range": {"starts_at": starts_at, "ends_at": ends_at},
        "available": len(bookings) == 0,
        "bookings": [serialize(row) for row in bookings],
    }


@app.post("/api/interviews")
def create_interview(payload: InterviewCreate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        next_id = (db.query(Interview).count() or 0) + 1
        row = schedule_interview(
            db, f"INT-{datetime.now().year}-{next_id:06d}", payload.application_id,
            payload.interviewer_id, payload.starts_at, payload.ends_at, payload.round_number, user,
        )
        return serialize(row)
    except Exception as error:
        handle_service_error(error)


@app.put("/api/interviews/{interview_id}")
def update_interview(interview_id: str, payload: InterviewUpdate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        if payload.starts_at is not None or payload.ends_at is not None or payload.interviewer_id is not None:
            interview = db.get(Interview, interview_id)
            if not interview:
                raise ValueError("Interview does not exist")
            reschedule_interview(
                db, interview_id, payload.starts_at or interview.starts_at,
                payload.ends_at or interview.ends_at, payload.interviewer_id, user,
            )
        elif payload.status:
            update_interview_status(db, interview_id, payload.status, user)
        else:
            raise ValueError("Interview update requires a status or schedule")
        return serialize(db.get(Interview, interview_id))
    except Exception as error:
        handle_service_error(error)


@app.get("/api/feedback/{interview_id}")
def feedback(interview_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    row = db.query(Feedback).filter(Feedback.interview_id == interview_id).first()
    if not row:
        raise HTTPException(404, "Feedback not found")
    return serialize(row)


@app.post("/api/feedback")
def create_feedback(payload: FeedbackCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_feedback")
    interview = db.get(Interview, payload.interview_id)
    if not interview:
        raise HTTPException(404, "Interview not found")
    if interview.status != "Completed":
        raise HTTPException(400, "Feedback is allowed only after an interview is completed")
    if payload.interviewer_id != interview.interviewer_id:
        raise HTTPException(400, "Feedback interviewer must match the assigned interviewer")
    if db.query(Feedback).filter(Feedback.interview_id == payload.interview_id).first():
        raise HTTPException(409, "Feedback already exists for this interview")
    ratings = [payload.technical_rating, payload.problem_solving_rating, payload.communication_rating, payload.role_skills_rating]
    row = Feedback(
        id=f"FDB-{datetime.now().year}-{(db.query(Feedback).count() or 0) + 1:06d}",
        overall_rating=sum(ratings) / len(ratings), **payload.model_dump(),
    )
    db.add(row)
    db.commit()
    return serialize(row)


@app.get("/api/offers")
def offers(db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Offer)).all()]


@app.post("/api/offers")
def create_offer_api(payload: OfferCreate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        next_id = (db.query(Offer).count() or 0) + 1
        return serialize(create_offer(db, f"OFF-{datetime.now().year}-{next_id:06d}", payload.application_id, payload.salary, user))
    except Exception as error:
        handle_service_error(error)


@app.put("/api/offers/{offer_id}/status")
def update_offer(offer_id: str, payload: StatusUpdate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        update_offer_status(db, offer_id, payload.status, user)
        return serialize(db.get(Offer, offer_id))
    except Exception as error:
        handle_service_error(error)


@app.put("/api/offers/{offer_id}/approve")
def approve_offer_api(offer_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        from backend.services.offer_service import approve_offer
        approve_offer(db, offer_id, user.username, user)
        return serialize(db.get(Offer, offer_id))
    except Exception as error:
        handle_service_error(error)


@app.put("/api/offers/{offer_id}/release")
def release_offer_api(offer_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        release_offer(db, offer_id, user)
        return serialize(db.get(Offer, offer_id))
    except Exception as error:
        handle_service_error(error)


@app.get("/api/exceptions")
def exceptions(db=Depends(get_db), user=Depends(get_current_user)):
    from backend.database.models import Anomaly
    return [serialize(row) for row in db.scalars(select(Anomaly)).all()]


@app.get("/api/validation")
def validation(db=Depends(get_db), user=Depends(get_current_user)):
    return validate(db)


@app.get("/api/analytics/overview")
def analytics_overview(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    department_id: int | None = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    return build_analytics_report(db, start_date, end_date, department_id)


@app.get("/api/analytics/hiring-funnel")
def hiring_funnel(db=Depends(get_db), user=Depends(get_current_user)):
    return recruitment_funnel(db, user)


@app.get("/api/analytics/department-performance")
def department_performance(db=Depends(get_db), user=Depends(get_current_user)):
    return {"departments": [serialize(row) for row in db.scalars(select(Department)).all()]}


@app.get("/api/departments")
def departments(db=Depends(get_db), user=Depends(get_current_user)):
    return [serialize(row) for row in db.scalars(select(Department)).all()]


@app.post("/api/departments")
def create_department(payload: DepartmentCreate, db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "manage_requisitions")
    row = Department(**payload.model_dump())
    db.add(row)
    db.commit()
    return serialize(row)


@app.put("/api/requisitions/{requisition_id}/status")
def update_requisition_status(requisition_id: str, payload: StatusUpdate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        set_requisition_status(db, requisition_id, payload.status, user)
        return serialize(db.get(JobRequisition, requisition_id))
    except Exception as error:
        handle_service_error(error)


@app.get("/api/admin/users")
def users(db=Depends(get_db), user=Depends(get_current_user)):
    require_permission(user, "view_audit")
    return [serialize_user(row) for row in db.scalars(select(User)).all()]


@app.post("/api/admin/users")
def create_user(payload: UserCreate, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        require_permission(user, "manage_users")
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    from backend.authentication.auth_service import ROLES, hash_password
    if payload.role not in ROLES:
        raise HTTPException(400, "Invalid role")
    row = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(row)
    db.commit()
    return serialize_user(row)
