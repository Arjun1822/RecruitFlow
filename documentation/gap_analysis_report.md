# RecruitFlow Requirements Gap Analysis

Audit date: 2026-11-01  
Scope: React/Vite frontend, FastAPI API, SQLAlchemy models, MySQL dataset, exports, generators, validation, tests, and documentation.

## Evidence summary

- The MySQL schema contains 18 tables, including all 12 requested core entities plus application events, approvals, audit logs, anomalies, users, and exception resolutions.
- The generator defines the required full volumes; the latest executed MySQL
  validation used the isolated starter dataset to avoid modifying application
  data. Full-volume generation must be run against an explicitly provisioned
  MySQL dataset before release.
- All five required anomaly fixtures are present with `ground_truth=positive`.
- Latest validation: Python compilation passed; the complete MySQL-backed suite
  passed 14 tests; the starter MySQL dataset passed 55 validation checks;
  frontend build, unit tests, and two Playwright smoke tests passed.

## Requirements matrix

| Requirement | Expected behavior | Actual implementation | Evidence | Status | Recommended action |
|---|---|---|---|---|---|
| Core entities | All 12 entities represented with relational integrity | All 12 ORM classes exist; 18 tables are present | `backend/database/models.py`; MySQL metadata inspection | COMPLETE | Keep schema regression coverage |
| Keys and constraints | PKs, FKs, unique application pair and unique offer relationship | PK/FK declarations and application/offer uniqueness exist | `backend/database/models.py:15-184`; MySQL integration test | COMPLETE | Keep automated schema inspection test |
| Lifecycle/history | Application events, approvals, audit, exception history | Additional history/audit tables exist and generator populates core history | `models.py`; `generator.py`; `application_service.py` | PARTIAL | Expose application history and resolution APIs |
| ID conventions | REQ, CAND, APP, INT, FB, OFF formats | Generator produces all requested patterns | `generator.py:32,44,58,73,79,89` | COMPLETE | Add format assertions to tests |
| Full dataset | 100/2,000/3,000/600/150 exact counts | Generator targets these counts directly in MySQL | `backend/data_generator/generator.py`; MySQL validation command | COMPLETE | Re-run after future generator changes |
| Seed reproducibility | Seed 20261022 yields deterministic data and exports | Fixed timestamps and export normalization exist; current artifact checksums recorded | `generator.py:14-18,108`; `export_data.py:22-31` | PARTIAL | Run two fresh generations and persist checksum comparison |
| Export separation | CSV, JSON, SQL and separate ground truth files | CSV/JSON/SQL exports exist; `ground_truth.csv/json` are separate from table folders | `export_data.py:57-80`; `exports/` | COMPLETE | Add export count/checksum test |
| Requisition workflow | Create, approve, reject, close with authorization | Create and status APIs call permission-aware service; approval/closure rules exist | `main.py:174-205,419`; `requisition_service.py` | COMPLETE | Add API workflow tests |
| Candidate workflow | Candidate registration and profile access | Create/update/get endpoints and React profile page exist | `main.py:220-247`; `CandidateProfile.jsx` | COMPLETE | Add related resume/application details to profile |
| Resume upload | Upload or register resume artifacts through API/UI | PDF multipart upload validates extension/content/size, stores randomized files privately, persists metadata, and supports authenticated download; candidate profile exposes upload/download | `main.py` resume routes; `CandidateProfile.jsx`; `tests/test_api.py` | COMPLETE | Use managed object storage for production scale |
| Application workflow | Apply, duplicate rejection, controlled transitions, history | Apply and stage routes enforce business rules; event rows are written; history endpoint and React timeline are exposed | `application_service.py`; `main.py`; `Applications.jsx` | COMPLETE | Continue browser coverage for stage actions |
| Screening | Explainable, job-related score with matched/missing skills | Screening service calculates score from skills/experience and returns explanation; React page has live Evaluate action and score column | `screening_service.py`; `Screening.jsx` | COMPLETE | Add richer matched/missing skill detail if API expands |
| Interview scheduling | Availability/conflict checks and status lifecycle | Scheduling service rejects inactive/overlapping interviewers; API exposes availability, rescheduling, cancellation, and completion; React page provides day/week/month calendar views | `interview_service.py`; `main.py`; `Interviews.jsx` | COMPLETE | Add deeper browser interaction coverage if required |
| Feedback | Structured ratings, recommendation, completion restriction | Feedback API validates completed interview, interviewer identity, duplicate feedback | `main.py:324-344`; `models.py:105-118` | COMPLETE | Add dedicated feedback history view |
| Offers | Salary-band validation, approval, release, acceptance/rejection | Offer service and API enforce salary and status rules; React actions expose approve, release, and accept | `offer_service.py`; `main.py`; `Offers.jsx` | COMPLETE | Add browser workflow coverage |
| Five anomalies | All required anomaly scenarios and labels | Five anomaly rows and separate ground-truth exports are generated by the dataset pipeline | `anomaly_generator.py`; `export_data.py`; MySQL validation | COMPLETE | Keep executable rejection/detection regression tests |
| Actors/RBAC | Five roles, bcrypt authentication, authorization | Roles, bcrypt, signed JWT, and permission checks exist | `auth_service.py`; `main.py`; `tests/test_auth.py` | COMPLETE | Add route-level role matrix tests |
| Metrics | Conversion, interview, offer, closure, time-to-hire, screening, feedback metrics | All requested metrics are now returned from database records; average time-to-hire is honestly `0` when no application is in `Hired` status | `backend/analytics/metrics.py`; `tests/test_analytics.py` | COMPLETE | Add historical trend endpoints if analytics scope expands |
| React modules | Dedicated functional pages for all modules | Specialized candidate profile/upload, application history timeline, screening evaluation, offer workflow, and interview day/week/month calendar pages use live APIs | `frontend/src/pages/*`; `Interviews.jsx`; Playwright smoke suite | COMPLETE | Continue expanding browser mutation coverage |
| API CRUD | Complete CRUD and workflow operations | Core create/list/update/status routes plus resume, application-history, and offer-release routes exist; some delete/detail operations remain limited | `backend/api/main.py` route inventory | PARTIAL | Add remaining resource-specific CRUD where product workflows require it |
| Security/data quality | No credentials in frontend, signed API access, non-sensitive synthetic data | Frontend has no database credentials; JWT and bcrypt are present; default development password remains documented | `frontend/src/services/api.js`; `auth_service.py`; `.env.example` | PARTIAL | Require non-default JWT secret/password outside development |
| MySQL verification | Current configured environment executes integration | Dedicated `recruitment_test` CRUD, foreign-key, and transaction checks pass; missing configuration fails rather than skips | `tests/conftest.py`; `tests/test_mysql_integration.py` | COMPLETE | Require dedicated database in CI |
| Final API workflow | Authenticated candidate-to-hired lifecycle and required negative cases | Dedicated MySQL API test passes all requested operations and validates actual offer response fields | `tests/test_api_workflow.py` | COMPLETE | Keep regression test in CI |

## Priority remediation completed after initial audit

1. Added missing database-derived metrics: total candidates, requisition closure rate, interview conversion rate, offer rate, feedback completion rate, offer acceptance rate, hired count, and average time to hire.
2. Added private PDF upload/download with validation, randomized storage names, metadata persistence, and authorization.
3. Added a deterministic hired-candidate workflow fixture and role-permission coverage.
4. Added application history timeline, live screening evaluation, and offer approve/release/accept controls.
5. Added API upload/download regression coverage and upgraded the FastAPI test-client dependency.
6. Added interview day/week/month calendar views, availability checks, conflict detection, rescheduling, and cancellation.

## Final validation evidence

```text
python -m compileall -q frontend backend tests
PASS

python -m pytest -v
11 passed

cd frontend; npm run build
PASS
```

`tests/test_mysql_integration.py` passed against the configured dedicated
`recruitment_test` database.

Completion-phase frontend evidence:

```text
cd frontend; npm run build
PASS
cd frontend; npm test
PASS: 1 test passed
cd frontend; PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run test:e2e
PASS: 2 tests passed
```

The previously recorded baseline metrics were derived from the historical
SQLite dataset:

- total candidates: 2,000
- application conversion rate: 37.87%
- interview conversion rate: 20.0%
- offer rate: 5.0%
- offer acceptance rate: 33.33%
- requisition closure rate: 36.0%
- feedback completion rate: 100.0%
- average time to hire: 0 days because the current generated dataset contains no `Hired` application

## Remaining limitations

- MySQL integration is currently verified against the configured dedicated test database; credentials are not documented or exposed.
- Some lower-priority React module pages still share the reusable table/form surface rather than providing every possible detail experience.
- Full role-by-route browser coverage remains recommended follow-up coverage; backend role permissions are tested.
- Focused workflow coverage now exercises all five anomaly decisions.
- Latest regression execution: Python compilation passed, the complete
  MySQL-backed `pytest` suite passed with 14 tests, the React production build
  passed, frontend unit tests passed, and Playwright passed 2 tests.
  both requested frontend Vitest commands passed with one test each.
- The validation page maps live validator fields (`check`, `passed`, `severity`,
  and `affected_ids`) instead of the old generic table fields.
- Analytics filters send valid ISO datetimes and keep candidate, interview,
  feedback, offer, and hiring metrics scoped to matching applications.
- The previous one-off harness `KeyError` was corrected by asserting the actual
  serialized offer response contract and by deleting the intentionally invalid
  temporary offer before creating the valid offer.
