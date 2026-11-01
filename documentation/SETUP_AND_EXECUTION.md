# Setup and execution

These instructions target Windows 11 and PowerShell.

## Prerequisites

- Python 3.12 or a supported compatible version
- Node.js and npm
- MySQL 8

## Python environment

```powershell
Set-Location C:\Users\aduva\OneDrive\Desktop\yottaflex
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set an approved local MySQL `DATABASE_URL` in `.env`; do not paste credentials into documentation.

## Database initialization

```powershell
python -m backend.database.migrate
```

The runtime requires `mysql+pymysql://`. Create a local database and least-privilege user through an approved MySQL administration process. Do not use the challenge database for development experiments.

## Start the application

Terminal 1:

```powershell
python -m uvicorn backend.api.main:app --reload --port 8000
```

Terminal 2:

```powershell
Set-Location C:\Users\aduva\OneDrive\Desktop\yottaflex\frontend
npm ci
npm run dev
```

URLs:

- React: `http://localhost:5173`
- API: `http://localhost:8000`
- OpenAPI UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Dataset and validation

```powershell
Set-Location C:\Users\aduva\OneDrive\Desktop\yottaflex
python -m backend.data_generator.generator --size starter --seed 20261022
python -m backend.data_generator.generator --size full --seed 20261022
python -m backend.validation.validator --size full
```

The generator is destructive and must not target `rms_challenge`. For an existing challenge database, inspect the anomaly repair with `--dry-run` first; do not run `--apply` without explicit approval.

## Testing

```powershell
python -m compileall -q frontend backend tests
python -m pytest -v
Set-Location frontend
npm test
npm run build
npm run test:e2e
```

Configure `MYSQL_TEST_URL` for the shared MySQL integration test and `ANOMALY_FIXTURE_DATABASE_URL` for the isolated anomaly suite. Missing required URLs are configuration blockers, not successful test results.

## Troubleshooting

- **MySQL URL rejected:** confirm the scheme is `mysql+pymysql://`, host, port, and database.
- **Admin registration unavailable:** set `RMS_ADMIN_REGISTRATION_ENABLED=true` only in a local development process, open the React app from localhost, and use the one-time **Create the first administrator** form. Registration is disabled by default and never available in production.
- **Uploads rejected:** use a real PDF beginning with `%PDF-` and stay within `MAX_RESUME_BYTES`.
- **Anomaly tests fail at setup:** set `ANOMALY_FIXTURE_DATABASE_URL` to a dedicated `recruitment_anomaly_test` database.
- **Frontend cannot reach API:** start Uvicorn and set `VITE_API_URL` only in the frontend environment when the API is not local.
