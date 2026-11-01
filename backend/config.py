import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be configured for the MySQL runtime")
if not DATABASE_URL.startswith("mysql+pymysql://"):
    raise RuntimeError("DATABASE_URL must use the MySQL driver (mysql+pymysql://)")
SEED = int(os.getenv("RMS_SEED", "20261022"))
EXPORT_DIR = BASE_DIR / "exports"
PRIVATE_UPLOAD_DIR = BASE_DIR / "private_uploads"
MAX_RESUME_BYTES = int(os.getenv("MAX_RESUME_BYTES", str(5 * 1024 * 1024)))
DATA_VERSION = "1.0.0"
RMS_ENV = os.getenv("RMS_ENV", "development").strip().lower()
JWT_SECRET = os.getenv("RMS_JWT_SECRET")
if RMS_ENV == "production" and not JWT_SECRET:
    raise RuntimeError("RMS_JWT_SECRET must be configured in production")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(32)
JWT_EXPIRE_MINUTES = int(os.getenv("RMS_JWT_EXPIRE_MINUTES", "30"))
ADMIN_REGISTRATION_ENABLED = (
    RMS_ENV != "production"
    and os.getenv("RMS_ADMIN_REGISTRATION_ENABLED", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)


def mysql_test_url() -> str | None:
    """Return the configured MySQL test URL without exposing its credentials."""
    value = os.getenv("MYSQL_TEST_URL")
    return value.strip() if value and value.strip() else None


def require_mysql_test_url() -> str:
    """Require a MySQL test URL for commands that explicitly target MySQL."""
    value = mysql_test_url()
    if not value:
        raise RuntimeError(
            "MYSQL_TEST_URL is not configured. Set it in the project .env file "
            "or in the environment before running MySQL integration tests."
        )
    if not value.startswith("mysql+pymysql://"):
        raise ValueError("MYSQL_TEST_URL must use mysql+pymysql:// and target a dedicated test database.")
    return value
