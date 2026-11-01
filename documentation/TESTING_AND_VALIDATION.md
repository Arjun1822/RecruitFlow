# Testing and validation

## Test architecture

Backend tests are under `tests/` and cover authentication, services, screening, analytics, API behavior, workflow completion, generation, MySQL integration, and anomaly fixtures. The React unit test is `frontend/src/App.test.jsx`; Playwright smoke coverage is under `frontend/tests/`.

Tests use dedicated MySQL targets. Shared fixtures require `recruitment_test`; anomaly fixtures require an explicit `ANOMALY_FIXTURE_DATABASE_URL` targeting exactly `recruitment_anomaly_test`. Protected application and challenge databases are rejected. Fixtures close sessions and dispose engines in cleanup paths.

## Commands

```powershell
python -m compileall -q frontend backend tests
python -m pytest -v
Set-Location frontend
npm test
npm run build
npm run test:e2e
```

The MySQL integration test requires `MYSQL_TEST_URL`. The anomaly suite requires `ANOMALY_FIXTURE_DATABASE_URL`; it has no fallback.

## Validation coverage

The validator checks:

- primary-key uniqueness and foreign-key integrity;
- required fields;
- application, offer, interview, and feedback enumerations;
- derived application identifiers and unique application pairs;
- interview time conflicts;
- missing feedback for completed interviews;
- lifecycle transition validity;
- offer salary bands, approvals, and application reconciliation;
- closed requisitions with active applications;
- expected baseline counts; and
- five positive anomaly labels and their relational evidence.

## Recorded results

The existing validation artifacts record:

- full dataset volumes of 100 requisitions, 2,000 candidates, 3,000 applications, 600 interviews, and 150 offers;
- backend integration results of 14 passed tests in the recorded validation cycle;
- frontend build success and one Vitest test passed;
- two Playwright smoke tests passed in the recorded cycle; and
- full generation/validation and export/reproducibility checks recorded as passing.

These are historical recorded results, not a claim that every command was rerun during this documentation update. A previous local run also showed the two anomaly tests blocked when `ANOMALY_FIXTURE_DATABASE_URL` was unset; blocked tests must not be reported as passed.

## Limitations

The validator's normal CLI initializes the database and writes validation exports, so it is not a pure read-only verifier. Browser coverage is narrower than API workflow coverage. The documented environment still requires an approved MySQL configuration before a submission run.
