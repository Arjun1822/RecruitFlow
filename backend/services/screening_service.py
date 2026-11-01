from sqlalchemy import select
from backend.database.models import Candidate, CandidateSkill, ScreeningRule, Skill, Application

def screen_application(session, application_id):
    app = session.get(Application, application_id)
    if not app: raise ValueError("Application does not exist")
    rule = session.scalar(select(ScreeningRule).where(ScreeningRule.requisition_id == app.requisition_id, ScreeningRule.active.is_(True)))
    if not rule: raise ValueError("No active screening rule configured")
    candidate_skills = {s.name for s in session.scalars(select(Skill).join(CandidateSkill).where(CandidateSkill.candidate_id == app.candidate_id))}
    required = {x.strip() for x in rule.required_skills.split(",") if x.strip()}
    preferred = {x.strip() for x in rule.preferred_skills.split(",") if x.strip()}
    matched_required = required & candidate_skills; matched_preferred = preferred & candidate_skills
    candidate = session.get(Candidate, app.candidate_id)
    score = len(matched_required) / max(1, len(required)) * 40 + min(candidate.years_experience / 10, 1) * 20 + len(matched_preferred) / max(1, len(preferred)) * 20 + 20
    app.screening_score = round(score, 2); session.commit()
    return {"score": app.screening_score, "matched_skills": sorted(matched_required | matched_preferred),
            "missing_skills": sorted((required | preferred) - candidate_skills), "rule_version": rule.version}
