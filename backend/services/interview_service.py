from sqlalchemy import select, and_
from backend.database.models import AuditLog, Interview, Interviewer
from backend.authentication.auth_service import require_permission

def schedule_interview(session, interview_id, application_id, interviewer_id, starts_at, ends_at, round_number=1, actor=None):
    if actor: require_permission(actor, "manage_interviews")
    if not session.get(Interviewer, interviewer_id) or not session.get(Interviewer, interviewer_id).active:
        raise ValueError("Interviewer is not active")
    if ends_at <= starts_at: raise ValueError("Interview end must be after start")
    conflict = session.scalar(select(Interview).where(and_(Interview.interviewer_id == interviewer_id,
        Interview.status.in_(["Scheduled", "Completed", "Rescheduled"]),
        Interview.starts_at < ends_at, Interview.ends_at > starts_at)))
    if conflict: raise ValueError(f"Interviewer is unavailable due to {conflict.id}")
    interview = Interview(id=interview_id, application_id=application_id, interviewer_id=interviewer_id,
                          round_number=round_number, starts_at=starts_at, ends_at=ends_at)
    session.add(interview)
    if actor: session.add(AuditLog(actor=actor.username, action="SCHEDULE_INTERVIEW", entity_type="Interview", entity_id=interview_id))
    session.commit(); return interview

def update_interview_status(session, interview_id, status, actor):
    require_permission(actor, "manage_interviews")
    if status not in {"Scheduled", "Completed", "Cancelled", "Rescheduled"}:
        raise ValueError("Invalid interview status")
    interview = session.get(Interview, interview_id)
    if not interview: raise ValueError("Interview does not exist")
    interview.status = status
    session.add(AuditLog(actor=actor.username, action="INTERVIEW_STATUS", entity_type="Interview", entity_id=interview_id, details=status))
    session.commit()


def reschedule_interview(session, interview_id, starts_at, ends_at, interviewer_id=None, actor=None):
    if actor:
        require_permission(actor, "manage_interviews")
    interview = session.get(Interview, interview_id)
    if not interview:
        raise ValueError("Interview does not exist")
    assigned_id = interviewer_id if interviewer_id is not None else interview.interviewer_id
    interviewer = session.get(Interviewer, assigned_id)
    if not interviewer or not interviewer.active:
        raise ValueError("Interviewer is not active")
    if ends_at <= starts_at:
        raise ValueError("Interview end must be after start")
    conflict = session.scalar(select(Interview).where(and_(
        Interview.id != interview_id,
        Interview.interviewer_id == assigned_id,
        Interview.status.in_(["Scheduled", "Completed", "Rescheduled"]),
        Interview.starts_at < ends_at,
        Interview.ends_at > starts_at,
    )))
    if conflict:
        raise ValueError(f"Interviewer is unavailable due to {conflict.id}")
    interview.interviewer_id = assigned_id
    interview.starts_at = starts_at
    interview.ends_at = ends_at
    interview.status = "Rescheduled"
    if actor:
        session.add(AuditLog(
            actor=actor.username, action="RESCHEDULE_INTERVIEW",
            entity_type="Interview", entity_id=interview_id,
        ))
    session.commit()
    return interview
