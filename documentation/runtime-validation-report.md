# Runtime Validation Report

**Generated**: 2026-11-01  
**Target**: `C:\Users\aduva\OneDrive\Desktop\yottaflex`

## Summary

| Step | Status | Exit code | Details |
|---|---|---:|---|
| Full dataset generation | PASS | 0 | 100 requisitions, 2,000 candidates, 3,000 applications, 600 interviews, 150 offers |
| Comprehensive validation | PASS | 0 | Primary keys, foreign keys, mandatory fields, enums, dates, conflicts, feedback, transitions, offers, reconciliation, closed requisitions, counts |
| Automated tests | PASS | 0 | 14 passed, 0 failed against dedicated MySQL |
| Authenticated API workflow acceptance | PASS | 0 | Dedicated MySQL workflow covering candidate through hired plus all requested negative cases |
| Five anomaly scenarios | PASS | 0 | All five independently exercised and detected |
| Export round-trip | PASS | 0 | CSV, JSON, Excel data dictionary, SQL schema and seed data |
| Fixed-seed reproducibility | PASS | 0 | Independent starter databases produced identical SHA-256 snapshots |
| Streamlit startup | NOT RE-RUN | n/a | Historical result retained; current runtime configuration requires MySQL |
| Browser smoke tests | PASS | 0 | Playwright Chromium available; 2 tests passed |

**Overall**: NEEDS SIGNOFF — code and dedicated MySQL verification pass, but the
local root `.env` still contains a legacy SQLite URL and was intentionally not
modified without approval or credentials.

## Environment

```text
docker: UNAVAILABLE — docker command not installed
node: AVAILABLE — v22.15.0
playwright: AVAILABLE — npx playwright install chromium succeeded
infra-tier: PRIMARY(MySQL 8) — runtime and isolated workflow use configured MySQL databases
browser-tier: PRIMARY(Playwright) — Chromium screenshot completed successfully
```

The browser application was started with:

```powershell
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Readiness was verified with `http://127.0.0.1:8000/docs` while injecting the
dedicated MySQL URL into the process environment, and Playwright completed the
two browser smoke tests. The checked-in `.env.example` now contains only a
MySQL placeholder; the local `.env` must be updated by the operator.

## Authenticated workflow evidence

`tests/test_api_workflow.py` runs against the dedicated MySQL test database. It logs
in as recruiter, process owner, and approver; registers a candidate; uploads
and downloads a private PDF; creates an application; checks duplicate and
invalid-stage rejection; evaluates screening; schedules an interview; checks
conflict and inactive-interviewer rejection; verifies mandatory feedback gating;
submits feedback; checks salary-band rejection; verifies unauthorized approval
rejection; approves, releases, and accepts an offer; and asserts analytics and
validation response structures.

Offer responses are asserted against the actual serialized API schema:
`id`, `application_id`, `salary`, and `status`.

## Issues found and corrected

1. Full generation could produce fewer than 3,000 applications because duplicate random pairs consumed attempts. The generator now loops until the exact target count is reached.
2. Tests previously mutated the shared `rms.db`. Tests now require and clean
   the dedicated MySQL test database through `tests/conftest.py`.
3. SQL exports were previously a placeholder. The generator now emits `exports/sql/schema.sql` and `exports/sql/seed_data.sql`.
4. Generated timestamps made fixed-seed checksums differ. Synthetic timestamps are now fixed to the seeded generation time.
5. Random interview scheduling generated unintended overlaps. Baseline interviews now use deterministic non-overlapping interviewer windows.
6. Applications could be created for closed requisitions and offers could have inconsistent approval metadata. Baseline generation now uses approved requisitions for applications and coherent offer statuses.
7. Duplicate offers were allowed to fail as a raw database error. The offer service now raises a clear business-rule `ValueError`.
8. Validation covered only a subset of requested checks. It now includes primary-key uniqueness, foreign keys, mandatory fields, enumerations, derived IDs, duplicate applications, conflicts, feedback, transitions, salary bands, approvals, reconciliation, closed requisitions, and expected counts.

## Anomaly evidence

The separate files `exports/ground_truth.csv` and `exports/ground_truth.json` each contain five labeled scenarios:

1. Unavailable interviewer
2. Duplicate application
3. Missing interview feedback
4. Offer salary outside approved band
5. Closed requisition with active applications

Each scenario was executed independently against an isolated database. All five produced the expected rejection or validation result.

## Data and schema evidence

The MySQL schema contains the requested core entities plus application events,
approval history, audit logs, anomalies, users, and exception resolutions.
MySQL foreign-key checks returned no violations. The latest starter dataset
validation executed 55 checks with zero failures. Full-volume counts remain a
separate production-scale generation step and were not run against application
data during this audit.

Dashboard metric base values were compared with direct SQL counts:

| Metric | Dashboard/service | Direct SQL |
|---|---:|---:|
| Applications | 3,000 | 3,000 |
| Shortlisted-or-later applications | 1,136 | 1,136 |
| Interviews | 600 | 600 |
| Offers | 150 | 150 |
| Accepted offers | 50 | 50 |

## Remaining limitations

- Docker is unavailable, but the configured MySQL integration and workflow tests
  run directly against MySQL.
- The Streamlit UI currently exposes Dashboard, Applications, Exceptions, and Validation pages. The service layer contains the workflow operations, but the full set of requested CRUD/admin pages is not yet surfaced in the UI.
- Production authentication, password hashing, and backend-enforced role administration are not wired to an identity provider.
- The test suite emits SQLAlchemy deprecation warnings for `datetime.utcnow()` defaults; these do not currently fail tests but should be migrated to timezone-aware UTC values.
- Ground-truth anomaly records are kept separate from baseline data; the valid baseline intentionally does not contain corrupted records. The five invalid conditions are exercised by isolated QA fixtures.
- Browser mutation coverage remains narrower than API coverage: the browser
  suite verifies login/dashboard and interview navigation, while the complete
  mutation workflow is covered by authenticated FastAPI integration testing.
