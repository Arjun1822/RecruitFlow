from fastapi import Depends, Header, HTTPException

from backend.authentication.auth_service import decode_access_token
from backend.database.connection import SessionLocal
from backend.database.models import User


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    authorization: str | None = Header(default=None),
    db=Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        claims = decode_access_token(authorization[7:])
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    username = claims["sub"]
    session = db
    user = session.query(User).filter(User.username == username, User.active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user
