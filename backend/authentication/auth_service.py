from datetime import datetime, timedelta, timezone
import base64
import bcrypt
import hashlib
import hmac
import json
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.database.models import AuditLog, User, utc_now
from backend.config import ADMIN_REGISTRATION_ENABLED, JWT_EXPIRE_MINUTES, JWT_SECRET

ROLES = {"Business Requester", "Process Owner", "Approver", "Operations Analyst", "System Administrator"}
PERMISSIONS = {
    "Business Requester": {"view_dashboard", "manage_requisitions", "manage_candidates", "manage_applications"},
    "Process Owner": {"view_dashboard", "manage_requisitions", "manage_candidates", "manage_applications", "manage_interviews", "manage_feedback", "manage_offers"},
    "Approver": {"view_dashboard", "approve_requisitions", "approve_offers", "view_audit"},
    "Operations Analyst": {"view_dashboard", "manage_candidates", "manage_applications", "manage_interviews", "manage_feedback", "view_analytics", "view_exceptions"},
    "System Administrator": {"*", "manage_users"},
}

def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def has_permission(user: User, permission: str) -> bool:
    return user is not None and user.active and ("*" in PERMISSIONS.get(user.role, set()) or permission in PERMISSIONS.get(user.role, set()))

ADMIN_REGISTRATION_LOCK = "recruitflow:first-administrator"


def admin_registration_available(session) -> bool:
    return ADMIN_REGISTRATION_ENABLED and not session.scalar(
        select(User.id).where(User.role == "System Administrator").limit(1)
    )


def register_admin(session, username: str, password: str) -> User:
    if not ADMIN_REGISTRATION_ENABLED:
        raise PermissionError("Administrator registration is disabled")
    if not username.strip():
        raise ValueError("Administrator username is required")
    if len(username) > 100:
        raise ValueError("Administrator username is too long")

    connection = session.get_bind().connect()
    transaction = connection.begin()
    registration_session = Session(bind=connection, autoflush=False, expire_on_commit=False)
    lock_acquired = False
    try:
        lock_acquired = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 10)"),
            {"lock_name": ADMIN_REGISTRATION_LOCK},
        ).scalar() == 1
        if not lock_acquired:
            raise RuntimeError("Administrator registration is busy; try again")

        if registration_session.scalar(select(User.id).where(User.role == "System Administrator").limit(1)):
            raise ValueError("Administrator registration is no longer available")
        if registration_session.scalar(select(User.id).where(User.username == username)):
            raise ValueError("Administrator username already exists")

        user = User(
            username=username,
            password_hash=hash_password(password),
            role="System Administrator",
        )
        registration_session.add(user)
        registration_session.flush()
        registration_session.add(AuditLog(
            actor=username,
            action="REGISTER_ADMIN",
            entity_type="User",
            entity_id=str(user.id),
            details="First administrator registered",
        ))
        registration_session.flush()
        transaction.commit()
        return user
    except Exception:
        if transaction.is_active:
            transaction.rollback()
        raise
    finally:
        if lock_acquired:
            try:
                connection.execute(
                    text("SELECT RELEASE_LOCK(:lock_name)"),
                    {"lock_name": ADMIN_REGISTRATION_LOCK},
                )
            finally:
                connection.rollback()
        registration_session.close()
        connection.close()

def authenticate(session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username))
    if not user or not user.active or (user.locked_until and user.locked_until > utc_now()):
        return None
    if verify_password(password, user.password_hash):
        user.failed_login_attempts = 0; user.last_login_at = utc_now()
        session.add(AuditLog(actor=username, action="LOGIN", entity_type="User", entity_id=str(user.id), details="successful"))
        session.commit(); return user
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
        user.locked_until = utc_now() + timedelta(minutes=15)
    session.add(AuditLog(actor=username, action="LOGIN_FAILURE", entity_type="User", entity_id=str(user.id) if user else "unknown", details="invalid credentials"))
    session.commit(); return None

def require_permission(user: User, permission: str) -> None:
    if not has_permission(user, permission):
        raise PermissionError(f"Role {user.role if user else 'anonymous'} lacks {permission}")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user: User) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({
        "sub": user.username,
        "role": user.role,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
    }, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode()
        expected = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            raise ValueError("Invalid token signature")
        data = json.loads(_unb64(payload))
        if int(data["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")
        if data.get("sub") is None:
            raise ValueError("Token subject missing")
        return data
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid authentication token") from error
