# Validation and Limitations

## Verified commands

The following results were executed in the current validation cycle:

| Command | Result |
|---|---|
| `python -m compileall -q frontend backend tests` | PASS |
| `python -m pytest -v` | PASS — 14 passed against dedicated MySQL |
| `cd frontend; npm run build` | PASS |
| `cd frontend; npm test` | PASS — 1 test |
| `cd frontend; npm run test` | PASS — 1 test |
| `cd frontend; npm run test:e2e` | PASS — 2 Playwright smoke tests |
| `python -m pytest -q tests/test_mysql_integration.py` | PASS — 1 test |
| Full MySQL generation and validation | PASS — 100/2,000/3,000/600/150; 50 checks, 0 failures |
| `npx playwright install chromium` | PASS |

The backend suite includes the isolated authenticated API workflow in
`tests/test_api_workflow.py`. It uses the dedicated MySQL test database and
does not modify the production database or `.env`.

## Workflow validation

The isolated API workflow verifies candidate registration, private PDF
upload/download, application creation, screening, valid stage progression,
interview scheduling, availability/conflict rules, feedback, offer creation,
approval, release, acceptance, hired status, analytics, and validation details.

## Required anomaly scenarios

The generator stores five positive anomaly labels plus one
`anomaly_fixture_evidence` row per label. Evidence references valid records and
describes the intentional condition without violating primary keys or foreign
keys. Duplicate applications are represented as a rejected duplicate-attempt
record, not as a second row that would violate `uq_application_pair`.

The focused anomaly tests require an explicit environment variable:

```powershell
$env:ANOMALY_FIXTURE_DATABASE_URL="mysql+pymysql://<user>:<password>@localhost:3306/recruitment_anomaly_test?charset=utf8mb4"
python -m pytest tests/test_anomaly_fixtures.py -v
```

The test rejects `rms`, `rms_challenge`, `DATABASE_URL`, and `MYSQL_TEST_URL`.
It parses and normalizes each URL's scheme, case-insensitive host, port
(defaulting an omitted MySQL port to `3306`), and database name, so changing
credentials or URL formatting cannot bypass same-target protection.
The anomaly and shared MySQL fixtures release their sessions and engines even
when setup or cleanup raises an exception.
It creates missing tables through SQLAlchemy, clears only the dedicated
`recruitment_anomaly_test` schema before each test, and clears only that schema
after each test. The global `MYSQL_TEST_URL` cleanup fixture is explicitly
disabled for this module.

The validator reports ordinary baseline checks separately from
`Intentional anomaly fixtures` and `Unlabelled data-quality violations`.
Only the exact labelled fixture records are excluded from the corresponding
ordinary checks; unrelated failures remain failures. In particular, the
closed-requisition fixture excludes only its evidence-linked application.
Other active applications under the same closed requisition remain ordinary
violations.

For an existing `rms_challenge` database whose five labels predate evidence
generation, the non-destructive repair utility can first be inspected with:

```powershell
python -m backend.data_generator.repair_anomaly_fixtures --dry-run
```

The utility requires exactly five baseline counts (100 requisitions, 2,000
candidates, 3,000 applications, 600 interviews, and 150 offers), exactly the
five existing positive labels, and zero existing evidence rows. It never
initializes or resets the schema. `--dry-run` performs read-only inspection;
`--apply` is the only mode that writes, and it commits one transaction only
after all five anomaly conditions verify. It inserts five evidence rows, two
valid lifecycle events, and five audit rows while preserving baseline IDs and
counts. The closed-requisition repair is pinned to `REQ-2026-000051` and
requires exactly 27 active applications, exactly one labelled active
application (`APP-REQ-2026-000051-CAND-000002`), no offers on those active
applications, and exactly 26 valid transitions to `Rejected`. Post-change
verification independently checks offer reconciliation. No `--apply`
execution is part of this validation report.

The following cases are exercised by workflow and validation tests:

1. Duplicate application — rejected by application uniqueness/business rules.
2. Unavailable interviewer — rejected when the interviewer is inactive.
3. Missing feedback — progression is rejected until mandatory feedback exists.
4. Salary outside approved band — offer approval is rejected.
5. Closed requisition with active applications — validation reports the affected
   records.

Invalid application stage transitions and unauthorized offer approval are also
verified.

To apply the new `anomaly_fixture_evidence` schema against an explicitly
configured MySQL database, run:

```powershell
python -m backend.database.migrate
```

To regenerate the challenge dataset after approval, using only the root
`.env` `DATABASE_URL`, run:

```powershell
python -m backend.data_generator.generator --size full --seed 20261022
```

The generator is destructive for generated-domain tables and must not be run
against an existing database without an approved backup and replacement plan.
The destructive reset is committed before population begins and cannot be
rolled back by a later failure. All population work is then committed as one
transaction; failures before that commit roll back uncommitted population
changes. The generator closes its session and disposes its engine on every
generation path, including failures during reset, population, or export.
Exports run after the database commit. If export generation fails, the command
reports that the database records remain committed; rollback cannot undo that
completed database commit, and exports may be incomplete.

## Limitations

- Playwright currently covers login/dashboard and interview navigation; the full
  mutation workflow is verified through authenticated FastAPI integration tests,
  not through one browser mutation journey.
- MySQL is mandatory. Missing or unreachable MySQL configuration is a startup
  or test failure, not a fallback condition.
- The local `.env` inspected during this audit still has a legacy SQLite
  `DATABASE_URL`; it was not changed because database credentials and the
  application database were not to be modified. Copy `.env.example` values and
  provide an approved MySQL URL before starting the application.
- MFA, SSO, password reset, and production secret-manager integration are not
  implemented.
- The repository contains a development admin bootstrap password in source/test
  defaults. This is not repeated here; the author must confirm whether it is
  removed or replaced before submission. The application no longer provisions
  it automatically; administrator creation now requires explicit configuration.
- Generated user exports contain usernames and password hashes. The user export
  files are now excluded by `.gitignore`; remove any already-tracked copies
  from the submission explicitly if this workspace is later placed under Git.
- API user serialization and generated seed exports now exclude password hashes.
- Production configuration fails closed when `RMS_JWT_SECRET` is missing.

## Claim policy

Only the commands and results listed above are verified by the current
artifacts. Personal contribution, AI prompt history, submission dates, and
claims about unobserved development work require author confirmation.

## Documentation status

This document and the companion documentation set were reviewed against the
source tree, ORM models, route decorators, service implementations, generator,
validator, tests, and existing exports. No application code or database was
executed or changed during the documentation review. The result is a source-
anchored description; recorded test results above remain historical evidence
and are not silently upgraded to new passes.
