# Security and configuration

## Configuration

Configuration is loaded from environment variables, with the local `.env` used only as a developer source. Do not copy secret values into documentation or source control. `.env.example` is the safe template.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Required `mysql+pymysql://` runtime URL |
| `MYSQL_TEST_URL` | Dedicated shared integration-test URL |
| `ANOMALY_FIXTURE_DATABASE_URL` | Dedicated anomaly-test URL |
| `RMS_SEED` | Generator seed, default `20261022` |
| `RMS_ENV` | Environment mode; production requires JWT secret |
| `RMS_JWT_SECRET` | HS256 signing secret |
| `RMS_JWT_EXPIRE_MINUTES` | Token lifetime, default 30 |
| `RMS_ADMIN_REGISTRATION_ENABLED` | Enables one-time localhost administrator registration; defaults to `false` and is always disabled in production |
| `PRIVATE_UPLOAD_DIR` | Code default private upload location |
| `MAX_RESUME_BYTES` | Upload limit, default 5 MiB |

## Authentication and authorization

Passwords are stored as bcrypt hashes and require at least 12 characters when created. JWTs use an HS256 signature and configurable expiry. Every protected request must carry a valid Bearer token whose subject maps to an active user. Role permissions are checked in service functions and routes.

The first administrator is created through `POST /api/auth/register-admin` only when registration is explicitly enabled, the request client IP is `127.0.0.1` or `::1`, and no System Administrator exists. Forwarded IP headers are not trusted. MySQL `GET_LOCK` serializes concurrent first-registration requests; the user and registration audit record commit in one transaction. Registration is never available in production. The former environment-based administrator provisioning mechanism has been removed.

Login success and failure are audited. Five failed attempts set a 15-minute lock. Logout is stateless and currently removes the token on the client; server-side revocation is not implemented.

## Input and data protection

Pydantic models enforce field lengths and numeric ranges. SQLAlchemy expressions and ORM queries are used for application data access; the validator quotes inspected identifiers when building metadata checks. Resume uploads require a PDF extension, accepted content type, PDF signature, and size limit. Stored files use randomized names and downloads enforce path confinement.

Exports intentionally omit user table data from SQL seed output. Generated user CSV/JSON exports are excluded by `.gitignore`; any already-tracked copies would need explicit removal before submission.

## Production requirements

Use MySQL 8, a secret manager or protected environment injection for credentials and JWT secrets, HTTPS at the deployment boundary, restricted database permissions, and a private upload volume. MFA, SSO, password reset, and production secret-manager integration are future work rather than implemented features.
