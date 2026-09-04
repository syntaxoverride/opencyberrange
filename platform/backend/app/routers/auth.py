"""
Authentication routes for login and registration
"""

from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import logging
import re

from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import jwt as _jose_jwt, JWTError as _JWTError

from app.database import get_db
from app.models import User, WireGuardConfig, Lab, CourseLabAssignment, CourseEnrollment, Course, InviteCode, Assignment, AssignmentLab
from app.auth import (
    authenticate_user,
    get_password_hash,
    create_access_token,
    get_user_by_username,
    get_current_active_user,
    get_current_instructor_user,
    verify_password,
    validate_privileged_password,
    is_impersonating,
    create_impersonation_token,
    revoke_token,
    _decode_token,
    oauth2_scheme,
)
from app.services import totp as totp_service
from app.config import settings
from app.schemas import ChangePasswordRequest, ImpersonateRequest, ImpersonateResponse, _validate_password
from app.services.wireguard_manager import WireGuardManager
from app.services.activity import log_activity, EventTypes
from app.services.settings_service import get_setting_fresh

wireguard_manager = WireGuardManager()

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter for auth endpoints - stricter limits for security
limiter = Limiter(key_func=get_remote_address)


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    student_id: Optional[str] = None
    is_admin: bool
    is_approved: bool
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    """Registration request with input validation for security"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    student_id: Optional[str] = Field(None, min_length=5, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    invite_code: Optional[str] = Field(None, min_length=4, max_length=64)

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: str) -> str:
        """Username must start with letter and contain only alphanumeric, underscore, hyphen"""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Username must start with a letter and contain only letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        """Basic email format validation"""
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', v):
            raise ValueError('Invalid email format')
        return v.lower()  # Normalize to lowercase
    
    @field_validator('student_id')
    @classmethod
    def student_id_valid(cls, v: Optional[str]) -> Optional[str]:
        """Student ID must contain only alphanumeric characters (if provided)"""
        if v is None:
            return None
        if not re.match(r'^[A-Za-z0-9]+$', v):
            raise ValueError('Student ID must contain only letters and numbers')
        return v.upper()  # Normalize to uppercase
    
    @field_validator('password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        return _validate_password(v)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # 10 login attempts per minute per IP
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    totp_code: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Login endpoint - rate limited to 10 attempts per minute"""
    # Authenticate first — returns None for non-existent users, wrong
    # passwords, AND locked accounts.  We intentionally return the same
    # generic error for all cases to prevent username enumeration.
    from app.auth import LOCKOUT_DURATION_MINUTES

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Check if the account is locked so we can log it, but NEVER
        # reveal this distinction to the caller.
        existing_user = get_user_by_username(db, form_data.username)
        if existing_user and existing_user.is_locked:
            if existing_user.locked_at:
                locked_at = existing_user.locked_at
                if locked_at.tzinfo is None:
                    locked_at = locked_at.replace(tzinfo=timezone.utc)
                lockout_expires = locked_at + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                now = datetime.now(timezone.utc)
                if now >= lockout_expires:
                    # Lockout expired — tell user to try again (same generic message)
                    pass
                else:
                    logger.info(f"Login attempt for locked account: {form_data.username}")
            else:
                # Admin-locked account
                logger.info(f"Login attempt for admin-locked account: {form_data.username}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is approved
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account not approved. Please wait for admin approval."
        )
    
    # Check if user is locked (shouldn't happen after authenticate_user, but double-check)
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is locked. Contact an administrator."
        )
    
    # Check if is_active exists and is False
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Second factor. Only enforced after the password checks out, so the
    # X-MFA-Required hint never leaks whether an account exists.
    if getattr(user, "mfa_enabled", False):
        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required",
                headers={"WWW-Authenticate": "Bearer", "X-MFA-Required": "true"},
            )
        if not totp_service.verify_code(user.totp_secret, totp_code):
            logger.info(f"Failed MFA attempt for user: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code",
                headers={"WWW-Authenticate": "Bearer", "X-MFA-Required": "true"},
            )

    # Create access token
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Return token and user info
    user_dict = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "student_id": user.student_id,
        "role": getattr(user, 'role', 'admin' if user.is_admin else 'student'),
        "is_admin": user.role == 'admin' if hasattr(user, 'role') else user.is_admin,
        "is_approved": user.is_approved,
        "must_change_password": getattr(user, 'must_change_password', False),
    }
    
    # Add is_active if it exists
    if hasattr(user, 'is_active'):
        user_dict["is_active"] = user.is_active
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_dict
    }


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")  # 5 registrations per minute per IP
async def register(
    request: Request,
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user - rate limited to 5 per minute"""
    # Check for existing username, email, or student_id.
    # Use a single generic error to prevent account enumeration.
    existing = get_user_by_username(db, user_data.username)
    if not existing:
        existing = db.query(User).filter(User.email == user_data.email).first()
    if not existing and user_data.student_id:
        existing = db.query(User).filter(User.student_id == user_data.student_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with these credentials already exists"
        )
    
    # Invite gate: registration needs a valid, unused InviteCode. The gate is
    # OFF by default; a deployment turns it on with the runtime
    # "require_invite_code" setting when it wants registration limited to
    # issued codes. Errors stay generic so codes cannot be probed for their
    # state (nonexistent vs used vs expired vs wrong email).
    #
    # The default used to be ON, which blocked every fresh install. A new
    # install has no codes issued, and the sign-up form does not show a code
    # field until the server asks for one, so nobody could register at all.
    # The approval gate below is the control that was actually wanted.
    #
    # Read fresh rather than cached: a gate that controls access must not go
    # on enforcing for up to the cache TTL on whichever workers missed the
    # write (see settings_service.get_setting_fresh).
    invite = None
    require_invite = get_setting_fresh(db, "require_invite_code", "false") == "true"
    supplied_code = (user_data.invite_code or "").strip()
    if require_invite:
        if not supplied_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invite code is required to register"
            )
        # Row lock so two concurrent registrations cannot both consume
        # the same single-use code.
        invite = db.query(InviteCode).filter(
            InviteCode.code == supplied_code
        ).with_for_update().first()
        invite_valid = (
            invite is not None
            and invite.used_by is None
            and invite.used_at is None
        )
        if invite_valid:
            expires = invite.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                invite_valid = False
        if invite_valid and invite.email:
            # Email-pinned codes only register their own address
            if invite.email.lower() != user_data.email:
                invite_valid = False
        if not invite_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite code"
            )

    # Approval gate honors the runtime "require_approval" setting: when an admin
    # turns approval off, registrations are auto-approved and can log in at once.
    require_approval = get_setting_fresh(db, "require_approval", "true") != "false"

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        student_id=user_data.student_id,
        hashed_password=hashed_password,
        is_admin=False,
        is_approved=not require_approval,
        is_active=True if hasattr(User, 'is_active') else None,
        is_locked=False,
        failed_attempts=0
    )
    
    db.add(new_user)
    db.flush()  # assign new_user.id without ending the transaction

    # Burn the invite code in the same transaction as the user insert, so
    # the with_for_update() row lock holds until both changes land together.
    if invite is not None:
        invite.used_by = new_user.id
        invite.used_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.username} (ID: {new_user.id})")

    log_activity(db, EventTypes.USER_REGISTERED,
                  actor_id=new_user.id, target_type="user",
                  target_id=new_user.id, target_label=new_user.username)

    return new_user


@router.get("/me")
async def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information - syncs VPN registration status with Peer Manager.
    When impersonating, returns the effective (impersonated) identity with metadata."""
    imp = is_impersonating(current_user)
    imp_mode = getattr(current_user, '_imp_mode', None)

    # For synthetic impersonation modes, override the returned identity
    if imp and imp_mode in ('role_course', 'role_global'):
        imp_course_id = getattr(current_user, '_imp_course_id', None)
        course_name = None
        if imp_course_id:
            course = db.query(Course).filter(Course.id == imp_course_id).first()
            course_name = course.name if course else None

        return {
            "id": current_user.id,
            "username": f"_preview_{current_user.username}",
            "email": current_user.email,
            "student_id": None,
            "is_active": True,
            "is_approved": True,
            "is_admin": False,
            "role": "student" if imp_mode == 'role_course' else getattr(current_user, '_imp_mode', 'student'),
            "must_change_password": False,
            "impersonating": True,
            "impersonation": {
                "original_user": {
                    "id": current_user._imp_original_id,
                    "username": current_user._imp_original_username,
                },
                "mode": imp_mode,
                "course_id": imp_course_id,
                "course_name": course_name,
                "read_only": True,
            },
        }

    # Sync VPN registration status with Peer Manager (same logic as /labs/vpn-status)
    if not imp:
        wg_config = db.query(WireGuardConfig).filter(
            WireGuardConfig.user_id == current_user.id
        ).first()

        if wg_config and wg_config.public_key:
            try:
                actually_registered = wireguard_manager.peer_exists(wg_config.public_key)

                # Sync database flag if it's out of sync
                if actually_registered != current_user.vpn_registered:
                    current_user.vpn_registered = actually_registered
                    db.commit()
                    logger.info(f"Synced VPN registration status for user {current_user.username}: {actually_registered}")
            except Exception as e:
                logger.warning(f"Could not verify peer status with Peer Manager: {e}")

    # Build response
    resp = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "student_id": current_user.student_id,
        "is_active": getattr(current_user, 'is_active', True),
        "is_approved": current_user.is_approved,
        "is_admin": current_user.role == 'admin',
        "role": current_user.role,
        "must_change_password": getattr(current_user, 'must_change_password', False),
    }

    if imp:
        resp["impersonating"] = True
        resp["impersonation"] = {
            "original_user": {
                "id": current_user._imp_original_id,
                "username": current_user._imp_original_username,
            },
            "mode": imp_mode,
            "course_id": getattr(current_user, '_imp_course_id', None),
            "read_only": True,
        }

    return resp


def _require_workbook_released(db, current_user, original_uri: str) -> None:
    """Hold a course workbook page until its assignment opens.

    Enrollment alone used to open every chapter, so a student could read the
    Week 15 walkthrough during Week 1 while the Week 15 exercise stayed locked.
    The exercise list and the workbook are two views of the same schedule and
    should release together.

    The page is mapped to its assignment through data rather than by parsing
    week numbers out of directory names: the requested path is matched against
    ``Lab.workbook`` prefixes, and those labs are followed through
    ``assignment_labs`` to their assignments.

    Deliberately permissive when there is nothing to enforce. A path that
    matches no lab (a chapter index, the wiki root, a shared asset) is allowed,
    and so is a lab that no assignment schedules. A page reachable from several
    assignments opens with the earliest of them, so shared pages are never
    stranded behind the latest week that happens to cite them.
    """
    wiki_path = _normalize_wiki_path(original_uri)
    if not wiki_path:
        return

    labs = db.query(Lab).filter(
        Lab.workbook.isnot(None), Lab.workbook != ""
    ).all()
    lab_ids = []
    for lab in labs:
        # Older rows store a bare chapter path with no leading "wiki/" segment.
        # _normalize_wiki_path returns "" for those, and "".startswith() is
        # True for every request, so an unguarded comparison matched every lab
        # in the catalogue and pulled in unrelated courses' assignments. An
        # empty prefix is not a match.
        prefix = _normalize_wiki_path("/" + lab.workbook.lstrip("/"))
        if not prefix:
            prefix = _normalize_wiki_path("/wiki/" + lab.workbook.lstrip("/"))
        if not prefix:
            continue
        if wiki_path.startswith(prefix):
            lab_ids.append(lab.id)
            continue
        # Also hold the rest of the chapter the lab lives in. Workbook paths
        # point at a single page, so a chapter's introduction and its index
        # match no lab at all and would stay readable while every graded page
        # in the same week is held back.
        chapter = prefix.rstrip("/").rsplit("/", 1)[0] + "/"
        if chapter.count("/") >= 3 and wiki_path.startswith(chapter):
            lab_ids.append(lab.id)
    if not lab_ids:
        return

    rows = db.query(Assignment).join(
        AssignmentLab, AssignmentLab.assignment_id == Assignment.id
    ).filter(AssignmentLab.lab_id.in_(lab_ids)).all()
    if not rows:
        return

    now = datetime.now(timezone.utc)
    for asn in rows:
        if asn.locked:
            continue
        start = asn.start_date
        if start is None:
            return                      # unscheduled assignment: nothing to hold
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start <= now:
            return                      # at least one assignment has opened
    raise HTTPException(
        status_code=403,
        detail="This workbook opens when its assignment does.",
    )


def _normalize_wiki_path(original_uri: str) -> str:
    """Reduce an X-Original-URI to the space that ``Lab.workbook`` is stored in.

    Workbook paths are recorded inconsistently across the lab catalogue: most
    rows carry a leading ``wiki/`` segment (``wiki/range/<track>/CH_.../00_X/``)
    while older rows store the bare chapter path (``CH_COURSE01_.../01_Y/``).
    Requests arrive as ``/wiki/<rest>`` or ``/wiki-<id>/<rest>``.  Both sides
    get reduced to ``<rest>`` here so a prefix comparison is meaningful.

    Returning "" means the URI is not a wiki path at all.
    """
    path = original_uri.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/wiki"):
        return ""
    path = path.lstrip("/")
    # Drop the routing prefix: "wiki/", "wiki-oscp/", "wiki-1234/", ...
    first, sep, rest = path.partition("/")
    if not sep or not (first == "wiki" or first.startswith("wiki-")):
        return ""
    # Some rows keep a redundant leading "wiki/" of their own.
    if rest.startswith("wiki/"):
        rest = rest[len("wiki/"):]
    return rest


def _normalize_workbook(workbook: str) -> str:
    """Reduce a stored ``Lab.workbook`` value to the same space as above."""
    wb = (workbook or "").strip().lstrip("/")
    if wb.startswith("wiki/"):
        wb = wb[len("wiki/"):]
    return wb


@router.get("/wiki-released")
async def wiki_released_chapters(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Chapter directories of a course wiki this user may open right now.

    Feeds the workbook's own navigation so a learner is not shown links that
    the release gate will refuse. Purely cosmetic: /wiki-access is still the
    enforcement point, and hiding a link protects nothing on its own.

    Returns every chapter when the caller is staff or the course has no
    schedule, which matches the gate's permissive default.

    Authenticates from the ``wiki_auth`` cookie as well as a bearer header.
    The caller is a script running inside a workbook page, which carries the
    wiki cookie and no Authorization header; nginx only rewrites that cookie
    into a bearer for its internal auth_request locations, not for /api. Taking
    the header alone made this 401 for every learner, and since the script fails
    open the navigation then listed every chapter as though nothing was gated.
    """
    token = ""
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("wiki_auth", "")
    if not token:
        # Unauthenticated: reveal nothing, and let the caller leave the nav be.
        return {"all": True, "chapters": []}
    try:
        payload = _decode_token(token)
        current_user = get_user_by_username(db, payload.get("sub"))
    except HTTPException:
        return {"all": True, "chapters": []}
    if not current_user or not getattr(current_user, "is_active", True):
        return {"all": True, "chapters": []}

    course = db.query(Course).filter(Course.wiki_slug == slug).first()
    if not course:
        return {"all": True, "chapters": []}

    staff = current_user.role == "admin" or course.instructor_id == current_user.id
    if staff:
        return {"all": True, "chapters": []}

    prefix = f"course/{slug}/"
    labs = db.query(Lab).filter(Lab.workbook.isnot(None), Lab.workbook != "").all()
    released, seen_any = set(), False
    now = datetime.now(timezone.utc)
    for lab in labs:
        p = _normalize_wiki_path("/" + lab.workbook.lstrip("/")) or \
            _normalize_wiki_path("/wiki/" + lab.workbook.lstrip("/"))
        if not p or not p.startswith(prefix):
            continue
        chapter = p[len(prefix):].split("/", 1)[0]
        if not chapter:
            continue
        rows = db.query(Assignment).join(
            AssignmentLab, AssignmentLab.assignment_id == Assignment.id
        ).filter(AssignmentLab.lab_id == lab.id).all()
        if not rows:
            released.add(chapter)
            continue
        seen_any = True
        for asn in rows:
            if asn.locked:
                continue
            start = asn.start_date
            if start is None:
                released.add(chapter); break
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if start <= now:
                released.add(chapter); break
    if not seen_any:
        return {"all": True, "chapters": []}
    return {"all": False, "chapters": sorted(released)}


@router.get("/wiki-access")
async def check_wiki_access(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user)
):
    """Validate wiki access for a specific path.

    Nginx sends the original URI via X-Original-URI header.  Course-specific
    chapters (``/wiki/course/<slug>/...``, or any path that resolves to a lab
    with visibility='course') require the user to be enrolled in, or to be
    instructing, a course that assigns that lab.  Any other wiki path is open
    to every authenticated user.

    Returns 200 if allowed, raises 403 if denied.
    """
    original_uri = request.headers.get("X-Original-URI", "")

    # Admins always pass
    if current_user.role == "admin":
        return {"status": "ok"}

    # ── Per-course wiki paths: /wiki/course/<slug>/... ──
    # Check enrollment in the specific course identified by its wiki_slug.
    if original_uri.startswith("/wiki/course/"):
        parts = original_uri.split("/", 5)  # ['', 'wiki', 'course', '<slug>', ...]
        if len(parts) >= 4:
            course_slug = parts[3]
            course = db.query(Course).filter(Course.wiki_slug == course_slug).first()
            if course:
                # Instructors of this course always pass
                if course.instructor_id == current_user.id:
                    return {"status": "ok"}
                # Check enrollment + course active
                enrollment = db.query(CourseEnrollment).filter(
                    CourseEnrollment.course_id == course.id,
                    CourseEnrollment.user_id == current_user.id,
                ).first()
                if not enrollment:
                    raise HTTPException(status_code=403, detail="Course enrollment required")
                now = datetime.now(timezone.utc)
                course_end = course.end_date
                if course_end.tzinfo is None:
                    course_end = course_end.replace(tzinfo=timezone.utc)
                if not course.is_active or course_end < now:
                    raise HTTPException(status_code=403, detail="Course is not active")
                _require_workbook_released(db, current_user, original_uri)
                return {"status": "ok"}
        # Course not found or malformed path — deny
        raise HTTPException(status_code=403, detail="Course not found")

    # ── Track and legacy wiki paths: /wiki/range/<track>/..., /wiki-NNNN/... ──
    # Both the request URI and the stored workbook get normalized into the
    # same space first, so a leading-slash difference cannot make a lookup
    # come up empty and fall through to the permissive return below.
    wiki_path = _normalize_wiki_path(original_uri)

    # Check if this path belongs to a course-visibility lab
    if wiki_path:
        # Find labs whose workbook path is a prefix of the requested path
        course_labs = db.query(Lab).filter(
            Lab.workbook.isnot(None),
            Lab.visibility == "course",
        ).all()

        # Multiple labs may share the same workbook path (e.g. a pen-test
        # lab reused across courses).  Grant access if the user is enrolled
        # in ANY course that assigns a matching lab.
        matching_labs = [
            lab for lab in course_labs
            if _normalize_workbook(lab.workbook)
            and wiki_path.startswith(_normalize_workbook(lab.workbook))
        ]
        if matching_labs:
            now = datetime.now(timezone.utc)
            matching_ids = [lab.id for lab in matching_labs]
            has_access = db.query(CourseLabAssignment.id).join(
                Course, Course.id == CourseLabAssignment.course_id
            ).outerjoin(
                CourseEnrollment,
                (CourseEnrollment.course_id == Course.id) &
                (CourseEnrollment.user_id == current_user.id)
            ).filter(
                CourseLabAssignment.lab_id.in_(matching_ids),
                (
                    (CourseEnrollment.id.isnot(None) & (Course.end_date >= now) & (Course.is_active == True)) |
                    (Course.instructor_id == current_user.id)
                )
            ).first()

            if not has_access:
                raise HTTPException(status_code=403, detail="Course enrollment required")

    return {"status": "ok"}




@router.get("/wiki-admin-access")
async def check_wiki_admin_access(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Validate admin-only wiki access.

    Used by nginx auth_request for /wiki-admin/ paths.
    Returns 200 if the user is an admin, raises 403 otherwise.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"status": "ok"}


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Change user password - rate limited to 5 per minute"""
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password matches confirm password
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match"
        )
    
    # Validate new password meets requirements (using RegisterRequest validator logic)
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    if not re.search(r'[A-Z]', password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    if not re.search(r'[a-z]', password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    if not re.search(r'[0-9]', password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )

    # Stricter policy for privileged accounts
    if current_user.role in ('instructor', 'admin'):
        policy_error = validate_privileged_password(password_data.new_password)
        if policy_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=policy_error
            )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    
    # Clear must_change_password flag if set
    if hasattr(current_user, 'must_change_password') and current_user.must_change_password:
        current_user.must_change_password = False
    
    db.commit()
    
    logger.info(f"User {current_user.username} changed their password")

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Revoke the presented token so it stops working on every worker.

    Revocation is DB-backed (revoked_tokens table), so a logged-out token is
    dead platform-wide, not just on the worker that handled this request."""
    payload = _decode_token(token)
    jti = payload.get("jti")
    if jti:
        revoke_token(jti, float(payload.get("exp", 0)), user_id=current_user.id)
    return {"message": "Logged out"}


# ==================== MFA (TOTP) ====================

class MfaCodeRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MfaDisableRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=6, max_length=8)


@router.post("/mfa/enroll")
@limiter.limit("5/minute")
async def enroll_mfa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Start TOTP enrollment: generate a secret and return the otpauth URI.

    The secret is stored Fernet-encrypted; mfa_enabled stays False until the
    user proves possession via /mfa/verify. Re-calling before verification
    rotates the pending secret."""
    if getattr(current_user, "mfa_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled. Disable it first to re-enroll."
        )

    secret = totp_service.generate_secret()
    current_user.totp_secret = totp_service.encrypt_totp_secret(secret)
    db.commit()

    logger.info(f"User {current_user.username} started MFA enrollment")

    return {
        "secret": secret,
        "provisioning_uri": totp_service.provisioning_uri(
            secret, current_user.email or current_user.username
        ),
        "issuer": totp_service.ISSUER_NAME,
    }


@router.post("/mfa/verify")
@limiter.limit("10/minute")
async def verify_mfa(
    request: Request,
    body: MfaCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Confirm TOTP enrollment with a code from the authenticator app.

    First valid code flips mfa_enabled on; later calls just report state."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No MFA enrollment in progress. Call /mfa/enroll first."
        )

    if not totp_service.verify_code(current_user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )

    if not current_user.mfa_enabled:
        current_user.mfa_enabled = True
        db.commit()
        logger.info(f"User {current_user.username} enabled MFA")

    return {"mfa_enabled": True}


@router.post("/mfa/disable")
@limiter.limit("5/minute")
async def disable_mfa(
    request: Request,
    body: MfaDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Turn MFA off. Requires the account password AND a current TOTP code,
    so a hijacked session alone cannot strip the second factor."""
    if not getattr(current_user, "mfa_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )

    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password is incorrect"
        )

    if not totp_service.verify_code(current_user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )

    current_user.mfa_enabled = False
    current_user.totp_secret = None
    db.commit()

    logger.info(f"User {current_user.username} disabled MFA")

    return {"mfa_enabled": False}


# ==================== Impersonation ====================

@router.post("/impersonate", response_model=ImpersonateResponse)
async def start_impersonation(
    body: ImpersonateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Start an impersonation session.

    Modes:
      1. target_user_id set          → impersonate a specific user (admin only)
      2. target_role + course_id set  → synthetic student in a course (admin or instructor-of-course)
      3. target_role only             → generic role view (admin only)
    """
    # Block if already impersonating (no nesting)
    if is_impersonating(current_user):
        raise HTTPException(status_code=403, detail="Cannot impersonate while already impersonating")

    # Must be at least instructor
    if current_user.role not in ('admin', 'instructor'):
        raise HTTPException(status_code=403, detail="Impersonation requires admin or instructor role")

    mode = None
    target_user = None
    target_username = None
    target_role = None
    course_id = body.course_id

    # ── Mode 1: Impersonate specific user ──
    if body.target_user_id is not None:
        if current_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Only admins can impersonate specific users")

        target_user = db.query(User).filter(User.id == body.target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        if target_user.role == 'admin':
            raise HTTPException(status_code=403, detail="Cannot impersonate admin users")

        mode = "user"
        target_username = target_user.username
        target_role = target_user.role

    # ── Mode 2/3: Synthetic role ──
    elif body.target_role is not None:
        target_role = body.target_role

        if course_id is not None:
            # Mode 2: role + course
            mode = "role_course"
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Instructors can only preview their own courses
            if current_user.role == 'instructor' and course.instructor_id != current_user.id:
                raise HTTPException(status_code=403, detail="You can only preview your own courses")

            # Instructors can only impersonate as student
            if current_user.role == 'instructor' and target_role != 'student':
                raise HTTPException(status_code=403, detail="Instructors can only view as student")

            target_username = f"_preview_{current_user.username}"
        else:
            # Mode 3: global role (admin only)
            if current_user.role != 'admin':
                raise HTTPException(status_code=403, detail="Only admins can impersonate a global role")
            mode = "role_global"
            target_username = f"_preview_{current_user.username}"
    else:
        raise HTTPException(status_code=400, detail="Must specify target_user_id or target_role")

    # For synthetic modes, we need a real user to back the token.
    # We'll use the original user's record but override the role in the JWT.
    # The frontend and /me endpoint will read imp claims to adjust behavior.
    if mode in ("role_course", "role_global"):
        # Use the current user's username as the sub so get_current_user resolves.
        # The imp claims carry the effective role.
        target_username = current_user.username

    # Create impersonation token
    token = create_impersonation_token(
        original_user=current_user,
        target_username=target_username,
        target_role=target_role,
        mode=mode,
        course_id=course_id,
    )

    # Build response user dicts
    if target_user:
        imp_user = {
            "id": target_user.id,
            "username": target_user.username,
            "email": target_user.email,
            "role": target_user.role,
            "student_id": target_user.student_id,
        }
    else:
        imp_user = {
            "id": current_user.id,
            "username": f"_preview_{current_user.username}",
            "email": current_user.email,
            "role": target_role,
            "student_id": None,
        }

    original = {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    }

    # Audit log
    log_activity(
        db, EventTypes.IMPERSONATION_START,
        actor_id=current_user.id,
        target_type="user" if target_user else "role",
        target_id=target_user.id if target_user else None,
        target_label=imp_user["username"],
        detail={
            "mode": mode,
            "target_role": target_role,
            "course_id": course_id,
        },
        ip_address=request.client.host if request.client else None,
    )

    logger.info(
        "Impersonation started: %s -> %s (mode=%s, course=%s)",
        current_user.username, imp_user["username"], mode, course_id,
    )

    return ImpersonateResponse(
        token=token,
        impersonated_user=imp_user,
        original_user=original,
        mode=mode,
        expires_in=3600,
    )


@router.post("/impersonate/exit")
async def exit_impersonation(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Exit impersonation and return a fresh token for the original user."""
    payload = _decode_token(token)

    if not payload.get("imp"):
        raise HTTPException(status_code=400, detail="Not currently impersonating")

    original_id = payload.get("imp_original_id")
    if not original_id:
        raise HTTPException(status_code=400, detail="Invalid impersonation token")

    original_user = db.query(User).filter(User.id == original_id).first()
    if not original_user:
        raise HTTPException(status_code=404, detail="Original user not found")

    # Verify the original user is still an admin/instructor
    if original_user.role not in ('admin', 'instructor'):
        raise HTTPException(status_code=403, detail="Original user no longer has impersonation privileges")

    # Create a fresh standard token for the original user
    fresh_token = create_access_token(
        data={"sub": original_user.username},
        expires_delta=timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    )

    # Audit log
    log_activity(
        db, EventTypes.IMPERSONATION_END,
        actor_id=original_user.id,
        target_type="user",
        target_id=original_user.id,
        target_label=original_user.username,
        detail={"imp_mode": payload.get("imp_mode")},
        ip_address=request.client.host if request.client else None,
    )

    logger.info("Impersonation ended: %s resumed", original_user.username)

    user_dict = {
        "id": original_user.id,
        "username": original_user.username,
        "email": original_user.email,
        "student_id": original_user.student_id,
        "role": original_user.role,
        "is_admin": original_user.role == 'admin',
        "is_approved": original_user.is_approved,
        "must_change_password": getattr(original_user, 'must_change_password', False),
    }

    return {
        "access_token": fresh_token,
        "token_type": "bearer",
        "user": user_dict,
    }


@router.get("/me/impersonation")
async def get_impersonation_status(
    current_user: User = Depends(get_current_active_user),
):
    """Return impersonation metadata for the current session."""
    if not is_impersonating(current_user):
        return {"impersonating": False}

    return {
        "impersonating": True,
        "original_user": {
            "id": current_user._imp_original_id,
            "username": current_user._imp_original_username,
        },
        "mode": current_user._imp_mode,
        "course_id": current_user._imp_course_id,
        "read_only": current_user._imp_read_only,
    }

