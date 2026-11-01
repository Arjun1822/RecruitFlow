# Module documentation

## Requisitions and departments

Requisitions start in `Draft`. Requesters with `manage_requisitions` can create or edit them; approvers can set `Approved` or `Rejected`. Approval validates the salary band and records `ApprovalHistory` plus `AuditLog`. Applications are accepted only for approved requisitions. Departments provide the organizational grouping used by requisitions and interviewers.

Entities: `Department`, `JobRequisition`, `ApprovalHistory`, `AuditLog`.

## Candidates and resumes

Candidate records use `CAND-000001` identifiers and unique email addresses. Authorized users can create and edit candidates and attach resume metadata. File uploads accept PDF content only, enforce the configured five-megabyte default limit, require the `%PDF-` signature, and store a randomized filename under `PRIVATE_UPLOAD_DIR`. Downloads verify candidate ownership and keep the resolved path inside the private upload root.

Entities: `Candidate`, `ResumeArtifact`.

## Applications and screening

An application ID is `APP-{requisition_id}-{candidate_id}`. The service rejects unknown candidates, non-approved requisitions, and duplicate requisition/candidate pairs. Stage changes are checked against the explicit graph in [RECRUITMENT_WORKFLOW.md](RECRUITMENT_WORKFLOW.md), then recorded in `ApplicationEvent` and `AuditLog`.

Screening reads the active `ScreeningRule`, intersects required/preferred skills with `CandidateSkill`, and calculates a score from required matches, experience, preferred matches, and a baseline component. It returns score, matched skills, missing skills, and rule version; it does not advance the stage itself.

Entities: `Application`, `ApplicationEvent`, `ScreeningRule`, `CandidateSkill`, `Skill`, `AuditLog`.

## Interviews, interviewers, and feedback

Scheduling requires an active interviewer, a positive time range, and no overlapping scheduled/completed/rescheduled booking. Availability returns the interviewer, requested range, boolean availability, and conflicting bookings. Interview status values are `Scheduled`, `Completed`, `Cancelled`, and `Rescheduled`. Feedback is allowed only after completion, must use the assigned interviewer, rejects duplicates, and validates four ratings from 1 to 5.

Entities: `Interviewer`, `Interview`, `Feedback`, `AuditLog`.

## Offers and approvals

Offers can be created for selected or offer-pending applications and are unique per application. Approval requires the salary to fall within the requisition band and records approval history. Release requires `Approved`; acceptance requires `Released` and changes the application to `Hired`. Status changes are audited.

Entities: `Offer`, `ApprovalHistory`, `ApplicationEvent`, `AuditLog`.

## Authentication and administration

Users authenticate with bcrypt password hashes. Roles map to permissions; inactive or locked users cannot sign in. Five failed attempts lock an account for 15 minutes. Tokens are signed HS256 tokens with configurable expiry, and protected routes require an active user. The first administrator is registered once through the localhost-only flow when explicitly enabled in local development.

Entities: `User`, `AuditLog`.

## Analytics and validation

Analytics derives totals, rates, funnel stages, monthly trends, and department statistics from the database. Validation checks primary keys, foreign keys, mandatory fields, enums, IDs, duplicate applications, interview conflicts, missing feedback, lifecycle transitions, salary bands, approvals, reconciliation, closed requisitions, counts, and anomaly evidence.

Entities: all operational entities, especially `Anomaly`, `AnomalyFixtureEvidence`, and `ExceptionResolution`.

## Exceptions and auditability

Anomalies store issue labels, expected outcomes, severity, descriptions, and ground-truth status. Evidence links each intentional challenge fixture to exact records. Exception resolutions record the actor, status, notes, and timestamp. Audit logs retain actor/action/entity details for operational changes.
