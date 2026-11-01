# Source manifest

The canonical generated manifest is [../exports/source_manifest.json](../exports/source_manifest.json). It is produced by `backend/data_generator/export_data.py`.

Generated exports contain fictional records created locally by the deterministic generator with seed `20261022`. The manifest records, for each exported table, the dataset filename, record count, generation method, seed, dataset version, provenance, and synthetic-data license note.

## Important source components

| Component | Purpose |
|---|---|
| `backend/database/models.py` | ORM schema and constraints |
| `backend/api/main.py` | FastAPI routes and request models |
| `backend/services/` | Workflow rules |
| `backend/data_generator/generator.py` | Seeded dataset creation |
| `backend/data_generator/anomaly_generator.py` | Five anomaly labels/evidence |
| `backend/data_generator/export_data.py` | CSV, JSON, SQL, XLSX, and manifest outputs |
| `backend/validation/validator.py` | Integrity and business-rule checks |
| `frontend/src/` | React/Vite workspace |
| `tests/` and `frontend/tests/` | Backend, integration, unit, and browser coverage |

## Generated outputs

The export set includes table CSV/JSON files, `ground_truth.csv`, `ground_truth.json`, `schema.sql`, `seed_data.sql`, `data_dictionary.xlsx`, and `source_manifest.json`. User rows are excluded from SQL seed output. The manifest is evidence of local synthetic provenance, not a claim that a database was queried during a documentation-only review.
