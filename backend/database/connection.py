from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import DATABASE_URL

def make_engine(database_url=DATABASE_URL):
    if not database_url.startswith("mysql+pymysql://"):
        raise ValueError("RecruitFlow requires a MySQL database URL")
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )

engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def init_db(bind=engine) -> None:
    from .models import Base
    Base.metadata.create_all(bind=bind)

def make_session(database_url=DATABASE_URL):
    local_engine = make_engine(database_url)
    try:
        init_db(local_engine)
        session = sessionmaker(bind=local_engine, autoflush=False, expire_on_commit=False)()
    except Exception:
        local_engine.dispose()
        raise
    return session
