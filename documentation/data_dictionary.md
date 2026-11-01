# Data dictionary

This dictionary follows `backend/database/models.py`. `created_at` and `updated_at` appear on models using `TimestampMixin`; both are non-null UTC timestamps with application defaults.

## departments

| Column | Type | Key/nullability | Default | Description/example |
|---|---|---|---|---|
| id | Integer | PK, required | generated | Department identifier, `1` |
| name | VARCHAR(100) | unique, required | — | Department name |
| description | Text | nullable | — | Human-readable description |
| created_at / updated_at | DateTime | required | UTC now | Record timestamps |

## job_requisitions

| Column | Type | Key/nullability | Default | Description |
|---|---|---|---|---|
| id | VARCHAR(24) | PK, required | — | `REQ-2026-000001` |
| department_id | Integer | FK, required | — | `departments.id` |
| title | VARCHAR(150) | required | — | Role title |
| openings | Integer | required | — | Number of positions |
| min_experience / max_experience | Integer | required | 0 / 20 | Experience band |
| min_salary / max_salary | Float | required | — | Approved salary band |
| location | VARCHAR(100) | required | — | Work location |
| status | VARCHAR(30) | indexed, required | `Draft` | Draft, Approved, Closed, or other service-managed status |
| requested_by | VARCHAR(100) | required | — | Requester identity |
| approved_by | VARCHAR(100) | nullable | — | Approver identity |
| effective_from | DateTime | nullable | — | Effective timestamp |
| created_at / updated_at | DateTime | required | UTC now | Record timestamps |

## candidates

| Column | Type | Key/nullability | Description |
|---|---|---|---|
| id | VARCHAR(20) | PK, required | `CAND-000001` |
| first_name / last_name | VARCHAR(80) | required | Candidate name |
| email | VARCHAR(255) | unique, required | Contact email |
| phone | VARCHAR(30) | required | Contact number |
| education | VARCHAR(150) | required | Education description |
| years_experience | Integer | required | Non-negative experience |
| location | VARCHAR(100) | required | Candidate location |
| created_at / updated_at | DateTime | required | Record timestamps |

## applications

| Column | Type | Key/nullability | Description |
|---|---|---|---|
| id | VARCHAR(60) | PK, required | Derived `APP-{requisition_id}-{candidate_id}` |
| requisition_id | VARCHAR(24) | FK/index, required | Target requisition |
| candidate_id | VARCHAR(20) | FK/index, required | Candidate |
| status | VARCHAR(35) | indexed, required | Lifecycle stage |
| applied_at | DateTime | required | Submission time |
| screening_score | Float | nullable | Explainable screening score |
| created_at / updated_at | DateTime | required | Record timestamps |

Unique constraint: `(requisition_id, candidate_id)`.

## resume_artifacts, skills, and candidate_skills

| Table | Columns |
|---|---|
| resume_artifacts | `id` Integer PK; `candidate_id` FK; `filename` VARCHAR(255); `storage_path` VARCHAR(500); `version` Integer default 1; `uploaded_at` DateTime; timestamps |
| skills | `id` Integer PK; `name` VARCHAR(80) unique; timestamps |
| candidate_skills | `candidate_id` VARCHAR(20) PK/FK; `skill_id` Integer PK/FK; `proficiency` VARCHAR(20), default `Intermediate` |

## screening_rules

`id` Integer PK; `requisition_id` FK/index; `required_skills` and `preferred_skills` Text; `version` Integer default 1; `active` Boolean default true; timestamps.

## interviewers and interviews

| Table | Columns |
|---|---|
| interviewers | `id` Integer PK; `name` VARCHAR(120); `email` VARCHAR(255) unique; `department_id` nullable FK; `active` Boolean default true; timestamps |
| interviews | `id` VARCHAR(24) PK, e.g. `INT-2026-000001`; `application_id` FK/index; `interviewer_id` FK/index; `round_number` Integer default 1; `starts_at`/`ends_at` DateTime; `status` VARCHAR(25); timestamps |

Index: `ix_interview_window(interviewer_id, starts_at, ends_at)`.

## feedback and offers

`feedback` contains `id` VARCHAR(40) PK, interview/interviewer foreign keys, four Integer ratings, `overall_rating` Float, strengths/weaknesses/comments Text, `recommendation` VARCHAR(20), and timestamps.

`offers` contains `id` VARCHAR(24) PK, unique `application_id` FK, `salary` Float, indexed `status`, nullable `approved_by`, `released_at`, `expires_at`, and timestamps.

## History, security, and anomaly tables

| Table | Columns |
|---|---|
| application_events | `id` Integer PK; application FK; nullable `from_status`; `to_status`; `changed_by`; `changed_at` |
| approval_history | `id` Integer PK; `entity_type`; `entity_id`; `decision`; `approver`; nullable `reason`; `decided_at` |
| audit_logs | `id` Integer PK; `actor`; `action`; `entity_type`; `entity_id`; nullable `details`; indexed `occurred_at` |
| anomalies | `issue_id` VARCHAR(25) PK; issue type, entity, expected outcome, ground truth, severity, description; `resolved` Boolean default false |
| anomaly_fixture_evidence | `id` Integer PK; unique/indexed `issue_id` FK; nullable FKs to requisition, candidate, application, interview, interviewer, and offer; `expected_result`; `details` |
| users | `id` Integer PK; unique/indexed username; password_hash; indexed role; active; failed_login_attempts; nullable locked_until and last_login_at; timestamps |
| exception_resolutions | `id` Integer PK; indexed anomaly issue FK; actor; status; notes; resolved_at |
