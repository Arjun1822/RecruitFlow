# Data generation and reproducibility

## Synthetic dataset

`backend.data_generator.generator` uses Python `random`, Faker, fixed timestamps, master-data lists, and seed `20261022`. It creates fictional records only. The supported baseline sizes are:

| Size | Requisitions | Candidates | Applications | Interviews | Offers |
|---|---:|---:|---:|---:|---:|
| starter | 10 | 100 | 150 | 40 | 12 |
| full | 100 | 2,000 | 3,000 | 600 | 150 |

## Generation order

Departments and skills are inserted first, followed by requisitions and screening rules, candidates, candidate skills, resumes, applications, initial application events, interviewers, interviews, feedback, offers, approvals, and anomaly labels/evidence. Applications are sampled only from approved requisitions and the generator rejects duplicate requisition/candidate pairs before insertion.

Identifiers are deterministic: `REQ-2026-000001`, `CAND-000001`, `APP-{requisition}-{candidate}`, `INT-2026-000001`, and `OFF-2026-000001`.

## Transactions and destructive behavior

The generator deletes generated-domain rows, commits that destructive reset, then populates the new dataset and commits population work as one transaction. A population failure rolls back uncommitted population changes, but cannot undo the already committed reset. Exports run after the database commit; an export failure leaves database records committed and may leave incomplete exports.

## Safe commands

```powershell
python -m backend.database.migrate
python -m backend.data_generator.generator --size full --seed 20261022
python -m backend.validation.validator --size full
```

Run these only against an explicitly approved local MySQL database. Never point the generator at `rms_challenge` or another shared database without an approved backup/replacement plan. The configuration requires `mysql+pymysql://`; there is no SQLite fallback.

The anomaly repair utility is separate and safer for an existing challenge dataset:

```powershell
python -m backend.data_generator.repair_anomaly_fixtures --dry-run
python -m backend.data_generator.repair_anomaly_fixtures --apply
```

`--dry-run` is read-only. `--apply` is restricted to `rms_challenge`, requires exact baseline counts and stale labels, and commits one verified transaction. Do not use it as a regeneration mechanism.

## Exports

`export_data.py` writes table CSV/JSON files, `exports/sql/schema.sql`, `exports/sql/seed_data.sql`, `exports/ground_truth.csv`, `exports/ground_truth.json`, `source_manifest.json`, and `data_dictionary.xlsx`. User exports are omitted from SQL seed output and excluded by `.gitignore`.
