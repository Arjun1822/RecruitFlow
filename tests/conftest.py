import pytest
from sqlalchemy import delete
from sqlalchemy.engine import make_url

from backend.config import DATABASE_URL, require_mysql_test_url
from backend.database.models import Base


def _database_identity(url: str) -> tuple[str, str, int, str]:
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise ValueError("Database URL must be a valid SQLAlchemy URL") from exc
    if parsed.drivername != "mysql+pymysql" or not parsed.host or not parsed.database:
        raise ValueError("Database URL must include a MySQL scheme, host, and database")
    try:
        port = parsed.port or 3306
    except ValueError as exc:
        raise ValueError("Database URL must use a valid port") from exc
    return (
        parsed.drivername.lower(),
        parsed.host.lower(),
        port,
        parsed.database,
    )


def _clear_database(session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(delete(table))
    session.commit()


@pytest.fixture(scope="session")
def mysql_database_url():
    url = require_mysql_test_url()
    if _database_identity(url)[3] != "recruitment_test":
        raise RuntimeError("MYSQL_TEST_URL must target the dedicated recruitment_test database")
    if _database_identity(url) == _database_identity(DATABASE_URL):
        raise RuntimeError("MYSQL_TEST_URL must not equal the application DATABASE_URL")
    return url


@pytest.fixture(autouse=True)
def clean_mysql_test_database(request):
    if request.module.__name__.endswith("test_anomaly_fixtures"):
        yield
        return
    mysql_database_url = require_mysql_test_url()
    if _database_identity(mysql_database_url)[3] != "recruitment_test":
        raise RuntimeError("MYSQL_TEST_URL must target the dedicated recruitment_test database")
    if _database_identity(mysql_database_url) == _database_identity(DATABASE_URL):
        raise RuntimeError("MYSQL_TEST_URL must not equal the application DATABASE_URL")
    from backend.database.connection import make_session

    session = None
    engine = None
    try:
        session = make_session(mysql_database_url)
        engine = session.get_bind()
        _clear_database(session)
        yield
    finally:
        try:
            if session is not None:
                try:
                    session.rollback()
                finally:
                    try:
                        _clear_database(session)
                    finally:
                        session.close()
        finally:
            if engine is not None:
                engine.dispose()
