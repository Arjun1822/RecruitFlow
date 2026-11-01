from sqlalchemy import select
from backend.database.models import ApprovalHistory, AuditLog, JobRequisition, utc_now
from backend.authentication.auth_service import require_permission

def set_requisition_status(session, requisition_id, status, actor):
    require_permission(actor, "approve_requisitions" if status in {"Approved", "Rejected"} else "manage_requisitions")
    requisition = session.get(JobRequisition, requisition_id)
    if not requisition: raise ValueError("Requisition does not exist")
    if status == "Approved" and requisition.max_salary < requisition.min_salary: raise ValueError("Invalid salary band")
    requisition.status = status
    if status == "Approved": requisition.approved_by = actor.username
    if status in {"Approved", "Rejected"}:
        session.add(ApprovalHistory(entity_type="Requisition", entity_id=requisition.id, decision=status, approver=actor.username))
    session.add(AuditLog(actor=actor.username, action="REQUISITION_STATUS", entity_type="JobRequisition", entity_id=requisition.id, details=status))
    session.commit()
