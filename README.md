# Recruitment Management System

A modular Python recruitment lifecycle application backed by SQLAlchemy, with a FastAPI API and React/Vite frontend. The legacy Streamlit console remains available as a fallback. It includes requisitions, candidates, applications, explainable screening, interview scheduling, structured feedback, offers, approvals, audit history, anomalies, validation, analytics, authentication, and exports.

## Installation and prerequisites

Prerequisites:

- Python 3.12 or compatible supported Python version.
- Node.js and npm for the React frontend.
- MySQL 8 for all runtime and test database operations.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m backend.database.migrate
python -m backend.data_generator.generator --size starter --seed 20261022
```

Do not commit `.env`. Use `.env.example` as the configuration template and
provide a MySQL `DATABASE_URL` locally. Database credentials, JWT secrets, and
upload paths remain server-side.

## Run the application

Start the React/FastAPI stack in two terminals:

```powershell
python -m uvicorn backend.api.main:app --reload --port 8000
Set-Location frontend
npm install
npm run dev
```

The React application is served at `http://localhost:5173`, the API at
`http://localhost:8000`, and API documentation at `http://localhost:8000/docs`.
Set `VITE_API_URL` only in the frontend environment when the API is not on
localhost; database credentials remain server-side.

MySQL 8 is required for every application operation. Passwords are stored as
bcrypt hashes.

The local `.env` must contain an approved MySQL `DATABASE_URL`; the application
fails clearly rather than falling back when it is missing, non-MySQL, or
unreachable. Do not copy credentials into source control.
For local development, set `RMS_ADMIN_REGISTRATION_ENABLED=true` in the
backend process, open the React app from localhost, and use the one-time
administrator registration form. Registration is disabled by default and never
available in production; credentials are intentionally not documented here.

Resume uploads use `POST /api/candidates/{candidate_id}/resumes/upload`. Only PDF
files beginning with a valid PDF signature and within `MAX_RESUME_BYTES` are
accepted. Files are stored under the private `PRIVATE_UPLOAD_DIR` (default
`private_uploads/`), never under the frontend public assets, and downloads require
an authenticated API request. `python-multipart` is required for multipart form
parsing.

The interview workspace provides day, week, and month calendar views backed by
`/api/interviews`. It lists active interviewers, checks availability for a
requested window, rejects overlapping bookings, and supports authenticated
completion, cancellation, and rescheduling actions.

The Validation workspace displays live validator rule names, pass/fail status,
severity, messages, and affected record IDs with status, severity, and text
filters. The Analytics workspace uses `/api/analytics/overview` and supports
date and department filters; all displayed metrics and charts are
database-derived.

## MySQL 8 configuration

```sql
CREATE DATABASE rms CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'rms_user'@'localhost' IDENTIFIED BY 'use-a-secret-manager';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON rms.* TO 'rms_user'@'localhost';
```

Set this in `.env` (URL-encode special characters in the password):

```text
DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/rms?charset=utf8mb4
```

Create the dedicated `recruitment_test` database before running the integration test. Set `MYSQL_TEST_URL` to its URL and run `python -m pytest tests/test_mysql_integration.py -q`. The test creates the ORM schema, verifies connectivity, exercises CRUD inside a rollback transaction, checks foreign-key enforcement, and leaves test records cleaned up. A missing `MYSQL_TEST_URL` is skipped; a configured URL that cannot connect fails. SQLAlchemy uses connection pre-ping, a pool size of 10, overflow of 20, and 30-minute recycling. The reference bootstrap is [001_mysql_bootstrap.sql](backend/database/migrations/001_mysql_bootstrap.sql).

## UI and roles

The React frontend provides authenticated dashboard, requisition, candidate,
application, screening, interview, offer, exception, validation, analytics,
and administration workspaces with live API data, search, responsive tables,
loading/error states, and light/dark theme support. The Streamlit console
remains available with the broader legacy page set:

The Streamlit console contains Dashboard, Requisitions, Departments, Candidates, Resumes, Skills, Applications, Screening, Interviews, Interviewers, Feedback, Offers, Approvals, Analytics, Exceptions, Validation, Users, and Audit pages. Lists support search and pagination.

* **Business Requester** — requisitions, candidates, and applications.
* **Process Owner** — operational workflow, interviews, feedback, and offers.
* **Approver** — requisition and offer approvals plus audit viewing.
* **Operations Analyst** — candidates, applications, interviews, feedback, analytics, and exceptions.
* **System Administrator** — all permissions and user administration.

Backend services enforce permissions. Login failures are audited and accounts lock for 15 minutes after five failed attempts. Account activation is stored in the `users` table.

## Dataset, validation, and exports

```powershell
python -m backend.data_generator.generator --size starter --seed 20261022
python -m backend.data_generator.generator --size full --seed 20261022
python -m backend.validation.validator --size full
python -m pytest -q
```

`starter` creates 10 requisitions, 100 candidates, 150 applications, 40 interviews, and 12 offers. `full` creates exactly 100 requisitions, 2,000 candidates, 3,000 applications, 600 interviews, and 150 offers. Generation is deterministic for a fixed seed and configuration. Exports are written under `exports/csv`, `exports/json`, and `exports/sql`. Ground truth is separate in `exports/ground_truth.csv` and `exports/ground_truth.json`.

The five challenge anomalies are stored as positive ground-truth labels with
inspectable `anomaly_fixture_evidence`. Duplicate applications are represented
as rejected attempts rather than duplicate application rows. Validation reports
ordinary baseline checks, intentional anomaly fixtures, and unlabelled
data-quality violations separately.

Only approved requisitions accept applications. Application transitions are checked against an explicit state graph, interview scheduling rejects overlaps and inactive interviewers, screening uses job-related criteria only, feedback gates interview progression, and offers must fall inside the requisition salary band before approval.

## Demo workflow

1. Start the API and React frontend.
2. Register the first administrator through the localhost-only setup form,
   then sign in.
3. Select an approved requisition.
4. Register a synthetic candidate and upload a PDF resume.
5. Create an application and run screening.
6. Progress the application through the valid lifecycle.
7. Schedule an interview, inspect availability, and record structured feedback.
8. Create an in-band offer, approve it with an approver role, release it, and
   accept it.
9. Review application history, validation results, and database-derived
   analytics.

The permanent authenticated API regression workflow is
`tests/test_api_workflow.py`; it uses the dedicated MySQL test database and
synthetic records.

## Architecture overview

```text
React/Vite frontend
        |
      Axios
        |
FastAPI routes -> application/auth/workflow services
        |
    SQLAlchemy
     |
   MySQL 8
```

Core entities, relationships, lifecycle rules, deterministic generation, and
trade-offs are documented in
[TECHNICAL_DECISIONS.md](documentation/TECHNICAL_DECISIONS.md).

## Testing

```powershell
python -m compileall -q frontend backend tests
python -m pytest -v
Set-Location frontend
npm run build
npm test
npm run test
npm run test:e2e
```

The MySQL integration test requires the dedicated test database:

```powershell
python -m pytest -q tests/test_mysql_integration.py
```

It requires `MYSQL_TEST_URL` targeting the dedicated `recruitment_test`
database. If unset, the test is skipped; a configured but unreachable URL
fails. See [VALIDATION_AND_LIMITATIONS.md](documentation/VALIDATION_AND_LIMITATIONS.md)
for current evidence.

## Troubleshooting and limitations

* MySQL is mandatory. If `DATABASE_URL` is missing, non-MySQL, or unreachable,
  startup fails clearly; the application does not fall back to SQLite.
* If the database schema is stale, rerun `python -m backend.database.migrate`.
* If a user is locked, an administrator can set `active` or reset `failed_login_attempts` through the database until an administrative reset screen is added.
* Live MySQL integration uses `MYSQL_TEST_URL`; when it is absent, the integration test is explicitly skipped. The current configured dedicated test database has passed the CRUD, foreign-key, and transaction checks.
* The API uses signed, expiring HS256 JWTs. Set a strong `RMS_JWT_SECRET` outside development and rotate it through a secret manager in production.
* `DATABASE_URL` is required for runtime and `MYSQL_TEST_URL` is required for
  the dedicated test database. Tests fail when MySQL configuration is missing;
  they do not silently skip.
* Password reset, MFA, SSO, and enterprise secret-manager integration are not included.
* Browser tests cover login/dashboard and interview navigation; the complete
  mutation workflow is verified through authenticated API integration tests.
* Review and replace development bootstrap credentials before submission or
  deployment.
