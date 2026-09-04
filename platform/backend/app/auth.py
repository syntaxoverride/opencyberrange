"""
Authentication utilities and dependencies
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


PRIVILEGED_PASSWORD_MIN_LENGTH = 14


def validate_privileged_password(password: str) -> Optional[str]:
    """Password policy for instructor/admin accounts.

    Returns an error message when the password is too weak, else None.
    Privileged accounts authenticate from the open internet, so they carry
    a stricter policy than the 8-char student minimum.
    """
    if len(password) < PRIVILEGED_PASSWORD_MIN_LENGTH:
        return (
            f"Instructor/admin passwords must be at least "
            f"{PRIVILEGED_PASSWORD_MIN_LENGTH} characters"
        )
    classes = sum([
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ])
    if classes < 3:
        return (
            "Instructor/admin passwords need at least three of: lowercase, "
            "uppercase, digit, symbol"
        )
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with a unique jti claim for revocation support."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


# ─── Token Revocation (DB-backed) ────────────────────────────────────
# Revocations live in the revoked_tokens table so they apply across every
# uvicorn worker (the old in-process dict was invisible to sibling workers).
# Two row shapes share the table:
#   jti = "<uuid>"                  one specific token is dead
#   jti = "revoke-all:<username>"   tokens issued before revoked_at are dead
# Rows older than the JWT lifetime are pruned opportunistically; by then the
# tokens they refer to have expired on their own.

_REVOKE_ALL_PREFIX = "revoke-all:"


def _revocation_sentinel(username: str) -> str:
    """Sentinel jti for a per-user mass revocation row.

    The jti column is 64 chars and usernames are capped at 50, so the
    truncation guard never fires in practice."""
    return f"{_REVOKE_ALL_PREFIX}{username}"[:64]


def _prune_expired_revocations(db) -> None:
    """Delete revocation rows older than the JWT lifetime plus slack."""
    from app.models import RevokedToken
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.JWT_EXPIRATION_HOURS + 1
    )
    db.query(RevokedToken).filter(RevokedToken.revoked_at < cutoff).delete(
        synchronize_session=False
    )


def revoke_token(jti: str, expires_at_epoch: float, user_id: Optional[int] = None) -> None:
    """Persist a token's jti to the revocation table.

    expires_at_epoch is kept for API compatibility; pruning now keys off
    revoked_at instead. user_id is required because the revoked_tokens
    table attributes every row to an account."""
    if user_id is None:
        raise ValueError("revoke_token requires user_id for DB-backed revocation")
    from app.database import SessionLocal
    from app.models import RevokedToken
    db = SessionLocal()
    try:
        _prune_expired_revocations(db)
        if db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is None:
            db.add(RevokedToken(
                jti=jti,
                user_id=user_id,
                revoked_at=datetime.now(timezone.utc),
            ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist token revocation for jti %s", jti)
        raise
    finally:
        db.close()


def revoke_all_user_tokens(username: str) -> None:
    """Revoke every outstanding token for a user.

    Writes (or refreshes) a per-user sentinel row; tokens whose iat predates
    the sentinel's revoked_at are rejected in _decode_token(). DB-backed, so
    the revocation is visible to all workers immediately."""
    from app.database import SessionLocal
    from app.models import RevokedToken
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return
        sentinel = _revocation_sentinel(username)
        now = datetime.now(timezone.utc)
        row = db.query(RevokedToken).filter(RevokedToken.jti == sentinel).first()
        if row is None:
            db.add(RevokedToken(jti=sentinel, user_id=user.id, revoked_at=now))
        else:
            row.revoked_at = now
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist mass revocation for user %s", username)
        raise
    finally:
        db.close()


def is_token_revoked(jti: str) -> bool:
    """Check if a specific token has been revoked by jti."""
    from app.database import SessionLocal
    from app.models import RevokedToken
    db = SessionLocal()
    try:
        return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None
    finally:
        db.close()


def _check_token_revocation(username: str, jti: Optional[str], iat_epoch: float) -> bool:
    """Return True when the token is revoked, either individually (jti row)
    or by a per-user mass revocation issued after the token's iat.

    Fails open with a logged warning if the revoked_tokens table is missing,
    so a half-deployed schema does not lock everyone out."""
    from app.database import SessionLocal
    from app.models import RevokedToken
    keys = [_revocation_sentinel(username)]
    if jti:
        keys.append(jti)
    db = SessionLocal()
    try:
        rows = db.query(RevokedToken).filter(RevokedToken.jti.in_(keys)).all()
        for row in rows:
            if jti and row.jti == jti:
                return True
            if row.jti.startswith(_REVOKE_ALL_PREFIX):
                revoked_at = row.revoked_at
                if revoked_at.tzinfo is None:
                    revoked_at = revoked_at.replace(tzinfo=timezone.utc)
                if iat_epoch < revoked_at.timestamp():
                    return True
        return False
    except Exception:
        logger.warning(
            "Revocation check failed (revoked_tokens table missing or DB error); "
            "treating token as not revoked", exc_info=True
        )
        return False
    finally:
        db.close()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


# Account lockout constants
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.
    Implements account lockout after MAX_FAILED_ATTEMPTS failures.
    
    Args:
        db: Database session
        username: User's username
        password: User's plaintext password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    # Check if account is locked
    if user.is_locked:
        # Check if lockout period has expired
        if user.locked_at:
            locked_at = user.locked_at
            # Ensure timezone awareness
            if locked_at.tzinfo is None:
                locked_at = locked_at.replace(tzinfo=timezone.utc)
            
            lockout_expires = locked_at + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            
            if datetime.now(timezone.utc) > lockout_expires:
                # Lockout expired, unlock the account
                user.is_locked = False
                user.failed_attempts = 0
                user.locked_at = None
                db.commit()
            else:
                # Still locked - return None without incrementing attempts
                return None
        else:
            # Locked without timestamp (manual lock by admin), don't auto-unlock
            return None
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        # Increment failed attempts
        user.failed_attempts = (user.failed_attempts or 0) + 1
        
        # Check if we should lock the account
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.is_locked = True
            user.locked_at = datetime.now(timezone.utc)
        
        db.commit()
        return None
    
    # Successful login - reset failed attempts
    if user.failed_attempts and user.failed_attempts > 0:
        user.failed_attempts = 0
        db.commit()
    
    return user


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token, returning the full payload.
    Raises HTTPException on invalid/revoked tokens."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # One DB round trip covers both individual (jti) revocation and
        # per-user mass revocation (e.g. admin force-logout).
        if _check_token_revocation(username, payload.get("jti"), payload.get("iat", 0)):
            raise credentials_exception

        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token.

    Checks:
      1. Token is valid and not expired (jose handles this)
      2. Token's jti has not been individually revoked
      3. Token was not issued before a per-user revocation timestamp
      4. User still exists in the database

    For impersonation tokens (imp=True), returns the impersonated user
    but attaches impersonation metadata to the user object.
    """
    payload = _decode_token(token)
    username = payload.get("sub")

    user = get_user_by_username(db, username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach impersonation metadata if present
    user._imp = payload.get("imp", False)
    user._imp_original_id = payload.get("imp_original_id")
    user._imp_original_username = payload.get("imp_original")
    user._imp_mode = payload.get("imp_mode")
    user._imp_course_id = payload.get("imp_course_id")
    user._imp_read_only = payload.get("imp_read_only", False)

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active and approved user"""
    # Check if is_active column exists (for backward compatibility)
    if hasattr(current_user, 'is_active') and not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if not current_user.is_approved:
        raise HTTPException(status_code=403, detail="User not approved")
    if current_user.is_locked:
        raise HTTPException(status_code=403, detail="User account is locked")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current admin user"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


async def get_current_instructor_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require instructor or admin role"""
    if current_user.role not in ('instructor', 'admin'):
        raise HTTPException(status_code=403, detail="Instructor access required")
    return current_user


# ─── Impersonation Helpers ──────────────────────────────────────

def is_impersonating(user: User) -> bool:
    """Check if the current request is an impersonation session."""
    return getattr(user, '_imp', False)


async def enforce_not_impersonating(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency that blocks mutating endpoints during impersonation.
    Returns 403 with impersonating flag so the frontend can show a toast."""
    if is_impersonating(current_user):
        raise HTTPException(
            status_code=403,
            detail="Action blocked: you are viewing as another user",
            headers={"X-Impersonating": "true"},
        )
    return current_user


def create_impersonation_token(
    original_user: User,
    target_username: str,
    target_role: str,
    mode: str,
    course_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT for an impersonation session.
    The token carries the target identity plus original-user metadata."""
    if expires_delta is None:
        expires_delta = timedelta(hours=1)
    data = {
        "sub": target_username,
        "imp": True,
        "imp_original": original_user.username,
        "imp_original_id": original_user.id,
        "imp_mode": mode,
        "imp_read_only": True,
    }
    if course_id is not None:
        data["imp_course_id"] = course_id
    return create_access_token(data, expires_delta=expires_delta)


# ─── WebSocket Ticket System ────────────────────────────────────────
# Short-lived, single-use tickets that replace JWT in WebSocket URLs.
# Prevents long-lived JWTs from leaking into logs and browser history.
# Stored in the database so tickets work across multiple uvicorn workers.

_WS_TICKET_TTL = 30  # seconds


def create_ws_ticket(user_id: int) -> str:
    """Generate a single-use, 30-second ticket for WebSocket authentication."""
    from app.database import SessionLocal
    ticket = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=_WS_TICKET_TTL)
    db = SessionLocal()
    try:
        # Prune expired tickets while we're here
        db.execute(
            __import__('sqlalchemy').text("DELETE FROM ws_tickets WHERE expires_at < :now"),
            {"now": datetime.now(timezone.utc)}
        )
        db.execute(
            __import__('sqlalchemy').text(
                "INSERT INTO ws_tickets (ticket, user_id, expires_at) VALUES (:ticket, :user_id, :expires_at)"
            ),
            {"ticket": ticket, "user_id": user_id, "expires_at": expires}
        )
        db.commit()
    finally:
        db.close()
    return ticket


def validate_ws_ticket(ticket: str) -> Optional[int]:
    """Validate and consume a single-use WebSocket ticket.
    Returns user_id on success, None on failure or expiry."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        row = db.execute(
            __import__('sqlalchemy').text(
                "DELETE FROM ws_tickets WHERE ticket = :ticket RETURNING user_id, expires_at"
            ),
            {"ticket": ticket}
        ).fetchone()
        if row is None:
            return None
        user_id, expires_at = row
        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
            return None
        db.commit()
        return user_id
    finally:
        db.close()

