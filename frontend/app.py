from datetime import datetime, timedelta, timezone
from pathlib import Path
import streamlit as st
from sqlalchemy import func, select
from backend.database.connection import SessionLocal, init_db
from backend.database.models import (
    Anomaly, Application, ApplicationEvent, ApprovalHistory, AuditLog, Candidate, CandidateSkill,
    Department, ExceptionResolution, Feedback, Interview, Interviewer, JobRequisition, Offer, ResumeArtifact, Skill, User
)
from backend.analytics.metrics import calculate_metrics
from backend.authentication.auth_service import ROLES, authenticate, has_permission, hash_password, require_permission
from backend.services.application_service import apply_candidate, transition_application
from backend.services.interview_service import schedule_interview, update_interview_status
from backend.services.offer_service import approve_offer, create_offer, release_offer, update_offer_status
from backend.services.requisition_service import set_requisition_status
from backend.services.screening_service import screen_application
from backend.validation.validator import validate

st.set_page_config(page_title="Recruitment Management System", page_icon="👥", layout="wide")
init_db()
session = SessionLocal()

def fail_safe(action):
    try:
        action()
        st.success("Saved successfully.")
    except (ValueError, PermissionError) as exc:
        session.rollback()
        st.error(str(exc))

def rows_page(query, columns, key):
    search = st.text_input("Search", key=f"{key}-search")
    page_size = st.selectbox("Rows per page", [10, 25, 50], key=f"{key}-size")
    items = session.scalars(query).all()
    if search:
        needle = search.lower()
        items = [item for item in items if needle in str(item.__dict__).lower()]
    page = st.number_input("Page", min_value=1, value=1, step=1, key=f"{key}-page")
    start = (page - 1) * page_size
    st.dataframe([{column: getattr(item, column, None) for column in columns} for item in items[start:start + page_size]],
                 use_container_width=True)
    st.caption(f"{len(items)} matching records")
    return items

def actor_required(permission):
    if not has_permission(st.session_state.get("user"), permission):
        st.warning("Your role does not have permission for this action.")
        return False
    return True

def dashboard():
    metrics = calculate_metrics(session)
    st.subheader("Recruitment KPIs")
    cols = st.columns(6)
    for col, label in zip(cols, ["total_requisitions", "open_requisitions", "total_applications", "shortlisted_candidates", "interviews_scheduled", "offers_accepted"]):
        col.metric(label.replace("_", " ").title(), metrics[label])
    st.json(metrics)
    st.caption("Formula definitions: pass rates divide the successful count by the relevant completed population; release and acceptance rates divide by applications and offers respectively.")

def requisitions():
    st.subheader("Job requisition management")
    if actor_required("manage_requisitions"):
        with st.form("new-requisition"):
            departments = session.scalars(select(Department).order_by(Department.name)).all()
            dept = st.selectbox("Department", departments, format_func=lambda x: x.name)
            title = st.text_input("Job title"); openings = st.number_input("Openings", 1, 100, 1)
            minimum = st.number_input("Minimum salary", 0.0, 10000000.0, 50000.0)
            maximum = st.number_input("Maximum salary", minimum, 10000000.0, minimum + 20000.0)
            location = st.text_input("Location", "Remote")
            if st.form_submit_button("Create requisition"):
                if not title.strip() or not location.strip():
                    st.error("Job title and location are required.")
                    return
                next_id = (session.scalar(select(func.count(JobRequisition.id))) or 0) + 1
                session.add(JobRequisition(id=f"REQ-{datetime.now(timezone.utc).year}-{next_id:06d}", department_id=dept.id,
                    title=title, openings=openings, min_experience=0, max_experience=20, min_salary=minimum,
                    max_salary=maximum, location=location, requested_by=st.session_state.user.username, status="Draft"))
                session.commit(); st.success("Requisition created.")
    items = rows_page(select(JobRequisition).order_by(JobRequisition.created_at.desc()),
                      ["id", "title", "status", "location", "min_salary", "max_salary"], "requisitions")
    if items and actor_required("approve_requisitions"):
        with st.form("requisition-decision"):
            selected = st.selectbox("Requisition", items, format_func=lambda x: x.id)
            decision = st.selectbox("Decision", ["Approved", "Rejected"])
            if st.form_submit_button("Record decision"):
                fail_safe(lambda: set_requisition_status(session, selected.id, decision, st.session_state.user))

def departments():
    st.subheader("Department management")
    if actor_required("manage_requisitions"):
        with st.form("department"):
            name = st.text_input("Name"); description = st.text_area("Description")
            if st.form_submit_button("Add department"):
                if not name.strip():
                    st.error("Department name is required.")
                else:
                    session.add(Department(name=name.strip(), description=description)); session.commit(); st.success("Department added.")
    rows_page(select(Department).order_by(Department.name), ["id", "name", "description"], "departments")

def candidates():
    st.subheader("Candidate management")
    if actor_required("manage_candidates"):
        with st.form("candidate"):
            first = st.text_input("First name"); last = st.text_input("Last name"); email = st.text_input("Email")
            phone = st.text_input("Phone"); education = st.text_input("Education"); experience = st.number_input("Years of experience", 0, 60, 0)
            location = st.text_input("Location", "Remote")
            if st.form_submit_button("Register candidate"):
                if not all(value.strip() for value in [first, last, email, phone, education, location]):
                    st.error("All candidate fields are required.")
                    return
                try:
                    number = (session.scalar(select(func.count(Candidate.id))) or 0) + 1
                    session.add(Candidate(id=f"CAND-{number:06d}", first_name=first, last_name=last, email=email,
                        phone=phone, education=education, years_experience=experience, location=location)); session.commit(); st.success("Candidate registered.")
                except Exception as exc:
                    session.rollback(); st.error(f"Could not register candidate: {exc}")
    rows_page(select(Candidate).order_by(Candidate.created_at.desc()), ["id", "first_name", "last_name", "email", "years_experience", "location"], "candidates")

def resumes():
    st.subheader("Resume management")
    candidates_list = session.scalars(select(Candidate).order_by(Candidate.id)).all()
    if actor_required("manage_candidates") and candidates_list:
        with st.form("resume"):
            candidate = st.selectbox("Candidate", candidates_list, format_func=lambda x: x.id)
            upload = st.file_uploader("Resume file", type=["pdf", "doc", "docx", "txt"])
            if st.form_submit_button("Store resume metadata") and upload:
                root = Path("exports") / "resumes"; root.mkdir(parents=True, exist_ok=True)
                path = root / f"{candidate.id}-{upload.name}"
                path.write_bytes(upload.getbuffer())
                version = (session.scalar(select(func.max(ResumeArtifact.version)).where(ResumeArtifact.candidate_id == candidate.id)) or 0) + 1
                session.add(ResumeArtifact(candidate_id=candidate.id, filename=upload.name, storage_path=str(path), version=version)); session.commit(); st.success("Resume stored.")
    rows_page(select(ResumeArtifact).order_by(ResumeArtifact.uploaded_at.desc()), ["id", "candidate_id", "filename", "version", "storage_path"], "resumes")

def skills():
    st.subheader("Skills management")
    if actor_required("manage_candidates"):
        with st.form("skill"):
            name = st.text_input("Skill name")
            if st.form_submit_button("Add skill"):
                if not name.strip():
                    st.error("Skill name is required.")
                else:
                    session.add(Skill(name=name.strip())); session.commit(); st.success("Skill added.")
    rows_page(select(Skill).order_by(Skill.name), ["id", "name"], "skills")

def screening():
    st.subheader("Explainable resume screening")
    apps = session.scalars(select(Application).order_by(Application.applied_at.desc())).all()
    if apps:
        selected = st.selectbox("Application", apps, format_func=lambda x: x.id)
        if st.button("Run screening") and actor_required("manage_applications"):
            try: st.json(screen_application(session, selected.id))
            except ValueError as exc: st.error(str(exc))
        st.dataframe([{"application": a.id, "status": a.status, "score": a.screening_score} for a in apps[:100]], use_container_width=True)

def applications():
    st.subheader("Application management")
    requisitions_list = session.scalars(select(JobRequisition).where(JobRequisition.status == "Approved")).all()
    candidates_list = session.scalars(select(Candidate).order_by(Candidate.id)).all()
    if actor_required("manage_applications") and requisitions_list and candidates_list:
        with st.form("application"):
            req = st.selectbox("Approved requisition", requisitions_list, format_func=lambda x: f"{x.id} — {x.title}")
            candidate = st.selectbox("Candidate", candidates_list, format_func=lambda x: f"{x.id} — {x.first_name} {x.last_name}")
            if st.form_submit_button("Apply candidate"):
                fail_safe(lambda: apply_candidate(session, req.id, candidate.id, st.session_state.user))
    items = rows_page(select(Application).order_by(Application.applied_at.desc()),
                      ["id", "requisition_id", "candidate_id", "status", "screening_score"], "applications")
    if items and actor_required("manage_applications"):
        with st.form("application-status"):
            item = st.selectbox("Application", items, format_func=lambda x: x.id)
            status = st.selectbox("Next status", ["Screening", "Shortlisted", "Rejected", "Withdrawn", "Interview Scheduled", "Interview Completed", "Selected"])
            if st.form_submit_button("Advance application"):
                fail_safe(lambda: transition_application(session, item.id, status, st.session_state.user))

def interviews():
    st.subheader("Interview scheduling")
    apps = session.scalars(select(Application).where(Application.status.in_(["Shortlisted", "Interview Scheduled"]))).all()
    interviewers = session.scalars(select(Interviewer).where(Interviewer.active.is_(True))).all()
    if actor_required("manage_interviews") and apps and interviewers:
        with st.form("schedule"):
            app = st.selectbox("Application", apps, format_func=lambda x: x.id); person = st.selectbox("Interviewer", interviewers, format_func=lambda x: x.name)
            starts = st.datetime_input("Starts at", datetime.now(timezone.utc) + timedelta(days=1)); duration = st.number_input("Duration (minutes)", 15, 240, 60)
            if st.form_submit_button("Schedule"):
                fail_safe(lambda: schedule_interview(session, f"INT-{datetime.now(timezone.utc).year}-{(session.scalar(select(func.count(Interview.id))) or 0)+1:06d}",
                    app.id, person.id, starts, starts + timedelta(minutes=duration), actor=st.session_state.user))
    items = rows_page(select(Interview).order_by(Interview.starts_at.desc()), ["id", "application_id", "interviewer_id", "starts_at", "ends_at", "status"], "interviews")
    if items and actor_required("manage_interviews"):
        with st.form("interview-status"):
            item = st.selectbox("Interview", items, format_func=lambda x: x.id); status = st.selectbox("Status", ["Completed", "Cancelled", "Rescheduled"])
            if st.form_submit_button("Update interview"):
                fail_safe(lambda: update_interview_status(session, item.id, status, st.session_state.user))

def interviewers():
    st.subheader("Interviewer management")
    departments_list = session.scalars(select(Department)).all()
    if actor_required("manage_interviews"):
        with st.form("interviewer"):
            name = st.text_input("Name"); email = st.text_input("Email"); department = st.selectbox("Department", departments_list, format_func=lambda x: x.name) if departments_list else None
            if st.form_submit_button("Add interviewer"):
                session.add(Interviewer(name=name, email=email, department_id=department.id if department else None)); session.commit(); st.success("Interviewer added.")
    rows_page(select(Interviewer).order_by(Interviewer.name), ["id", "name", "email", "active"], "interviewers")

def feedback():
    st.subheader("Structured feedback")
    completed = session.scalars(select(Interview).where(Interview.status == "Completed")).all()
    if actor_required("manage_feedback") and completed:
        with st.form("feedback"):
            interview = st.selectbox("Interview", completed, format_func=lambda x: x.id)
            ratings = [st.slider(label, 1, 5, 3) for label in ["Technical", "Problem solving", "Communication", "Role skills"]]
            recommendation = st.selectbox("Recommendation", ["Strong Hire", "Hire", "Hold", "Reject"])
            strengths = st.text_area("Strengths"); weaknesses = st.text_area("Weaknesses"); comments = st.text_area("Comments")
            if st.form_submit_button("Submit feedback"):
                session.add(Feedback(id=f"FB-{interview.id}-{interview.interviewer_id}", interview_id=interview.id, interviewer_id=interview.interviewer_id,
                    technical_rating=ratings[0], problem_solving_rating=ratings[1], communication_rating=ratings[2], role_skills_rating=ratings[3],
                    overall_rating=sum(ratings) / 4, recommendation=recommendation, strengths=strengths, weaknesses=weaknesses, comments=comments)); session.commit(); st.success("Feedback submitted.")
    rows_page(select(Feedback).order_by(Feedback.created_at.desc()), ["id", "interview_id", "overall_rating", "recommendation"], "feedback")

def offers():
    st.subheader("Offer management")
    apps = session.scalars(select(Application).where(Application.status.in_(["Selected", "Offer Pending"]))).all()
    if actor_required("manage_offers") and apps:
        with st.form("offer"):
            app = st.selectbox("Application", apps, format_func=lambda x: x.id); salary = st.number_input("Salary", 0.0, 10000000.0, 50000.0)
            if st.form_submit_button("Create offer"):
                fail_safe(lambda: create_offer(session, f"OFF-{datetime.now(timezone.utc).year}-{(session.scalar(select(func.count(Offer.id))) or 0)+1:06d}", app.id, salary, st.session_state.user))
    items = rows_page(select(Offer).order_by(Offer.created_at.desc()), ["id", "application_id", "salary", "status", "approved_by"], "offers")
    if items:
        item = st.selectbox("Offer action", items, format_func=lambda x: x.id)
        c1, c2, c3 = st.columns(3)
        if c1.button("Approve") and actor_required("approve_offers"): fail_safe(lambda: approve_offer(session, item.id, st.session_state.user.username, st.session_state.user))
        if c2.button("Release") and actor_required("manage_offers"): fail_safe(lambda: release_offer(session, item.id, st.session_state.user))
        if c3.button("Reject") and actor_required("manage_offers"): fail_safe(lambda: update_offer_status(session, item.id, "Rejected", st.session_state.user))

def approvals():
    st.subheader("Approval history")
    rows_page(select(ApprovalHistory).order_by(ApprovalHistory.decided_at.desc()), ["id", "entity_type", "entity_id", "decision", "approver", "decided_at"], "approvals")

def analytics():
    st.subheader("Recruitment analytics")
    st.json(calculate_metrics(session))
    st.dataframe([{"department": d.name, "applications": session.scalar(select(func.count(Application.id)).join(JobRequisition, Application.requisition_id == JobRequisition.id).where(JobRequisition.department_id == d.id)) or 0} for d in session.scalars(select(Department))], use_container_width=True)

def administration():
    st.subheader("User administration")
    if not actor_required("*"): return
    with st.form("user"):
        username = st.text_input("Username"); password = st.text_input("Temporary password", type="password")
        role = st.selectbox("Role", sorted(ROLES))
        if st.form_submit_button("Create user"):
            try:
                session.add(User(username=username, password_hash=hash_password(password), role=role)); session.commit(); st.success("User created.")
            except Exception as exc: session.rollback(); st.error(str(exc))
    rows_page(select(User).order_by(User.username), ["id", "username", "role", "active", "last_login_at"], "users")

def audit():
    st.subheader("Audit history")
    rows_page(select(AuditLog).order_by(AuditLog.occurred_at.desc()), ["id", "actor", "action", "entity_type", "entity_id", "occurred_at"], "audit")

def exceptions():
    st.subheader("Exception management")
    anomalies = session.scalars(select(Anomaly).order_by(Anomaly.severity, Anomaly.issue_id)).all()
    st.dataframe([{"issue_id": a.issue_id, "type": a.issue_type, "entity": a.entity_id, "severity": a.severity, "description": a.description,
                   "expected": a.expected_outcome, "actual_detection": "Detected" if a.ground_truth == "positive" else "Not detected", "resolved": a.resolved} for a in anomalies], use_container_width=True)
    if anomalies and actor_required("view_exceptions"):
        with st.form("exception-resolution"):
            issue = st.selectbox("Issue", anomalies, format_func=lambda x: x.issue_id)
            notes = st.text_area("Resolution notes")
            if st.form_submit_button("Resolve issue"):
                issue.resolved = True
                session.add(ExceptionResolution(issue_id=issue.issue_id, actor=user.username, status="Resolved", notes=notes))
                session.commit()
                st.success("Exception resolved and resolution history recorded.")

def validation_page():
    st.subheader("Validation")
    st.dataframe(validate(session), use_container_width=True)

if "user" not in st.session_state:
    st.title("Recruitment Management System")
    st.caption("Development administrator: admin / ChangeMe!2026 — change this password before deployment.")
    with st.form("login"):
        username = st.text_input("Username"); password = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            user = authenticate(session, username, password)
            if user: st.session_state.user = user; st.rerun()
            else: st.error("Invalid, inactive, or locked account.")
    session.close()
    st.stop()

user = st.session_state.user
st.sidebar.success(f"{user.username} ({user.role})")
if st.sidebar.button("Sign out"):
    del st.session_state["user"]; st.rerun()
page = st.sidebar.radio("Navigation", ["Dashboard", "Requisitions", "Departments", "Candidates", "Resumes", "Skills", "Applications", "Screening",
    "Interviews", "Interviewers", "Feedback", "Offers", "Approvals", "Analytics", "Exceptions", "Validation", "Users", "Audit"])
dispatch = {"Dashboard": dashboard, "Requisitions": requisitions, "Departments": departments, "Candidates": candidates, "Resumes": resumes,
    "Applications": applications,
    "Skills": skills, "Screening": screening, "Interviews": interviews, "Interviewers": interviewers, "Feedback": feedback, "Offers": offers,
    "Approvals": approvals, "Analytics": analytics, "Exceptions": exceptions, "Validation": validation_page, "Users": administration, "Audit": audit}
dispatch[page]()
session.close()
