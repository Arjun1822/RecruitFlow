from datetime import datetime
from sqlalchemy import select
from backend.database.models import Application, ApplicationEvent, AuditLog, Candidate, Feedback, Interview, JobRequisition
from backend.authentication.auth_service import require_permission

TRANSITIONS = {"Applied": {"Screening", "Withdrawn", "Rejected"}, "Screening": {"Shortlisted", "Rejected", "Withdrawn"},
               "Shortlisted": {"Interview Scheduled", "Rejected", "Withdrawn"}, "Interview Scheduled": {"Interview Completed", "Withdrawn"},
               "Interview Completed": {"Selected", "Rejected", "Withdrawn"}, "Selected": {"Offer Pending", "Rejected"},
               "Offer Pending": {"Offer Released", "Rejected"}, "Offer Released": {"Hired", "Withdrawn"},
               "Hired": set(), "Rejected": set(), "Withdrawn": set()}

def apply_candidate(session, requisition_id, candidate_id, actor):
    require_permission(actor, "manage_applications")
    requisition = session.get(JobRequisition, requisition_id)
    if not requisition or requisition.status != "Approved":
        raise ValueError("Only approved requisitions accept applications")
    if not session.get(Candidate, candidate_id):
        raise ValueError("Candidate does not exist")
    application_id = f"APP-{requisition_id}-{candidate_id}"
    if session.get(Application, application_id):
        raise ValueError("Candidate already applied to this requisition")
    application = Application(id=application_id, requisition_id=requisition_id, candidate_id=candidate_id, status="Applied")
    session.add(application)
    session.add(ApplicationEvent(application_id=application_id, from_status=None, to_status="Applied", changed_by=actor.username))
    session.add(AuditLog(actor=actor.username, action="CREATE", entity_type="Application", entity_id=application_id))
    session.commit()
    return application

def transition_application(session, application_id, new_status, actor="system"):
    app = session.get(Application, application_id)
    if not app: raise ValueError("Application does not exist")
    if hasattr(actor, "username"): require_permission(actor, "manage_applications")
    if new_status not in TRANSITIONS.get(app.status, set()): raise ValueError(f"Invalid transition: {app.status} -> {new_status}")
    if new_status in {"Interview Completed", "Selected"}:
        interview_ids = session.scalars(select(Interview.id).where(Interview.application_id == app.id)).all()
        feedback_interviews = session.scalars(select(Feedback.interview_id).where(Feedback.interview_id.in_(interview_ids))).all()
        if not feedback_interviews: raise ValueError("Completed interview feedback is required before progression")
    actor_name = actor.username if hasattr(actor, "username") else actor
    old = app.status; app.status = new_status
    session.add(ApplicationEvent(application_id=app.id, from_status=old, to_status=new_status, changed_by=actor_name))
    session.add(AuditLog(actor=actor_name, action="STATUS_CHANGE", entity_type="Application", entity_id=app.id, details=f"{old}->{new_status}"))
    session.commit()
