from datetime import datetime
from sqlalchemy import select
from backend.database.models import ApprovalHistory, Application, AuditLog, JobRequisition, Offer, utc_now
from backend.authentication.auth_service import require_permission

def create_offer(session, offer_id, application_id, salary, actor=None):
    if actor: require_permission(actor, "manage_offers")
    app = session.get(Application, application_id)
    if not app: raise ValueError("Application does not exist")
    if app.status not in {"Selected", "Offer Pending"}: raise ValueError("Offer requires a selected application")
    if session.scalar(select(Offer).where(Offer.application_id == application_id)):
        raise ValueError("An offer already exists for this application")
    offer = Offer(id=offer_id, application_id=application_id, salary=salary)
    session.add(offer); session.commit(); return offer

def approve_offer(session, offer_id, approver, actor=None):
    if actor: require_permission(actor, "approve_offers")
    offer = session.get(Offer, offer_id)
    if not offer: raise ValueError("Offer does not exist")
    app = session.get(Application, offer.application_id); req = session.get(JobRequisition, app.requisition_id)
    if not req or not req.min_salary <= offer.salary <= req.max_salary: raise ValueError("Salary is outside approved requisition band")
    offer.status = "Approved"; offer.approved_by = approver
    session.add(ApprovalHistory(entity_type="Offer", entity_id=offer.id, decision="Approved", approver=approver))
    if actor: session.add(AuditLog(actor=actor.username, action="APPROVE_OFFER", entity_type="Offer", entity_id=offer.id))
    session.commit()

def release_offer(session, offer_id, actor):
    require_permission(actor, "manage_offers")
    offer = session.get(Offer, offer_id)
    if not offer or offer.status != "Approved": raise ValueError("Only approved offers can be released")
    offer.status = "Released"; offer.released_at = utc_now()
    app = session.get(Application, offer.application_id)
    if app and app.status == "Offer Pending":
        app.status = "Offer Released"
        from backend.database.models import ApplicationEvent
        session.add(ApplicationEvent(application_id=app.id, from_status="Offer Pending", to_status="Offer Released", changed_by=actor.username))
    session.add(AuditLog(actor=actor.username, action="RELEASE_OFFER", entity_type="Offer", entity_id=offer.id))
    session.commit()

def update_offer_status(session, offer_id, status, actor):
    require_permission(actor, "manage_offers")
    if status not in {"Accepted", "Rejected", "Expired", "Withdrawn"}: raise ValueError("Invalid offer status")
    offer = session.get(Offer, offer_id)
    if not offer: raise ValueError("Offer does not exist")
    if status == "Accepted" and offer.status != "Released": raise ValueError("Only released offers can be accepted")
    offer.status = status
    app = session.get(Application, offer.application_id)
    if status == "Accepted" and app:
        old_status = app.status
        app.status = "Hired"
        from backend.database.models import ApplicationEvent
        session.add(ApplicationEvent(application_id=app.id, from_status=old_status, to_status="Hired", changed_by=actor.username))
    session.add(AuditLog(actor=actor.username, action="OFFER_STATUS", entity_type="Offer", entity_id=offer.id, details=status))
    session.commit()
