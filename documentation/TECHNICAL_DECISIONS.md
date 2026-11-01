# Technical Decisions

## Architecture

RecruitFlow uses a mixed web architecture:

- Python FastAPI provides the HTTP API.
- SQLAlchemy provides ORM access and schema creation.
- MySQL 8 is the only supported runtime and test database.
- React and Vite provide the primary frontend.
- Streamlit remains as a legacy/fallback console.

The frontend calls the backend through the existing Axios client. Authentication
uses signed expiring HS256 JWTs, with bcrypt password hashes and backend
permission checks.

## Domain model

The twelve core entities are:

1. `JobRequisition`
2. `Department`
3. `Candidate`
4. `Application`
5. `ResumeArtifact`
6. `Skill`
7. `CandidateSkill`
8. `ScreeningRule`
9. `Interview`
10. `Interviewer`
11. `Feedback`
12. `Offer`

Additional tables preserve application events, approval history, audit logs,
anomaly records, users, and exception resolutions. Foreign keys connect
requisitions to departments, applications to requisitions/candidates,
interviews to applications/interviewers, feedback to interviews/interviewers,
offers to applications, and screening/candidate-skill records to their parents.
The application pair has a uniqueness constraint, and offers are unique per
application.

## API and lifecycle design

FastAPI routes expose resource reads, creation/update operations, workflow
transitions, resume upload/download, interview scheduling, feedback, offers,
validation, analytics, and authentication.

Application transitions use an explicit state graph rather than accepting
arbitrary status strings. Interview scheduling rejects invalid windows,
inactive interviewers, and overlapping bookings. Feedback is required before
progressing from a completed interview. Offers must be within the requisition
salary band before approval, and acceptance moves the application to `Hired`.

## Database selection

MySQL 8 is mandatory for runtime, tests, generation, validation, analytics, and
exports. The application reads `DATABASE_URL` from the root `.env`, rejects
missing or non-MySQL URLs during configuration, and uses SQLAlchemy with the
PyMySQL driver. Tests use a dedicated `recruitment_test` database and clean
their records before and after each test. This intentionally trades away
SQLite's setup convenience in favor of one production-equivalent relational
behavior path.

## Synthetic data and reproducibility

The generator supports `starter` and `full` sizes. Seed `20261022` drives
Python `random` and Faker; generated timestamps are fixed to
`2026-01-01T00:00:00`, and exports include CSV, JSON, SQL, and separate
ground-truth files. The full target is 100 requisitions, 2,000 candidates,
3,000 applications, 600 interviews, and 150 offers.

Synthetic records use non-sensitive example domains and generated values. The
five anomaly scenarios are represented by deterministic positive labels and the
`anomaly_fixture_evidence` table. Each evidence row points to valid
application, interview, offer, interviewer, candidate, or requisition records.
The duplicate-application case records a rejected second-attempt condition
without inserting a duplicate row, preserving the database uniqueness rule.
Validation distinguishes these intentional fixtures from unlabelled
data-quality violations. The closed-requisition fixture records one exact
evidence-linked active application; validation excludes only that application,
so any other active application under the same closed requisition remains a
reported violation.

## Security and storage trade-offs

JWT and bcrypt provide application-level authentication without requiring an
external identity provider. Resume files are stored under a private directory
with randomized storage names and authenticated download routes, rather than
frontend public assets.

Production deployment still requires a strong secret manager, non-default
credentials, and an enterprise identity strategy. MFA, SSO, password reset,
and managed object storage are not implemented.
