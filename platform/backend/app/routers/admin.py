"""
Admin routes for user, lab, and session management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone, timedelta
import os
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import (
    User, Lab, LabSession, WireGuardConfig, LabCompletion, FlagAttempt, Level, Track, Course,
    CourseEnrollment, Achievement, CourseCompletionReset, ActivityEvent,
)
from app.schemas import (
    UserAdminResponse,
    LabResponse,
    UserDetailResponse,
    LabCompletionDetail,
    LabSessionResponse,
    CreateUserRequest,
    UpdateUserRequest,
    ResetPasswordRequest,
    UpdateLabRequest,
    LabCreate,
)
from app.auth import get_current_admin_user, get_current_instructor_user, get_password_hash, validate_privileged_password
from app import entitlement
from app.services import settings_service
from app.services.docker_manager import DockerManager, get_subnet_id, RangeBoxCapacityError
from app.services.wireguard_manager import WireGuardManager
from app.services.audit import log_admin_action, AuditActions
from app.services.activity import log_activity, EventTypes
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter for admin endpoints
limiter = Limiter(key_func=get_remote_address)

docker_manager = DockerManager()
wireguard_manager = WireGuardManager(
    api_url=settings.WG_API_URL,
    api_key=settings.WG_API_KEY
)


# ==================== User Management ====================

@router.get("/users", response_model=List[UserAdminResponse])
async def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all users — bulk-syncs vpn_registered flags from Peer Manager"""
    # Sync vpn_registered flags against the live Peer Manager peer list.
    # Only update when the API responds (peers is not None) so we don't
    # accidentally reset everyone to False on a transient API failure.
    peers = wireguard_manager.list_peers()
    if peers is not None:
        peer_keys = {p.get("public_key", "").strip() for p in peers}
        wg_configs = db.query(WireGuardConfig).options(joinedload(WireGuardConfig.user)).all()
        dirty = False
        for cfg in wg_configs:
            is_registered = cfg.public_key.strip() in peer_keys
            if cfg.user and cfg.user.vpn_registered != is_registered:
                cfg.user.vpn_registered = is_registered
                dirty = True
        if dirty:
            db.commit()

    users = db.query(User).all()
    return users


@router.get("/users/pending", response_model=List[UserAdminResponse])
async def list_pending_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List users awaiting approval"""
    users = db.query(User).filter(User.is_approved == False, User.is_active == True).all()
    return users


@router.get("/users/locked", response_model=List[UserAdminResponse])
async def list_locked_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List locked user accounts"""
    users = db.query(User).filter(User.is_locked == True).all()
    return users


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/details", response_model=UserDetailResponse)
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get detailed user information with completions and statistics"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get completions with lab information - only for enabled labs
    completions_query = db.query(LabCompletion, Lab).join(Lab).filter(
        LabCompletion.user_id == user_id,
        Lab.is_active == True
    ).order_by(LabCompletion.completed_at.desc())
    
    completions_data = []
    total_hints = 0
    total_attempts = 0
    total_time = 0
    labs_with_time = 0
    
    for completion, lab in completions_query.all():
        # Get track and level info
        track_name = None
        level_number = None
        if lab.level:
            level_number = lab.level.level_number
            if lab.level.track:
                track_name = lab.level.track.name
        
        completions_data.append(LabCompletionDetail(
            lab_id=lab.id,
            lab_name=lab.name,
            lab_slug=lab.slug,
            track_name=track_name,
            level_number=level_number,
            completed_at=completion.completed_at,
            attempts=completion.attempts,
            hints_used=completion.hints_used,
            time_spent_minutes=completion.time_spent_minutes
        ))
        
        total_hints += completion.hints_used
        total_attempts += completion.attempts
        if completion.time_spent_minutes:
            total_time += completion.time_spent_minutes
            labs_with_time += 1
    
    # Get flag attempts count
    flag_attempts_count = db.query(func.count(FlagAttempt.id)).filter(
        FlagAttempt.user_id == user_id
    ).scalar() or 0
    
    # Calculate average time per lab
    average_time = None
    if labs_with_time > 0:
        average_time = round(total_time / labs_with_time, 1)
    
    # Get active sessions
    active_sessions = db.query(LabSession).filter(
        LabSession.user_id == user_id,
        LabSession.status == "running"
    ).all()
    
    sessions_data = []
    for session in active_sessions:
        lab = db.query(Lab).filter(Lab.id == session.lab_id).first()
        if lab:
            targets = docker_manager.get_lab_targets(user_id, lab.slug)
            sessions_data.append(LabSessionResponse(
                id=session.id,
                lab_id=session.lab_id,
                lab_name=lab.name,
                lab_slug=lab.slug,
                network_subnet=session.network_subnet,
                status=session.status,
                started_at=session.started_at,
                expires_at=session.expires_at,
                targets=[{"name": t["name"], "ip": t["ip"], "ports": t.get("ports", [])} for t in targets]
            ))
    
    # Build response
    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        student_id=user.student_id,
        is_active=user.is_active,
        is_approved=user.is_approved,
        is_admin=user.is_admin,
        is_locked=user.is_locked,
        failed_attempts=user.failed_attempts,
        locked_at=user.locked_at,
        vpn_registered=user.vpn_registered,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        total_labs_completed=len(completions_data),
        total_flag_attempts=flag_attempts_count,
        total_hints_used=total_hints,
        average_time_per_lab=average_time,
        completions=completions_data,
        active_sessions=sessions_data
    )


@router.post("/users/{user_id}/labs/{lab_id}/reset")
@limiter.limit("10/minute")
async def reset_user_lab(
    request: Request,
    user_id: int,
    lab_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Reset a lab for a user, allowing them to replay it"""
    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate lab exists
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    # Check if completion exists
    completion = db.query(LabCompletion).filter(
        LabCompletion.user_id == user_id,
        LabCompletion.lab_id == lab_id
    ).first()
    
    if not completion:
        return {
            "message": f"Lab '{lab.name}' has not been completed by user '{user.username}'. Nothing to reset.",
            "reset": False
        }
    
    try:
        # Check for active session and stop it if exists
        active_session = db.query(LabSession).filter(
            LabSession.user_id == user_id,
            LabSession.lab_id == lab_id,
            LabSession.status == "running"
        ).first()
        
        if active_session:
            try:
                docker_manager.destroy_lab_environment(
                    user_id=user_id,
                    lab_slug=lab.slug
                )
                active_session.status = "stopped"
                db.commit()
                logger.info(f"Stopped active session for lab {lab.slug} (user {user_id}) during reset")
            except Exception as e:
                logger.warning(f"Failed to stop Docker environment during lab reset: {e}")
                # Continue with reset even if Docker cleanup fails
                active_session.status = "stopped"
                db.commit()
        
        # Delete all flag attempts (includes hint requests)
        db.query(FlagAttempt).filter(
            FlagAttempt.user_id == user_id,
            FlagAttempt.lab_id == lab_id
        ).delete()
        
        # Delete completion record
        db.delete(completion)
        db.commit()
        
        # Audit log
        log_admin_action(
            action=AuditActions.LAB_RESET,
            admin_user_id=admin.id,
            admin_username=admin.username,
            target_type="lab",
            target_id=lab_id,
            target_identifier=f"{lab.slug} (user: {user.username})",
            details={
                "user_id": user_id,
                "user_username": user.username,
                "lab_id": lab_id,
                "lab_name": lab.name,
                "lab_slug": lab.slug
            },
            ip_address=request.client.host if request.client else None
        )
        
        return {
            "message": f"Lab '{lab.name}' has been reset for user '{user.username}'. They can now replay this lab.",
            "reset": True
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting lab {lab_id} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset lab: {str(e)}"
        )


def _enforce_privileged_cap(db: Session):
    """Entitlement cap on instructor/admin accounts (None = unlimited)."""
    limit = entitlement.privileged_account_limit()
    if limit is None:
        return
    count = db.query(User).filter(User.role.in_(("instructor", "admin"))).count()
    if count >= limit:
        edition = f"OCR-{entitlement.edition_name().capitalize()}"
        raise HTTPException(
            status_code=403,
            detail=(
                f"{edition} includes {limit} privileged account(s) (admin or "
                f"instructor) and this install has {count}. Upgrade for "
                f"unlimited instructor accounts (see LICENSING.md)."
            ),
        )


@router.post("/users/create", response_model=UserAdminResponse)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new user - rate limited to 5 per minute"""
    # Check for existing username or email
    existing = db.query(User).filter(
        (User.username == user_data.username) |
        (User.email == user_data.email)
    ).first()
    
    if existing:
        if existing.username == user_data.username:
            raise HTTPException(status_code=400, detail="Username already exists")
        if existing.email == user_data.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Check student_id separately only if provided (allow multiple NULL values)
    if user_data.student_id:
        existing_student = db.query(User).filter(User.student_id == user_data.student_id).first()
        if existing_student:
            raise HTTPException(status_code=400, detail="Student ID already exists")
    
    # Determine role and is_admin with backward compatibility
    if getattr(user_data, 'role', None) is not None:
        role = user_data.role
        is_admin = (role == 'admin')
    elif user_data.is_admin:
        role = 'admin'
        is_admin = True
    else:
        role = 'student'
        is_admin = False

    # Stricter password policy for privileged accounts
    if role in ('instructor', 'admin'):
        policy_error = validate_privileged_password(user_data.password)
        if policy_error:
            raise HTTPException(status_code=400, detail=policy_error)
        _enforce_privileged_cap(db)

    user = User(
        username=user_data.username,
        email=user_data.email,
        student_id=user_data.student_id,
        hashed_password=get_password_hash(user_data.password),
        is_approved=user_data.is_approved,
        is_admin=is_admin,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Audit log
    log_admin_action(
        action=AuditActions.USER_CREATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="user",
        target_id=user.id,
        target_identifier=user.username,
        details={"email": user.email, "is_admin": user.is_admin, "role": user.role, "is_approved": user.is_approved},
        ip_address=request.client.host if request.client else None
    )
    
    return user


@router.put("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    user_request: UpdateUserRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update user details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Track changes for audit log
    changes = {}
    
    # Update username if provided
    if user_request.username is not None:
        # Check if new username already exists (excluding current user)
        existing_username = db.query(User).filter(
            User.username == user_request.username,
            User.id != user_id
        ).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already exists")
        changes['username'] = {'old': user.username, 'new': user_request.username}
        user.username = user_request.username
    
    # Update email if provided
    if user_request.email is not None:
        # Check if new email already exists (excluding current user)
        existing_email = db.query(User).filter(
            User.email == user_request.email,
            User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        changes['email'] = {'old': user.email, 'new': user_request.email}
        user.email = user_request.email
    
    # Update password if provided
    if user_request.password is not None:
        _eff_role = user_request.role or getattr(user, 'role', 'student')
        if _eff_role in ('instructor', 'admin') or getattr(user, 'role', 'student') in ('instructor', 'admin'):
            policy_error = validate_privileged_password(user_request.password)
            if policy_error:
                raise HTTPException(status_code=400, detail=policy_error)
        user.hashed_password = get_password_hash(user_request.password)
        changes['password'] = 'updated'
    
    # Update account flags
    if user_request.is_active is not None:
        changes['is_active'] = {'old': user.is_active, 'new': user_request.is_active}
        user.is_active = user_request.is_active
    if user_request.is_approved is not None:
        changes['is_approved'] = {'old': user.is_approved, 'new': user_request.is_approved}
        user.is_approved = user_request.is_approved
    # Entitlement cap: block promotion of a non-privileged account to a
    # privileged role once the cap is reached
    _requested_role = user_request.role
    if _requested_role is None and user_request.is_admin:
        _requested_role = 'admin'
    if (_requested_role in ('instructor', 'admin')
            and getattr(user, 'role', 'student') not in ('instructor', 'admin')):
        _enforce_privileged_cap(db)

    # Handle role and is_admin with backward compatibility
    if user_request.role is not None:
        # Explicit role update — sync is_admin to match
        old_role = getattr(user, 'role', 'student')
        changes['role'] = {'old': old_role, 'new': user_request.role}
        user.role = user_request.role
        new_is_admin = (user_request.role == 'admin')
        if user.is_admin != new_is_admin:
            changes['is_admin'] = {'old': user.is_admin, 'new': new_is_admin}
            user.is_admin = new_is_admin
    elif user_request.is_admin is not None:
        # Legacy is_admin update — derive role from it
        changes['is_admin'] = {'old': user.is_admin, 'new': user_request.is_admin}
        user.is_admin = user_request.is_admin
        if user_request.is_admin:
            derived_role = 'admin'
        else:
            # Demoting from admin: fall back to current role if it's not admin, else student
            current_role = getattr(user, 'role', 'student')
            derived_role = current_role if current_role != 'admin' else 'student'
        old_role = getattr(user, 'role', 'student')
        if old_role != derived_role:
            changes['role'] = {'old': old_role, 'new': derived_role}
            user.role = derived_role

    # Update must_change_password flag (only if column exists)
    if user_request.must_change_password is not None:
        try:
            old_value = getattr(user, 'must_change_password', False)
            changes['must_change_password'] = {'old': old_value, 'new': user_request.must_change_password}
            user.must_change_password = user_request.must_change_password
        except AttributeError:
            # Column doesn't exist yet - skip this update
            logger.warning(f"must_change_password column does not exist in database. Migration required.")
    
    db.commit()
    db.refresh(user)
    
    # Audit log
    log_admin_action(
        action=AuditActions.USER_UPDATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="user",
        target_id=user.id,
        target_identifier=user.username,
        details=changes,
        ip_address=http_request.client.host if http_request.client else None
    )
    
    return user


@router.post("/users/approve")
async def approve_user(
    user_id: int,
    approved: bool = True,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Approve or reject a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_approved = approved
    db.commit()

    if approved:
        log_activity(db, EventTypes.USER_APPROVED,
                      actor_id=admin.id, target_type="user",
                      target_id=user.id, target_label=user.username)

    return {"message": f"User {'approved' if approved else 'rejected'}"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Unlock a locked user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_locked = False
    user.failed_attempts = 0
    user.locked_at = None
    db.commit()
    
    return {"message": f"User {user.username} unlocked"}


@router.post("/users/{user_id}/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    user_id: int,
    password_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Reset a user's password - rate limited to 5 per minute"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Stricter password policy when the target account is privileged
    if user.role in ('instructor', 'admin'):
        policy_error = validate_privileged_password(password_data.new_password)
        if policy_error:
            raise HTTPException(status_code=400, detail=policy_error)

    user.hashed_password = get_password_hash(password_data.new_password)
    user.is_locked = False
    user.failed_attempts = 0
    user.locked_at = None
    db.commit()
    
    # Audit log
    log_admin_action(
        action=AuditActions.PASSWORD_RESET,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="user",
        target_id=user.id,
        target_identifier=user.username,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": f"Password reset for {user.username}"}


@router.post("/users/{user_id}/force-logout")
async def force_logout_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Revoke all active JWT tokens for a user, forcing them to re-authenticate."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.auth import revoke_all_user_tokens
    revoke_all_user_tokens(user.username)

    logger.info(f"Admin {admin.username} force-logged-out user {user.username}")
    return {"message": f"All sessions revoked for {user.username}"}


# Relations that reference users(id) through a foreign key that predates the
# ON DELETE rules now declared in models.py. On a database created before those
# rules, Postgres defaults to NO ACTION, so a user who has any of these rows
# cannot be deleted at all: the delete fails with a ForeignKeyViolation naming
# whichever table the planner happened to check first. Deletion therefore
# succeeded for users with no SOC or Studio history and failed for those with
# it, which reads like a random bug.
#
# Clearing these explicitly keeps deletion working regardless of whether a given
# deployment's constraints were migrated. "delete" removes rows that belong to
# the user; "null" keeps a row that has independent value and drops only the
# identity link.
_USER_REFERENCE_CLEANUP = (
    ("revoked_tokens",        "user_id",         "delete"),
    ("invite_codes",          "created_by",      "delete"),
    ("invite_codes",          "used_by",         "null"),
    ("lab_sessions",          "impersonated_by", "null"),
    ("template_instances",    "instructor_id",   "delete"),
    ("studio_pending_review", "instructor_id",   "delete"),
    ("exercise_gen_jobs",     "instructor_id",   "delete"),
    # Present on some instances only, skipped where the table does not exist.
    # soc_exercise_* are orphans on older databases: leftovers from the retired
    # tracks that earlier releases shipped. No model defines them any more,
    # their constraints still block user deletion, because a foreign key does not
    # care whether any code uses the table.
    # llmr_* belong to the LLM Range build and land here when that branch merges.
    ("llmr_seats",            "user_id",       "delete"),
    ("llmr_findings",         "user_id",       "delete"),
    ("llmr_defense_configs",  "submitted_by",  "null"),
)


def _clear_user_references(db: Session, user_id: int) -> None:
    """Clear rows referencing a user that would otherwise block deletion.

    Tables absent from this deployment are skipped, so an install without the
    SOC or Studio modules is unaffected. Table and column names come from the
    constant above, never from request input.
    """
    from sqlalchemy import text

    for table, column, action in _USER_REFERENCE_CLEANUP:
        try:
            if not db.execute(text("SELECT to_regclass(:t) IS NOT NULL"),
                              {"t": table}).scalar():
                continue
            stmt = (f"DELETE FROM {table} WHERE {column} = :uid"
                    if action == "delete"
                    else f"UPDATE {table} SET {column} = NULL WHERE {column} = :uid")
            db.execute(text(stmt), {"uid": user_id})
        except Exception as exc:
            logger.warning(f"User delete cleanup skipped {table}.{column}: {exc}")


@router.delete("/users/{user_id}")
@limiter.limit("5/minute")
async def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete a user (stops their active labs first) - rate limited to 5 per minute"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Allow admins to delete other admin users (removed restriction)
    
    # Stop any active labs
    active_session = db.query(LabSession).filter(
        LabSession.user_id == user_id,
        LabSession.status == "running"
    ).first()
    
    if active_session:
        try:
            docker_manager.destroy_lab_environment(user_id, active_session.lab.slug)
        except Exception:
            pass
    
    # Remove VPN peer from Peer Manager
    wg_config = db.query(WireGuardConfig).filter(WireGuardConfig.user_id == user_id).first()
    if wg_config:
        try:
            wireguard_manager.remove_peer(wg_config.public_key)
            logger.info(f"Removed VPN peer for deleted user {user.username}")
        except Exception as e:
            logger.error(f"Failed to remove VPN peer: {e}")
        db.delete(wg_config)
    
    # Delete all related records (handles cases where DB lacks CASCADE constraints)
    db.query(CourseCompletionReset).filter(CourseCompletionReset.user_id == user_id).delete()
    db.query(CourseCompletionReset).filter(CourseCompletionReset.reset_by == user_id).update({"reset_by": None})
    db.query(Achievement).filter(Achievement.user_id == user_id).delete()
    db.query(CourseEnrollment).filter(CourseEnrollment.user_id == user_id).delete()
    db.query(FlagAttempt).filter(FlagAttempt.user_id == user_id).delete()
    db.query(LabCompletion).filter(LabCompletion.user_id == user_id).delete()
    db.query(LabSession).filter(LabSession.user_id == user_id).delete()
    db.query(ActivityEvent).filter(ActivityEvent.actor_id == user_id).update({"actor_id": None})
    # Delete courses where user is instructor (no CASCADE on instructor_id FK)
    db.query(Course).filter(Course.instructor_id == user_id).delete()
    # Clear SOC, Studio, and token relations whose FKs may lack an ON DELETE rule
    _clear_user_references(db, user_id)

    # Store username before deletion for audit log
    deleted_username = user.username
    deleted_user_id = user.id

    # Delete user
    try:
        db.delete(user)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete user {user.username}: {e}")
        # Name the blocking table in the response. The previous message said only
        # "database constraint error", which gave an admin nothing to act on and
        # meant every occurrence needed a log dive to identify.
        import re as _re
        match = _re.search(r'on table "([A-Za-z0-9_]+)"', str(e))
        blocker = (f" Records in '{match.group(1)}' still reference this account."
                   if match else "")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete user: a database constraint blocked it.{blocker}"
        )
    
    # Audit log
    log_admin_action(
        action=AuditActions.USER_DELETED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="user",
        target_id=deleted_user_id,
        target_identifier=deleted_username,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": f"User {deleted_username} deleted"}


# ==================== Lab Management ====================

@router.get("/labs")
async def list_labs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all labs with track and level information"""
    from sqlalchemy.orm import joinedload
    from app.models import Level, Track
    
    labs = db.query(Lab).options(
        joinedload(Lab.level).joinedload(Level.track),
        joinedload(Lab.creator)
    ).all()
    
    # Convert to dict format with track/level info
    result = []
    for lab in labs:
        lab_dict = {
            "id": lab.id,
            "name": lab.name,
            "slug": lab.slug,
            "description": lab.description,
            "difficulty": lab.difficulty,
            "category": lab.category,
            "duration_minutes": lab.duration_minutes,
            "is_active": lab.is_active,
            "track_name": lab.level.track.name if lab.level and lab.level.track else ("Course Assessments" if getattr(lab, 'visibility', 'public') == 'course' else "Uncategorized"),
            "track_slug": lab.level.track.slug if lab.level and lab.level.track else None,
            "level_name": lab.level.name if lab.level else ("Assessments" if getattr(lab, 'visibility', 'public') == 'course' else "Uncategorized"),
            "level_number": lab.level.level_number if lab.level else None,
            "sort_order": lab.sort_order,
            "is_course_exclusive": getattr(lab, 'is_course_exclusive', False),
            "is_course_available": getattr(lab, 'is_course_available', False),
            "visibility": getattr(lab, 'visibility', 'public'),
            "created_by": getattr(lab, 'created_by', None),
            "created_by_username": lab.creator.username if lab.creator else None,
        }
        result.append(lab_dict)
    
    return result


@router.put("/labs/{lab_id}")
async def update_lab(
    lab_id: int,
    request: UpdateLabRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update lab settings"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    if request.name is not None:
        lab.name = request.name
    if request.description is not None:
        lab.description = request.description
    if request.difficulty is not None:
        lab.difficulty = request.difficulty
    if request.category is not None:
        lab.category = request.category
    if request.duration_minutes is not None:
        lab.duration_minutes = request.duration_minutes
    if request.is_active is not None:
        lab.is_active = request.is_active
    if request.is_course_exclusive is not None:
        lab.is_course_exclusive = request.is_course_exclusive
    if request.is_course_available is not None:
        lab.is_course_available = request.is_course_available

    # Handle visibility with backward-compat sync to boolean fields
    if request.visibility is not None:
        lab.visibility = request.visibility
        # Keep deprecated boolean fields in sync
        if request.visibility == 'course':
            lab.is_course_exclusive = True
            lab.is_course_available = True
        elif request.visibility == 'public':
            lab.is_course_exclusive = False
            lab.is_course_available = True
        elif request.visibility == 'draft':
            lab.is_course_exclusive = False
            lab.is_course_available = False
        # pending_public keeps current boolean values

    # level_id: explicit null clears (moves to "Course Assessments" bucket); omit key to leave alone
    if 'level_id' in request.model_fields_set:
        new_level_id = request.level_id
        if new_level_id is not None:
            from app.models import Level
            if not db.query(Level).filter(Level.id == new_level_id).first():
                raise HTTPException(status_code=400, detail=f"Level {new_level_id} not found")
        lab.level_id = new_level_id

    db.commit()
    db.refresh(lab)
    return {"message": f"Lab {lab.name} updated"}


@router.post("/labs/{lab_id}/approve")
async def approve_lab(
    lab_id: int,
    http_request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Approve a lab: change visibility from 'pending_public' to 'public'."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    current_visibility = getattr(lab, 'visibility', 'public')
    if current_visibility != 'pending_public':
        raise HTTPException(
            status_code=400,
            detail=f"Lab visibility is '{current_visibility}', not 'pending_public'. Nothing to approve."
        )

    lab.visibility = 'public'
    lab.is_course_exclusive = False
    lab.is_course_available = True
    db.commit()
    db.refresh(lab)

    log_admin_action(
        action="LAB_APPROVED",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="lab",
        target_id=lab.id,
        target_identifier=lab.slug,
        details={"old_visibility": "pending_public", "new_visibility": "public"},
        ip_address=http_request.client.host if http_request.client else None
    )

    return {"message": f"Lab '{lab.name}' approved and now public"}


@router.post("/labs/{lab_id}/reject")
async def reject_lab(
    lab_id: int,
    http_request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Reject a lab: change visibility from 'pending_public' back to 'course'."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    current_visibility = getattr(lab, 'visibility', 'public')
    if current_visibility != 'pending_public':
        raise HTTPException(
            status_code=400,
            detail=f"Lab visibility is '{current_visibility}', not 'pending_public'. Nothing to reject."
        )

    lab.visibility = 'course'
    lab.is_course_exclusive = True
    lab.is_course_available = True
    db.commit()
    db.refresh(lab)

    log_admin_action(
        action="LAB_REJECTED",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="lab",
        target_id=lab.id,
        target_identifier=lab.slug,
        details={"old_visibility": "pending_public", "new_visibility": "course"},
        ip_address=http_request.client.host if http_request.client else None
    )

    return {"message": f"Lab '{lab.name}' rejected and moved back to course-only"}


@router.post("/labs/{lab_id}/toggle")
async def toggle_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Enable or disable a lab"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    lab.is_active = not lab.is_active
    db.commit()
    
    return {"message": f"Lab {lab.name} {'enabled' if lab.is_active else 'disabled'}"}


@router.post("/labs/bulk-toggle")
async def bulk_toggle_labs(
    body: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Enable or disable multiple labs at once"""
    lab_ids = body.get("lab_ids", [])
    is_active = body.get("is_active", True)
    if not lab_ids:
        return {"message": "No labs specified", "count": 0}
    count = db.query(Lab).filter(Lab.id.in_(lab_ids)).update(
        {"is_active": is_active}, synchronize_session="fetch"
    )
    db.commit()
    return {"message": f"{'Enabled' if is_active else 'Disabled'} {count} exercises", "count": count}


# ==================== Session Management ====================

@router.get("/sessions/active")
async def list_active_sessions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all active lab sessions"""
    sessions = (
        db.query(LabSession)
        .options(joinedload(LabSession.user), joinedload(LabSession.lab))
        .filter(LabSession.status == "running")
        .all()
    )
    return [{
        "id": s.id,
        "user_id": s.user_id,
        "username": s.user.username,
        "lab_name": s.lab.name,
        "lab_slug": s.lab.slug,
        "network_subnet": s.network_subnet,
        "is_diagnostic": bool(s.is_diagnostic),
        "started_at": s.started_at,
        "expires_at": s.expires_at
    } for s in sessions]


@router.get("/sessions/history")
async def session_history(
    page: int = 1,
    per_page: int = 50,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get paginated session history with optional date range filters."""
    from datetime import datetime as dt_cls

    query = db.query(LabSession).options(
        joinedload(LabSession.user), joinedload(LabSession.lab)
    ).order_by(LabSession.started_at.desc())

    if start_date:
        try:
            sd = dt_cls.fromisoformat(start_date.replace('Z', '+00:00')).replace(tzinfo=None)
            query = query.filter(LabSession.started_at >= sd)
        except (ValueError, TypeError):
            pass

    if end_date:
        try:
            ed = dt_cls.fromisoformat(end_date.replace('Z', '+00:00')).replace(tzinfo=None)
            query = query.filter(LabSession.started_at <= ed)
        except (ValueError, TypeError):
            pass

    total = query.count()
    sessions = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "sessions": [{
            "id": s.id,
            "user_id": s.user_id,
            "username": s.user.username,
            "lab_name": s.lab.name,
            "status": s.status,
            "is_diagnostic": bool(s.is_diagnostic),
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "stopped_at": s.stopped_at.isoformat() if s.stopped_at else None
        } for s in sessions],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.post("/sessions/terminate/{session_id}")
async def terminate_session(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Terminate a specific lab session"""
    session = db.query(LabSession).filter(LabSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")
    
    try:
        docker_manager.destroy_lab_environment(session.user_id, session.lab.slug)
        session.status = "stopped"
        session.stopped_at = datetime.now(timezone.utc)
        db.commit()
        return {"message": "Session terminated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/reset-stale")
@limiter.limit("10/minute")
async def reset_stale_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Reset a stale session (DB says running but containers are gone)."""
    session = db.query(LabSession).filter(LabSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not in running state")

    lab = session.lab
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found for session")

    # Attempt Docker cleanup (safe even if containers are already gone)
    try:
        docker_manager.destroy_lab_environment(session.user_id, lab.slug)
    except Exception as e:
        logger.warning(f"Docker cleanup during stale reset (non-fatal): {e}")

    session.status = "stopped"
    session.stopped_at = datetime.now(timezone.utc)
    db.commit()

    log_admin_action(
        action=AuditActions.STALE_SESSION_RESET,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="session",
        target_id=session_id,
        target_identifier=f"{session.user.username}/{lab.slug}",
        details={"user_id": session.user_id, "username": session.user.username, "lab_slug": lab.slug},
        ip_address=request.client.host if request.client else None
    )

    return {
        "message": f"Stale session reset for {session.user.username}. They can now start a new lab.",
        "session_id": session_id,
    }


@router.post("/sessions/{session_id}/resync-vpn")
@limiter.limit("10/minute")
async def resync_session_vpn(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Re-sync VPN peer for a session's user."""
    session = db.query(LabSession).filter(LabSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user = session.user
    wg_config = db.query(WireGuardConfig).filter(WireGuardConfig.user_id == user.id).first()
    if not wg_config:
        raise HTTPException(status_code=404, detail="User has no VPN configuration")

    # Remove existing peer (ignore failure if already gone)
    try:
        wireguard_manager.remove_peer(wg_config.public_key)
    except Exception:
        pass

    # Re-add peer
    success = wireguard_manager.add_peer(wg_config.public_key, wg_config.client_ip)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to re-register VPN peer")

    # Re-apply firewall rules
    try:
        docker_manager.ensure_vpn_firewall_rules()
    except Exception as e:
        logger.warning(f"Firewall rule refresh during VPN resync (non-fatal): {e}")

    user.vpn_registered = True
    db.commit()

    log_admin_action(
        action=AuditActions.VPN_PEER_RESYNCED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="session",
        target_id=session_id,
        target_identifier=user.username,
        details={"user_id": user.id, "username": user.username, "client_ip": wg_config.client_ip},
        ip_address=request.client.host if request.client else None
    )

    return {
        "message": f"VPN re-synced for {user.username}. Peer re-registered and firewall rules refreshed.",
        "session_id": session_id,
    }


@router.post("/vpn/reconcile-peers")
@limiter.limit("6/minute")
async def reconcile_vpn_peers(
    request: Request,
    apply: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Prune dead and duplicate WireGuard peers from wg0.

    Historical allocator churn (re-downloads that minted a new key, formula
    changes, deleted users) can leave orphan peers on wg0 that no live config
    owns, and stale-IP peers squatting on an address now assigned to someone
    else. Both break connectivity for the rightful owner (allowed_ips is
    exclusive per peer). This reconciles wg0 against wireguard_configs: it
    removes orphans and repairs IP mismatches.

    Defaults to a DRY RUN (reports what it would change, touches nothing). Pass
    ?apply=true to actually prune and repair. `missing` (DB configs with no live
    peer) is reported for visibility; use the per-user resync to re-add those.
    """
    valid = {
        cfg.public_key.strip(): cfg.client_ip
        for cfg in db.query(WireGuardConfig).all()
        if cfg.public_key and cfg.client_ip
    }
    report = wireguard_manager.reconcile_peers(valid, dry_run=not apply)

    if report.get("error"):
        raise HTTPException(status_code=503, detail=report["error"])

    if apply and (report["removed"] or report["repaired"]):
        try:
            docker_manager.ensure_vpn_firewall_rules()
        except Exception as e:
            logger.warning(f"Firewall refresh after peer reconcile (non-fatal): {e}")
        log_admin_action(
            action=AuditActions.VPN_PEER_RESYNCED,
            admin_user_id=admin.id,
            admin_username=admin.username,
            target_type="vpn",
            target_id=0,
            target_identifier="reconcile-peers",
            details={
                "removed": len(report["removed"]),
                "repaired": len(report["repaired"]),
                "kept": report["kept"],
                "missing": len(report["missing"]),
            },
            ip_address=request.client.host if request.client else None,
        )

    verb = "Pruned" if apply else "Would prune"
    report["message"] = (
        f"{verb} {len(report['removed'])} dead and {len(report['repaired'])} "
        f"stale peer(s); {report['kept']} correct, {len(report['missing'])} "
        f"config(s) with no live peer."
        + ("" if apply else " Dry run: pass apply=true to make changes.")
    )
    return report


@router.post("/sessions/terminate-all")
@limiter.limit("2/minute")
async def terminate_all_sessions(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Emergency: terminate all running sessions - rate limited to 2 per minute"""
    sessions = db.query(LabSession).options(
        joinedload(LabSession.lab)
    ).filter(LabSession.status == "running").all()
    terminated = 0
    
    for session in sessions:
        try:
            docker_manager.destroy_lab_environment(session.user_id, session.lab.slug)
            session.status = "stopped"
            session.stopped_at = datetime.now(timezone.utc)
            terminated += 1
        except Exception as e:
            logger.error(f"Failed to terminate session {session.id}: {e}")
    
    db.commit()
    
    # Audit log
    log_admin_action(
        action=AuditActions.ALL_SESSIONS_TERMINATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="session",
        details={"sessions_terminated": terminated, "total_sessions": len(sessions)},
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": f"Terminated {terminated} sessions"}


@router.delete("/sessions/history")
@limiter.limit("5/minute")
async def clear_session_history(
    request: Request,
    status_filter: str = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Clear session history (non-running sessions only) - rate limited to 5 per minute"""
    query = db.query(LabSession).filter(LabSession.status != "running")
    
    # Optional filter by status
    if status_filter:
        query = query.filter(LabSession.status == status_filter)
    
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    
    # Audit log
    log_admin_action(
        action=AuditActions.SESSION_HISTORY_CLEARED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="session",
        details={"deleted_count": deleted_count, "status_filter": status_filter},
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": f"Cleared {deleted_count} session records", "deleted_count": deleted_count}


@router.get("/sessions/health")
async def get_sessions_health(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """
    Get live container health for all active sessions.
    Returns detailed container status, resource usage, health status,
    VPN connectivity, stale detection, and container IPs.
    """
    sessions = db.query(LabSession).filter(LabSession.status == "running").all()

    # Build VPN peer lookup (single API call + single DB query)
    vpn_peer_lookup = {}  # user_id -> {connected, registered, last_handshake}
    try:
        peers = wireguard_manager.list_peers()
        if peers:
            pk_to_peer = {p.get("public_key", "").strip(): p for p in peers}
            wg_configs = db.query(WireGuardConfig).all()
            now_utc = datetime.now(timezone.utc)
            for cfg in wg_configs:
                peer_data = pk_to_peer.get(cfg.public_key.strip())
                if peer_data:
                    connected = False
                    last_hs_display = ""
                    raw_hs = peer_data.get("last_handshake") or peer_data.get("last_handshake_time")
                    if raw_hs:
                        try:
                            if isinstance(raw_hs, (int, float)) and raw_hs > 0:
                                hs_dt = datetime.fromtimestamp(raw_hs, tz=timezone.utc)
                            elif isinstance(raw_hs, str):
                                hs_dt = datetime.fromisoformat(raw_hs.replace("Z", "+00:00"))
                            else:
                                hs_dt = None
                            if hs_dt:
                                age_s = (now_utc - hs_dt).total_seconds()
                                connected = age_s <= 180
                                if age_s < 60:
                                    last_hs_display = f"{int(age_s)}s ago"
                                elif age_s < 3600:
                                    last_hs_display = f"{int(age_s // 60)}m ago"
                                elif age_s < 86400:
                                    last_hs_display = f"{int(age_s // 3600)}h ago"
                                else:
                                    last_hs_display = f"{int(age_s // 86400)}d ago"
                        except Exception:
                            pass
                    vpn_peer_lookup[cfg.user_id] = {
                        "connected": connected,
                        "registered": True,
                        "last_handshake": last_hs_display,
                    }
                else:
                    vpn_peer_lookup[cfg.user_id] = {
                        "connected": False,
                        "registered": False,
                        "last_handshake": "",
                    }
    except Exception as e:
        logger.warning(f"Failed to build VPN peer lookup: {e}")

    health_data = []
    for session in sessions:
        lab = session.lab
        user = session.user

        # Get container health from Docker (skip stats for speed;
        # container.stats() blocks ~1-2s per container)
        containers = docker_manager.get_container_health(session.user_id, lab.slug, include_stats=False)

        # Merge container IPs from get_lab_targets
        try:
            targets = docker_manager.get_lab_targets(session.user_id, lab.slug)
            ip_map = {t["name"]: t.get("ip", "") for t in targets}
            for c in containers:
                c["ip"] = ip_map.get(c["name"], "")
        except Exception:
            pass

        # Stale detection: DB says running but no containers exist
        is_stale = len(containers) == 0

        # Calculate time remaining
        now = datetime.now(timezone.utc)
        expires_at = session.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        time_remaining_seconds = 0
        if expires_at:
            diff = (expires_at - now).total_seconds()
            time_remaining_seconds = max(0, int(diff))

        # VPN status for this user
        has_vpn_config = user.id in vpn_peer_lookup
        vpn_info = vpn_peer_lookup.get(user.id, {
            "connected": False,
            "registered": False,
            "last_handshake": "",
        })

        # RangeBox status for this session
        rangebox_info = {"enabled": bool(session.rangebox_enabled), "status": "not_found"}
        if session.rangebox_enabled:
            try:
                rb_status = docker_manager.get_rangebox_status(session.user_id, lab.slug, include_stats=False)
                rangebox_info["status"] = rb_status.get("status", "not_found")
            except Exception:
                pass
        # Also check for standalone RangeBox bridged to this lab
        if rangebox_info["status"] == "not_found":
            try:
                rb_standalone = docker_manager.get_rangebox_status(session.user_id, "standalone", include_stats=False)
                if rb_standalone.get("status") == "running":
                    # Check if standalone is bridged to this lab network
                    lab_net_name = f"lab_{session.user_id}_{lab.slug}"
                    rb_container = docker_manager.client.containers.get(f"rangebox_{session.user_id}_standalone")
                    rb_networks = rb_container.attrs.get("NetworkSettings", {}).get("Networks", {})
                    if lab_net_name in rb_networks:
                        rangebox_info = {"enabled": True, "status": "running", "mode": "standalone"}
            except Exception:
                pass

        health_data.append({
            "session_id": session.id,
            "user_id": user.id,
            "username": user.username,
            "lab_id": lab.id,
            "lab_name": lab.name,
            "lab_slug": lab.slug,
            "network_subnet": session.network_subnet,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "time_remaining_seconds": time_remaining_seconds,
            "is_diagnostic": bool(session.is_diagnostic),
            "containers": containers,
            "is_stale": is_stale,
            "vpn": {
                "has_config": has_vpn_config,
                "registered": vpn_info.get("registered", False),
                "connected": vpn_info.get("connected", False),
                "last_handshake": vpn_info.get("last_handshake", ""),
            },
            "rangebox": rangebox_info,
            "impersonated_by": None,
        })
        # Add impersonation info if present
        if session.impersonated_by:
            admin_user = db.query(User).filter(User.id == session.impersonated_by).first()
            health_data[-1]["impersonated_by"] = {
                "admin_id": session.impersonated_by,
                "admin_username": admin_user.username if admin_user else "unknown",
            }

    return {
        "total_sessions": len(health_data),
        "sessions": health_data
    }


# ==================== Admin Impersonate ====================

# Track which lab the admin is currently impersonating.
# Stored in a shared JSON file so all uvicorn workers see the same state.
import json as _json, fcntl as _fcntl

_IMPERSONATION_FILE = "/tmp/ocr_admin_impersonation.json"


def _read_impersonation_store() -> dict:
    """Read the shared impersonation state (worker-safe)."""
    try:
        with open(_IMPERSONATION_FILE, "r") as f:
            _fcntl.flock(f, _fcntl.LOCK_SH)
            data = _json.load(f)
            _fcntl.flock(f, _fcntl.LOCK_UN)
            return data
    except (FileNotFoundError, _json.JSONDecodeError):
        return {}


def _write_impersonation_store(data: dict):
    """Write the shared impersonation state (worker-safe)."""
    with open(_IMPERSONATION_FILE, "w") as f:
        _fcntl.flock(f, _fcntl.LOCK_EX)
        _json.dump(data, f)
        _fcntl.flock(f, _fcntl.LOCK_UN)


class _AdminImpersonation:
    """Dict-like wrapper backed by a shared file for multi-worker support."""

    def get(self, admin_id: int):
        store = _read_impersonation_store()
        return store.get(str(admin_id))

    def __setitem__(self, admin_id: int, value: dict):
        store = _read_impersonation_store()
        store[str(admin_id)] = value
        _write_impersonation_store(store)

    def __delitem__(self, admin_id: int):
        store = _read_impersonation_store()
        store.pop(str(admin_id), None)
        _write_impersonation_store(store)

    def __contains__(self, admin_id: int):
        store = _read_impersonation_store()
        return str(admin_id) in store


_admin_impersonation = _AdminImpersonation()


# NOTE: Literal routes (/disconnect, /status, /launch) MUST be defined
# BEFORE the parameterized route (/{session_id}) so FastAPI matches them first.

@router.post("/impersonate/disconnect")
async def disconnect_impersonation(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Disconnect admin's RangeBox from any impersonated student lab network."""
    prev = _admin_impersonation.get(admin.id)
    if not prev:
        return {"message": "Not currently impersonating any session"}

    try:
        docker_manager.unbridge_standalone_rangebox_from_lab(
            admin.id, prev["lab_slug"], prev["user_id"]
        )
    except Exception as e:
        logger.warning(f"Error disconnecting impersonation: {e}")

    del _admin_impersonation[admin.id]
    return {"message": f"Disconnected from {prev['username']}'s lab network"}


@router.get("/impersonate/status")
async def impersonation_status(
    admin: User = Depends(get_current_admin_user),
):
    """Check if admin is currently impersonating a student session."""
    prev = _admin_impersonation.get(admin.id)
    if not prev:
        return {"active": False}
    return {"active": True, **prev}


@router.post("/impersonate/launch")
async def impersonate_launch_lab(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    Launch a lab AS a specific student, even if they aren't logged in.
    Creates a session under the student's user_id with their subnet,
    marks it as admin-initiated, and bridges the admin's RangeBox.
    """
    import asyncio

    body = await request.json()
    target_user_id = body.get("user_id")
    lab_slug = body.get("lab_slug")

    if not target_user_id or not lab_slug:
        raise HTTPException(status_code=400, detail="user_id and lab_slug required")

    # Validate target user
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate lab
    lab = db.query(Lab).filter(Lab.slug == lab_slug).first()
    if not lab:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_slug}' not found")

    # Check if target user already has an active session
    existing = db.query(LabSession).filter(
        LabSession.user_id == target_user_id,
        LabSession.status.in_(["starting", "running"]),
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"{target_user.username} already has an active session ({existing.lab.name}). "
                   f"Stop it first or use the Impersonate button on their existing session."
        )

    # Create session under the student's user_id, but marked as admin-initiated
    session = LabSession(
        user_id=target_user_id,
        lab_id=lab.id,
        status="starting",
        is_diagnostic=False,
        rangebox_enabled=False,
        impersonated_by=admin.id,
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        compose_content = (lab.compose_file or "").strip()

        if compose_content:
            # Lab has containers — start them
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: docker_manager.create_lab_environment(
                    user_id=target_user_id,
                    lab_slug=lab_slug,
                    compose_content=compose_content,
                )
            )
            second_octet, third_octet = get_subnet_id(target_user_id, lab_slug)
            session.status = "running"
            session.network_id = result.get("network_id", f"lab_{target_user_id}_{lab_slug}")
            session.network_subnet = result.get("subnet", f"10.{second_octet}.{third_octet}.0/24")
        else:
            # Lab has no compose file.
            # Create a session record but skip container creation.
            second_octet, third_octet = get_subnet_id(target_user_id, lab_slug)
            session.status = "running"
            session.network_id = f"lab_{target_user_id}_{lab_slug}"
            session.network_subnet = f"10.{second_octet}.{third_octet}.0/24"

        db.commit()

        # Bridge admin's standalone RangeBox to the student's lab network
        bridged = False
        if compose_content:
            try:
                docker_manager.bridge_standalone_rangebox_to_lab(
                    admin.id, lab_slug, target_user_id
                )
                bridged = True
                _admin_impersonation[admin.id] = {
                    "user_id": target_user_id,
                    "lab_slug": lab_slug,
                    "username": target_user.username,
                }
            except Exception as e:
                logger.warning(f"Could not bridge admin RangeBox: {e}")

        # Log activity — clearly shows admin initiated this
        log_activity(
            db, EventTypes.LAB_STARTED,
            actor_id=admin.id,
            target_type="lab",
            target_id=lab.id,
            target_label=lab.name,
            detail={
                "source": "admin_impersonation",
                "admin_id": admin.id,
                "admin_username": admin.username,
                "target_user_id": target_user_id,
                "target_username": target_user.username,
                "has_containers": bool(compose_content),
            },
        )

        logger.info(
            f"Admin {admin.username} launched lab {lab_slug} as user "
            f"{target_user.username} (id={target_user_id}), bridged={bridged}, "
            f"has_compose={bool(compose_content)}"
        )

        note = ""
        if not compose_content:
            note = "This lab has no containers (shared target). Session created for tracking only."
        elif bridged:
            note = "Open your RangeBox to access the lab."
        else:
            note = "Launch a standalone RangeBox first, then use the Impersonate button."

        return {
            "message": f"Lab started as {target_user.username}",
            "session_id": session.id,
            "lab_slug": lab_slug,
            "network_subnet": session.network_subnet,
            "bridged": bridged,
            "note": note,
        }

    except Exception as e:
        session.status = "error"
        db.commit()
        logger.error(f"Admin impersonate launch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start lab: {str(e)}")


@router.post("/impersonate/{session_id}")
async def impersonate_session(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    Bridge the admin's standalone RangeBox to a student's lab network.
    Auto-disconnects from any previous impersonation.
    """
    # Look up the target session
    session = db.query(LabSession).filter(
        LabSession.id == session_id,
        LabSession.status == "running",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lab = session.lab
    target_user_id = session.user_id
    target_user = session.user

    # Auto-disconnect from previous impersonation
    prev = _admin_impersonation.get(admin.id)
    if prev:
        try:
            docker_manager.unbridge_standalone_rangebox_from_lab(
                admin.id, prev["lab_slug"], prev["user_id"]
            )
            logger.info(f"Admin {admin.username} disconnected from previous impersonation "
                        f"(user {prev['user_id']}, lab {prev['lab_slug']})")
        except Exception as e:
            logger.warning(f"Failed to disconnect previous impersonation: {e}")
        del _admin_impersonation[admin.id]

    # Bridge admin's standalone RangeBox to the student's lab network
    try:
        docker_manager.bridge_standalone_rangebox_to_lab(
            admin.id, lab.slug, target_user_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bridge RangeBox: {str(e)}. "
                   f"Make sure you have a standalone RangeBox running first.",
        )

    _admin_impersonation[admin.id] = {
        "user_id": target_user_id,
        "lab_slug": lab.slug,
        "username": target_user.username if target_user else "unknown",
    }

    logger.info(f"Admin {admin.username} impersonating user {target_user_id} "
                f"on lab {lab.slug}")

    return {
        "message": f"Connected to {target_user.username}'s lab network",
        "lab_slug": lab.slug,
        "target_user": target_user.username if target_user else "unknown",
        "network": session.network_subnet,
    }


# ==================== VPN Management ====================


def _format_handshake(value) -> str:
    """Format a handshake timestamp for display.
    Accepts ISO 8601 string, unix timestamp (int/float), or None."""
    if not value:
        return ""
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, (int, float)):
            if value == 0:
                return ""
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
        else:
            return ""
        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except (ValueError, TypeError, OSError):
        return str(value)


def _format_bytes(value) -> str:
    """Format byte count for human-readable display."""
    if value is None:
        return ""
    try:
        b = int(value)
    except (ValueError, TypeError):
        return ""
    if b == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            if unit == "B":
                return f"{b} {unit}"
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


@router.get("/vpn/peers")
async def list_vpn_peers(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all VPN peers from Peer Manager - returns empty list if API unavailable.

    Each peer is annotated with a `health` field:
      - 'ok': peer is registered correctly
      - 'no_allowed_ips': peer exists but allowed_ips is empty/(none) — WG drops all its traffic
      - 'duplicate_for_ip': another peer (not this one) holds the IP the DB expects for its user
      - 'orphan_no_db': peer is registered on WG but has no matching DB row
    """
    try:
        peers = wireguard_manager.list_peers()

        # If API is unavailable, return empty list instead of error
        if not peers:
            logger.debug("Peer Manager API unavailable, returning empty peer list")
            return {"peers": []}

        # Build lookups so we can detect peers that occupy a slot the DB
        # believes belongs to a different key (stale duplicate)
        all_configs = db.query(WireGuardConfig).all()
        ip_to_db = {f"{c.client_ip}/32": (c.public_key, c.user_id) for c in all_configs}
        pubkey_to_db = {c.public_key: c for c in all_configs}

        # Enrich with user info from database
        enriched_peers = []
        for peer in peers:
            public_key = peer.get("public_key")
            if not public_key:
                continue

            # Normalize public key (trim whitespace)
            public_key = public_key.strip()
            allowed_ips = (peer.get("allowed_ips") or "").strip()
            is_labs_server = public_key == settings.WG_SERVER_PUBLIC_KEY

            wg_config = pubkey_to_db.get(public_key)

            user_info = None
            if wg_config:
                user = wg_config.user
                user_info = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            else:
                logger.debug(f"Unmatched peer: public_key={public_key[:30]}..., allowed_ips={allowed_ips}")

            # Detect health problems (skip the labs server itself)
            health = "ok"
            health_detail = None
            repair_user_id = None
            if not is_labs_server:
                if allowed_ips in ("", "(none)"):
                    health = "no_allowed_ips"
                    health_detail = "WireGuard drops all traffic from this peer until allowed_ips is set."
                    if wg_config:
                        repair_user_id = wg_config.user_id
                elif wg_config is None:
                    db_owner = ip_to_db.get(allowed_ips)
                    if db_owner and db_owner[0] != public_key:
                        health = "duplicate_for_ip"
                        health_detail = f"Conflicts with the registered peer for user {db_owner[1]}; remove this row or repair the user."
                        repair_user_id = db_owner[1]
                    else:
                        health = "orphan_no_db"
                        health_detail = "No matching VPN config in the database."

            # Map Peer Manager field names to what the frontend expects
            # and format values for display
            last_hs = peer.get("last_handshake_time") or peer.get("last_handshake")
            rx = peer.get("rx_bytes")
            tx = peer.get("tx_bytes")

            enriched_peers.append({
                **peer,
                "public_key": public_key,
                "user": user_info,
                "is_labs_server": is_labs_server,
                "latest_handshake": _format_handshake(last_hs),
                "last_handshake_raw": last_hs,
                "transfer_rx": _format_bytes(rx),
                "transfer_tx": _format_bytes(tx),
                "health": health,
                "health_detail": health_detail,
                "repair_user_id": repair_user_id,
            })

        return {"peers": enriched_peers}
    except Exception as e:
        logger.warning(f"Failed to list VPN peers: {e}, returning empty list")
        # Return empty list instead of error to prevent UI blocking
        return {"peers": []}


@router.post("/vpn/peers/{user_id}/repair")
async def repair_vpn_peer(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Re-assert WireGuard registration for a user from DB truth.

    Removes any peer on the WG server whose public key matches the DB row OR
    whose allowed_ips matches the DB client_ip (catches stale duplicates), then
    re-adds the DB peer with the correct allowed_ips. Use this when a user can
    handshake but their traffic is dropped (allowed_ips=(none)) or when a stale
    duplicate has stolen their IP slot.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    wg_config = db.query(WireGuardConfig).filter(WireGuardConfig.user_id == user_id).first()
    if not wg_config:
        raise HTTPException(status_code=404, detail="User has no VPN config")

    db_pubkey = wg_config.public_key
    db_allowed = f"{wg_config.client_ip}/32"

    peers = wireguard_manager.list_peers()
    if peers is None:
        raise HTTPException(status_code=502, detail="Peer Manager API unavailable")

    removed = []
    for p in peers:
        pk = (p.get("public_key") or "").strip()
        ips = (p.get("allowed_ips") or "").strip()
        if pk == settings.WG_SERVER_PUBLIC_KEY:
            continue
        if pk == db_pubkey or ips == db_allowed:
            try:
                if wireguard_manager.remove_peer(pk):
                    removed.append(pk[:20] + "...")
            except Exception as e:
                logger.warning(f"Failed to remove peer {pk[:20]}... during repair: {e}")

    added = wireguard_manager.add_peer(db_pubkey, wg_config.client_ip)
    if not added:
        raise HTTPException(status_code=500, detail="Removed conflicting peers but failed to re-add the DB peer")

    user.vpn_registered = True
    db.commit()

    return {
        "message": f"Repaired VPN peer for {user.username}",
        "removed_peers": removed,
        "registered_pubkey": db_pubkey[:20] + "...",
        "client_ip": wg_config.client_ip,
    }


@router.get("/vpn/status")
async def vpn_sync_status(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get VPN sync status - compare DB to Peer Manager"""
    # Get all users with WireGuard configs
    wg_configs = db.query(WireGuardConfig).all()
    
    # Get peers from Peer Manager
    peers = wireguard_manager.list_peers() or []
    peer_keys = {p.get("public_key", "").strip() for p in peers}
    
    registered = []
    unregistered = []
    
    for config in wg_configs:
        user = config.user
        info = {
            "user_id": user.id,
            "username": user.username,
            "client_ip": config.client_ip,
            "public_key": config.public_key[:20] + "...",
            "vpn_registered_db": user.vpn_registered
        }
        
        if config.public_key in peer_keys:
            registered.append(info)
        else:
            unregistered.append(info)
    
    return {
        "registered_count": len(registered),
        "unregistered_count": len(unregistered),
        "registered": registered,
        "unregistered": unregistered
    }


@router.post("/vpn/sync")
async def sync_vpn_peers(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Sync all user VPN configs to Peer Manager"""
    wg_configs = db.query(WireGuardConfig).all()
    
    synced = 0
    failed = 0
    
    for config in wg_configs:
        user = config.user
        if not user.is_approved or not user.is_active or user.is_locked:
            continue
        
        try:
            success = wireguard_manager.sync_peer(config.public_key, config.client_ip)
            if success:
                user.vpn_registered = True
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to sync peer for {user.username}: {e}")
            failed += 1
    
    db.commit()
    
    return {
        "message": f"Synced {synced} peers, {failed} failed",
        "synced": synced,
        "failed": failed
    }


@router.post("/vpn/register/{user_id}")
async def register_vpn_peer(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Manually register a user's VPN peer with Peer Manager"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    wg_config = db.query(WireGuardConfig).filter(WireGuardConfig.user_id == user_id).first()
    if not wg_config:
        raise HTTPException(status_code=404, detail="User has no VPN config - they need to download it first")
    
    try:
        success = wireguard_manager.add_peer(wg_config.public_key, wg_config.client_ip)
        if success:
            user.vpn_registered = True
            db.commit()
            return {"message": f"VPN peer registered for {user.username}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to register peer")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vpn/peer/{user_id}")
async def remove_vpn_peer(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Remove a user's VPN peer from Peer Manager"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    wg_config = db.query(WireGuardConfig).filter(WireGuardConfig.user_id == user_id).first()
    if not wg_config:
        raise HTTPException(status_code=404, detail="User has no VPN config")
    
    try:
        success = wireguard_manager.remove_peer(wg_config.public_key)
        if success:
            user.vpn_registered = False
            db.commit()
            return {"message": f"VPN peer removed for {user.username}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove peer")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vpn/peer-by-key/{public_key:path}")
async def remove_vpn_peer_by_key(
    public_key: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Remove a VPN peer from Peer Manager by public key (for unknown peers)"""
    import urllib.parse
    # URL decode the public key
    public_key = urllib.parse.unquote(public_key)
    
    # Don't allow removing the server's own key
    if public_key == settings.WG_SERVER_PUBLIC_KEY:
        raise HTTPException(status_code=400, detail="Cannot remove the WireGuard server peer")
    
    try:
        success = wireguard_manager.remove_peer(public_key)
        if success:
            # Also update database if this peer belongs to a user
            wg_config = db.query(WireGuardConfig).filter(
                WireGuardConfig.public_key == public_key
            ).first()
            if wg_config:
                wg_config.user.vpn_registered = False
                db.commit()
            return {"message": "VPN peer removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove peer")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Container Management ====================

@router.post("/containers/cleanup-orphaned")
async def cleanup_orphaned_containers(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Clean up orphaned lab containers that aren't associated with active sessions"""
    try:
        removed_count = docker_manager.cleanup_orphaned_containers()
        log_admin_action(
            action=AuditActions.CLEANUP_ORPHANED_CONTAINERS,
            admin_user_id=admin.id,
            admin_username=admin.username,
            target_type="containers",
            target_id=None,
            details={"removed_count": removed_count}
        )
        return {
            "message": f"Cleaned up {removed_count} orphaned containers",
            "removed_count": removed_count
        }
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Docker Disk Management ====================

@router.get("/docker/disk-usage")
async def get_docker_disk_usage(
    admin: User = Depends(get_current_admin_user)
):
    """Return Docker disk usage broken down by images, containers, build cache, and volumes."""
    result = docker_manager.get_disk_usage()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/labs/{lab_id}/images")
async def get_lab_images(
    lab_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List cached Docker images for a specific exercise."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Exercise not found")

    images = docker_manager.get_lab_images(lab.slug)
    total_bytes = sum(i["size_bytes"] for i in images)
    return {
        "lab_id": lab_id,
        "slug": lab.slug,
        "images": images,
        "total_bytes": total_bytes,
    }


@router.delete("/labs/{lab_id}/images")
@limiter.limit("10/minute")
async def delete_lab_images(
    request: Request,
    lab_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete cached Docker images for a specific exercise.

    The exercise will rebuild its images on the next student launch.
    """
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Check that no active sessions are using this exercise
    active = db.query(LabSession).filter(
        LabSession.lab_id == lab_id,
        LabSession.status == "running"
    ).count()
    if active > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete images while {active} active session(s) are using this exercise"
        )

    result = docker_manager.delete_lab_images(lab.slug)

    log_admin_action(
        action=AuditActions.LAB_IMAGE_DELETED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="lab",
        target_id=lab.id,
        target_identifier=lab.slug,
        ip_address=request.client.host if request.client else None,
        details={
            "images_removed": result["removed"],
            "bytes_freed": result["bytes_freed"],
        }
    )

    return {
        "message": f"Deleted {result['removed']} cached image(s) for {lab.name}",
        "images_removed": result["removed"],
        "bytes_freed": result["bytes_freed"],
        "errors": result.get("errors"),
    }


@router.post("/docker/prune-images")
@limiter.limit("2/minute")
async def prune_all_images(
    request: Request,
    admin: User = Depends(get_current_admin_user)
):
    """Remove all unused Docker images not referenced by running containers.

    Exercises will rebuild their images on the next student launch.
    """
    result = docker_manager.prune_all_images()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    log_admin_action(
        action=AuditActions.IMAGES_PRUNED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="docker",
        target_id=None,
        ip_address=request.client.host if request.client else None,
        details=result
    )

    return {
        "message": f"Pruned {result['images_removed']} image(s), freed {_format_bytes(result['bytes_freed'])}",
        **result,
    }


@router.post("/docker/prune-build-cache")
@limiter.limit("2/minute")
async def prune_build_cache(
    request: Request,
    admin: User = Depends(get_current_admin_user)
):
    """Remove Docker build cache to free disk space.

    Future image builds will take longer as layers must be rebuilt from scratch.
    """
    result = docker_manager.prune_build_cache()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    log_admin_action(
        action=AuditActions.BUILD_CACHE_PRUNED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="docker",
        target_id=None,
        ip_address=request.client.host if request.client else None,
        details=result
    )

    return {
        "message": f"Pruned {result['cache_entries_removed']} cache entries, freed {_format_bytes(result['bytes_freed'])}",
        **result,
    }


def _format_bytes(n: int) -> str:
    """Format byte count as a human-readable string."""
    if n >= 1_073_741_824:
        return f"{n / 1_073_741_824:.1f} GB"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


# ==================== Statistics ====================

@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get platform statistics"""
    total_users = db.query(func.count(User.id)).scalar()
    pending_users = db.query(func.count(User.id)).filter(User.is_approved == False, User.is_active == True).scalar()
    locked_users = db.query(func.count(User.id)).filter(User.is_locked == True).scalar()
    active_labs = db.query(func.count(LabSession.id)).filter(LabSession.status == "running").scalar()

    # Get live peer count from Peer Manager; fall back to DB count if API unavailable
    peers = wireguard_manager.list_peers()
    if peers is not None:
        # Exclude the lab server's own WireGuard peer from the count
        vpn_registered = sum(
            1 for p in peers
            if p.get("public_key", "").strip() != settings.WG_SERVER_PUBLIC_KEY
        )
    else:
        vpn_registered = db.query(func.count(User.id)).filter(User.vpn_registered == True).scalar()

    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "locked_users": locked_users,
        "active_labs": active_labs,
        "vpn_registered": vpn_registered
    }


# ==================== Lab Creation & Flag Management ====================

@router.post("/labs")
@limiter.limit("10/minute")
async def create_lab(
    request: Request,
    payload: LabCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new lab from the web UI."""
    import yaml as yaml_lib, hashlib, json

    # If lab_yaml is provided, parse it and use values as defaults
    lab_data = {}
    if payload.lab_yaml:
        try:
            lab_data = yaml_lib.safe_load(payload.lab_yaml) or {}
        except yaml_lib.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid Lab YAML: {e}")

    # Form fields override parsed YAML values (if both provided, form wins)
    name = payload.name or lab_data.get('name', '')
    slug = payload.slug or lab_data.get('slug', '')
    if not name or not slug:
        raise HTTPException(status_code=400, detail="Name and slug are required")

    existing = db.query(Lab).filter(Lab.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lab slug already exists")

    description = payload.description or lab_data.get('description')
    scenario = payload.scenario or lab_data.get('scenario')
    difficulty = lab_data.get('difficulty', payload.difficulty) if lab_data else payload.difficulty
    category = lab_data.get('category', payload.category) if lab_data else payload.category
    duration_minutes = lab_data.get('duration_minutes', payload.duration_minutes) if lab_data else payload.duration_minutes
    compose_file = payload.compose_file

    # Validate compose YAML if provided
    if compose_file:
        try:
            yaml_lib.safe_load(compose_file)
        except yaml_lib.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid compose YAML: {e}")

    # JSON-encode array fields (from YAML or form)
    objectives = payload.objectives or (json.dumps(lab_data['objectives']) if lab_data.get('objectives') else None)
    hints = payload.hints or (json.dumps(lab_data['hints']) if lab_data.get('hints') else None)
    tools = payload.tools or (json.dumps(lab_data['tools']) if lab_data.get('tools') else None)
    hostnames_val = payload.hostnames or (json.dumps(lab_data['hostnames']) if lab_data.get('hostnames') else None)

    # Hash flag
    flag = payload.flag or lab_data.get('flag', '')
    flag_hash = hashlib.sha256(flag.encode()).hexdigest() if flag else None

    # Visibility
    valid_vis = ('draft', 'course', 'public')
    visibility = payload.visibility or lab_data.get('visibility', 'public')
    if visibility not in valid_vis:
        visibility = 'public'

    # Auto-generate scenario brief from scenario
    scenario_brief = None
    if scenario:
        scenario_brief = scenario[:150] + "..." if len(scenario) > 150 else scenario

    lab = Lab(
        name=name,
        slug=slug,
        description=description,
        scenario=scenario,
        scenario_brief=scenario_brief,
        difficulty=difficulty,
        category=category,
        duration_minutes=duration_minutes,
        level_id=payload.level_id,
        compose_file=compose_file,
        objectives=objectives,
        hints=hints,
        tools=tools,
        hostnames=hostnames_val,
        flag_hash=flag_hash,
        visibility=visibility,
        is_active=True,
        sort_order=0,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)

    log_admin_action(
        action=AuditActions.LAB_CREATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="lab",
        target_id=lab.id,
        target_identifier=lab.slug,
        details={"name": lab.name, "slug": lab.slug},
        ip_address=request.client.host if request.client else None
    )

    return {"message": f"Lab '{lab.name}' created", "id": lab.id}


@router.put("/labs/{lab_id}/compose")
async def update_lab_compose(
    lab_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update a lab's docker-compose file content."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    compose_content = payload.get("compose_file", "")
    if compose_content:
        import yaml
        try:
            yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    lab.compose_file = compose_content
    db.commit()
    return {"message": "Compose file updated"}


@router.get("/labs/{lab_id}/details")
async def get_lab_details_admin(
    lab_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Return full lab details including compose file and flag status."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    return {
        "id": lab.id,
        "name": lab.name,
        "slug": lab.slug,
        "description": lab.description,
        "scenario": lab.scenario,
        "difficulty": lab.difficulty,
        "category": lab.category,
        "duration_minutes": lab.duration_minutes,
        "compose_file": lab.compose_file,
        "objectives": lab.objectives,
        "hints": lab.hints,
        "tools": lab.tools,
        "hostnames": lab.hostnames,
        "has_flag": bool(lab.flag_hash),
        "is_active": lab.is_active,
        "level_id": lab.level_id,
        "sort_order": lab.sort_order,
        "is_course_exclusive": getattr(lab, 'is_course_exclusive', False),
        "is_course_available": getattr(lab, 'is_course_available', False),
    }


# ==================== Lab Discovery ====================

@router.post("/labs/discover")
@limiter.limit("5/minute")
async def discover_labs(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Scan the /labs directory for lab.yaml files and sync to database."""
    import os, yaml, hashlib, json

    # Dev-only. On a shared-host / multi-instance setup the /labs dir holds
    # every instance's labs, so a bulk scan would ingest exercises that do not
    # belong to this deployment. Gate it off unless developer tools are on.
    if os.environ.get("OCR_DEV_TOOLS", "1").strip().lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="Exercise discovery is disabled on this deployment.")

    LABS_DIR = "/labs"
    if not os.path.exists(LABS_DIR):
        raise HTTPException(status_code=500, detail="Labs directory not found")

    # Get all tracks and levels
    tracks = {}
    levels = {}
    for track in db.query(Track).all():
        tracks[track.slug] = track.id
    for level in db.query(Level).all():
        levels[(level.track_id, level.level_number)] = level.id

    created = 0
    updated = 0
    errors = []

    for track_name in os.listdir(LABS_DIR):
        track_path = os.path.join(LABS_DIR, track_name)
        # Skip hidden and underscore-prefixed dirs (_archive, _pending, etc.)
        if not os.path.isdir(track_path) or track_name[:1] in ('.', '_'):
            continue

        for lab_dirname in sorted(os.listdir(track_path)):
            lab_path = os.path.join(track_path, lab_dirname)
            # Underscore prefix (e.g. _archive-*) marks a retired/disabled lab.
            if not os.path.isdir(lab_path) or lab_dirname[:1] in ('.', '_'):
                continue

            yaml_path = os.path.join(lab_path, 'lab.yaml')
            if not os.path.exists(yaml_path):
                continue

            # Parse slug: track-level-num-name  (e.g. linux-1-3-ssh-basics)
            # Also supports non-numeric names  (e.g. linux-midterm-2-full-penetration-test)
            parts = lab_dirname.split('-')
            if len(parts) < 3:
                errors.append(f"Cannot parse: {lab_dirname}")
                continue

            track_slug = parts[0].lower()
            try:
                level_num = int(parts[1])
                lab_num = int(parts[2])
            except ValueError:
                # Non-standard naming (e.g. midterm, capstone) — import without level
                level_num = None
                lab_num = 0

            track_id = tracks.get(track_slug)
            if not track_id:
                errors.append(f"Track '{track_slug}' not found: {lab_dirname}")
                continue

            level_id = None
            if level_num is not None:
                level_id = levels.get((track_id, level_num))
                if not level_id:
                    errors.append(f"Level {level_num} not found in '{track_slug}': {lab_dirname} (imported with no level)")
                    # Continue anyway with level_id=None — allows course-only labs and assessments

            try:
                with open(yaml_path, 'r') as f:
                    lab_data = yaml.safe_load(f)
            except Exception as e:
                errors.append(f"YAML error in {lab_dirname}: {str(e)}")
                continue

            # Read docker-compose.yml
            compose_path = os.path.join(lab_path, 'docker-compose.yml')
            compose_content = ""
            if os.path.exists(compose_path):
                try:
                    with open(compose_path, 'r') as f:
                        compose_content = f.read()
                except Exception:
                    pass

            # Hash flag
            flag = lab_data.get('flag', '')
            flag_hash = hashlib.sha256(flag.encode()).hexdigest() if flag else None

            scenario = lab_data.get('scenario', '')
            scenario_brief = lab_data.get('scenario_brief', '')
            if not scenario_brief and scenario:
                scenario_brief = scenario[:150] + '...' if len(scenario) > 150 else scenario

            existing = db.query(Lab).filter(Lab.slug == lab_dirname).first()
            if existing:
                # NOTE: Do NOT overwrite visibility or created_by on existing labs.
                # Those are admin-managed fields, not derived from the filesystem.
                existing.name = lab_data.get('name', lab_dirname)
                existing.description = lab_data.get('description', '')
                existing.scenario = scenario
                existing.scenario_brief = scenario_brief
                existing.difficulty = lab_data.get('difficulty', 'beginner')
                existing.category = lab_data.get('category', 'general')
                existing.duration_minutes = lab_data.get('duration_minutes', 60)
                existing.objectives = json.dumps(lab_data.get('objectives', []))
                existing.hints = json.dumps(lab_data.get('hints', []))
                existing.tools = json.dumps(lab_data.get('tools', []))
                existing.hostnames = json.dumps(lab_data.get('hostnames', []))
                existing.compose_file = compose_content
                existing.level_id = level_id
                existing.sort_order = lab_num
                if flag_hash:
                    existing.flag_hash = flag_hash
                if lab_data.get('workbook'):
                    existing.workbook = lab_data['workbook']
                updated += 1
            else:
                new_lab = Lab(
                    name=lab_data.get('name', lab_dirname),
                    slug=lab_dirname,
                    description=lab_data.get('description', ''),
                    scenario=scenario,
                    scenario_brief=scenario_brief,
                    difficulty=lab_data.get('difficulty', 'beginner'),
                    category=lab_data.get('category', 'general'),
                    duration_minutes=lab_data.get('duration_minutes', 60),
                    objectives=json.dumps(lab_data.get('objectives', [])),
                    hints=json.dumps(lab_data.get('hints', [])),
                    tools=json.dumps(lab_data.get('tools', [])),
                    hostnames=json.dumps(lab_data.get('hostnames', [])),
                    flag_hash=flag_hash,
                    compose_file=compose_content,
                    level_id=level_id,
                    sort_order=lab_num,
                    is_active=True,
                    visibility=lab_data.get('visibility', 'public') if lab_data.get('visibility') in ('draft', 'course', 'public') else 'public',
                    created_by=None,
                    workbook=lab_data.get('workbook'),
                )
                db.add(new_lab)
                created += 1

    db.commit()

    log_admin_action(
        action="LABS_DISCOVERED",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="labs",
        details={"created": created, "updated": updated, "errors": errors[:10]},
        ip_address=request.client.host if request.client else None
    )

    return {
        "message": f"Discovered {created + updated} labs ({created} new, {updated} updated)",
        "created": created,
        "updated": updated,
        "errors": errors
    }


# ==================== Activity / Audit Log ====================

@router.get("/activity")
async def get_activity_log(
    page: int = 1,
    per_page: int = 50,
    event_type: str = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get paginated activity log with optional event type and date range filters."""
    from app.services.activity import EVENT_LABELS
    from datetime import datetime as dt_cls

    query = db.query(ActivityEvent).order_by(ActivityEvent.created_at.desc())

    if event_type:
        query = query.filter(ActivityEvent.event_type == event_type)

    if start_date:
        try:
            sd = dt_cls.fromisoformat(start_date.replace('Z', '+00:00')).replace(tzinfo=None)
            query = query.filter(ActivityEvent.created_at >= sd)
        except (ValueError, TypeError):
            pass

    if end_date:
        try:
            ed = dt_cls.fromisoformat(end_date.replace('Z', '+00:00')).replace(tzinfo=None)
            query = query.filter(ActivityEvent.created_at <= ed)
        except (ValueError, TypeError):
            pass

    total = query.count()
    events = query.offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for e in events:
        # Look up actor username and role
        actor_name = None
        actor_role = None
        if e.actor_id:
            actor = db.query(User.username, User.role).filter(User.id == e.actor_id).first()
            if actor:
                actor_name = actor[0]
                actor_role = actor[1]
            else:
                actor_name = f"user#{e.actor_id}"

        result.append({
            "id": e.id,
            "event_type": e.event_type,
            "label": EVENT_LABELS.get(e.event_type, e.event_type),
            "actor_id": e.actor_id,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "target_label": e.target_label,
            "detail": e.detail,
            "ip_address": e.ip_address,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "events": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "event_types": list(EVENT_LABELS.keys()),
    }


# ==================== Container Logs ====================

@router.get("/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: int,
    tail: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get container logs for a lab session."""
    session = db.query(LabSession).filter(LabSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.lab:
        raise HTTPException(status_code=404, detail="Lab not found for session")

    project_name = f"lab_{session.user_id}_{session.lab.slug}"
    logs = {}

    try:
        import docker as docker_lib
        client = docker_lib.from_env()
        containers = client.containers.list(
            all=True,
            filters={"label": f"com.docker.compose.project={project_name}"}
        )

        for container in containers:
            short_name = container.name.replace(f"{project_name}-", "").replace(f"{project_name}_", "")
            try:
                log_output = container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
                logs[short_name] = {
                    "status": container.status,
                    "logs": log_output,
                }
            except Exception as e:
                logs[short_name] = {
                    "status": container.status,
                    "logs": f"Error reading logs: {e}",
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e}")

    return {
        "session_id": session_id,
        "project": project_name,
        "containers": logs,
    }


# ==================== Database Backup ====================

@router.post("/system/backup")
@limiter.limit("3/minute")
async def create_backup(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a database backup (pg_dump)."""
    import subprocess, os
    from urllib.parse import urlparse

    db_url = settings.DATABASE_URL
    parsed = urlparse(db_url)

    backup_dir = "/app/backups"
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/ocr_backup_{timestamp}.sql"

    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    try:
        result = subprocess.run(
            [
                "pg_dump",
                "-h", parsed.hostname or "db",
                "-p", str(parsed.port or 5432),
                "-U", parsed.username or "labuser",
                "-d", parsed.path.lstrip("/") or "labdb",
                "-f", backup_file,
                "--no-owner",
                "--no-acl",
                "--clean",
                "--if-exists",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise Exception(result.stderr or "pg_dump failed")

        size = os.path.getsize(backup_file)

        log_admin_action(
            action="DATABASE_BACKUP",
            admin_user_id=admin.id,
            admin_username=admin.username,
            target_type="database",
            details={"file": backup_file, "size_bytes": size},
            ip_address=request.client.host if request.client else None
        )

        return {
            "message": "Backup created successfully",
            "file": backup_file,
            "size_bytes": size,
            "timestamp": timestamp,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Backup timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")


@router.get("/system/activity-calendar")
async def activity_calendar(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Return daily event data for the backup heatmap (last 12 months).

    Each day includes change/backup counts and the latest timestamp for each,
    so the frontend can detect same-day backup-then-change ordering.
    """
    from sqlalchemy import func as sa_func, cast, Date

    one_year_ago = datetime.utcnow() - timedelta(days=365)

    change_types = [
        "user_registered", "user_approved", "course_enrolled",
        "USER_CREATED", "USER_UPDATED", "USER_DELETED",
        "LAB_ACTIVATED", "LAB_DEACTIVATED", "LAB_UPDATED",
        "SETTINGS_UPDATED", "COURSE_CREATED", "COURSE_UPDATED",
        "COURSE_DELETED", "ENROLLMENT_ADDED", "ENROLLMENT_REMOVED",
    ]

    rows = (
        db.query(
            cast(ActivityEvent.created_at, Date).label("day"),
            ActivityEvent.event_type,
            sa_func.count().label("cnt"),
            sa_func.max(ActivityEvent.created_at).label("latest"),
        )
        .filter(ActivityEvent.created_at >= one_year_ago)
        .group_by("day", ActivityEvent.event_type)
        .all()
    )

    def _empty():
        return {"changes": 0, "backups": 0,
                "last_change_ts": None, "last_backup_ts": None}

    days = {}
    for day, etype, cnt, latest in rows:
        key = day.isoformat()
        if key not in days:
            days[key] = _empty()
        ts = latest.isoformat() if latest else None
        if etype in ("DATABASE_BACKUP", "DATABASE_RESTORE",
                     "CREATE_BACKUP", "RESTORE_BACKUP"):
            days[key]["backups"] += cnt
            if ts and (not days[key]["last_backup_ts"] or ts > days[key]["last_backup_ts"]):
                days[key]["last_backup_ts"] = ts
        elif etype in change_types:
            days[key]["changes"] += cnt
            if ts and (not days[key]["last_change_ts"] or ts > days[key]["last_change_ts"]):
                days[key]["last_change_ts"] = ts

    backup_dir = "/app/backups"
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith(".sql"):
                mtime = os.path.getmtime(os.path.join(backup_dir, f))
                key = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                ts = datetime.fromtimestamp(mtime).isoformat()
                if key not in days:
                    days[key] = _empty()
                days[key]["backups"] = max(days[key]["backups"], 1)
                if not days[key]["last_backup_ts"] or ts > days[key]["last_backup_ts"]:
                    days[key]["last_backup_ts"] = ts

    return {"days": days}


@router.get("/system/backups")
async def list_backups(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List available database backups."""
    import os

    backup_dir = "/app/backups"
    if not os.path.exists(backup_dir):
        return {"backups": []}

    backups = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        if f.endswith(".sql"):
            path = os.path.join(backup_dir, f)
            backups.append({
                "filename": f,
                "size_bytes": os.path.getsize(path),
                "created": datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat(),
            })

    return {"backups": backups}


@router.get("/system/backups/{filename}")
async def download_backup(
    filename: str,
    admin: User = Depends(get_current_admin_user)
):
    """Download a specific backup file."""
    import os
    from fastapi.responses import FileResponse

    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = os.path.realpath(f"/app/backups/{filename}")
    if not path.startswith("/app/backups/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Backup not found")

    return FileResponse(path, media_type="application/sql", filename=filename)


@router.delete("/system/backups/{filename}")
@limiter.limit("10/minute")
async def delete_backup(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete a specific backup file."""
    import os

    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = os.path.realpath(f"/app/backups/{filename}")
    if not path.startswith("/app/backups/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Backup not found")

    os.remove(path)

    log_admin_action(
        action="DELETE_BACKUP",
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="database",
        details={"filename": filename},
        ip_address=request.client.host if request.client else None
    )

    return {"message": "Backup deleted"}


@router.post("/system/restore")
@limiter.limit("1/minute")
async def restore_backup(
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Restore the database from a backup file using psql."""
    import subprocess, os
    from urllib.parse import urlparse

    filename = body.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")

    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = os.path.realpath(f"/app/backups/{filename}")
    if not path.startswith("/app/backups/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Backup not found")

    db_url = settings.DATABASE_URL
    parsed = urlparse(db_url)

    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    try:
        result = subprocess.run(
            [
                "psql",
                "-h", parsed.hostname or "db",
                "-p", str(parsed.port or 5432),
                "-U", parsed.username or "labuser",
                "-d", parsed.path.lstrip("/") or "labdb",
                "-f", path,
                "--single-transaction",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            error_msg = result.stderr or "psql restore failed"
            raise Exception(error_msg)

        log_admin_action(
            action="DATABASE_RESTORE",
            admin_user_id=admin.id,
            admin_username=admin.username,
            target_type="database",
            details={"filename": filename, "status": "success"},
            ip_address=request.client.host if request.client else None
        )

        return {"message": f"Database restored from {filename}"}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Restore timed out after 5 minutes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")


@router.get("/system/status")
async def system_status(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Minimal, plain-language status for non-technical admins. Every item is
    derived from THIS install (the database, the entitlement, this instance's own
    disk) rather than the whole Docker daemon or hardcoded assumptions, so it
    never reports on content that is not loaded and does not drift between
    OCR-Lite and OCR-Enterprise. The deep firewall/network/security diagnostics
    live in the Advanced section, not here."""
    import shutil
    from sqlalchemy import text
    from app import entitlement

    items = []

    def add(name, status, detail):
        items.append({"name": name, "status": status, "detail": detail})

    # 1. Platform + 2. Database (single DB round-trip)
    try:
        db.execute(text("SELECT 1"))
        add("Platform", "ok", "The platform is running and the database is reachable.")
    except Exception:
        add("Platform", "error", "The database is not reachable. Students cannot sign in until this is fixed.")

    # 3. Disk space (this host)
    try:
        u = shutil.disk_usage("/labs")
        free_gb = round(u.free / (1024**3), 1)
        used_pct = round(u.used / u.total * 100)
        if used_pct >= 95:
            add("Disk space", "error", f"Only {free_gb} GB free ({used_pct}% used). Free up space now; labs may fail to start.")
        elif used_pct >= 85:
            add("Disk space", "warning", f"{free_gb} GB free ({used_pct}% used). Getting full; plan to free up space soon.")
        else:
            add("Disk space", "ok", f"{free_gb} GB free ({used_pct}% used).")
    except Exception:
        add("Disk space", "warning", "Could not read disk usage.")

    # 4. Active sessions (from this install's DB -- naturally scoped to this instance)
    try:
        from app.models import LabSession
        active = db.query(func.count(LabSession.id)).filter(LabSession.status == "running").scalar() or 0
        if active:
            add("Active sessions", "ok", f"{active} student lab session{'s' if active != 1 else ''} running right now.")
        else:
            add("Active sessions", "ok", "No lab sessions running right now.")
    except Exception:
        add("Active sessions", "warning", "Could not read active sessions.")

    # 5. Backups -- same dir the backup writer and the Backups tab use.
    try:
        import os
        bdir = os.environ.get("OCR_BACKUP_DIR", "/app/backups")
        newest = None
        if os.path.isdir(bdir):
            files = [os.path.join(bdir, f) for f in os.listdir(bdir) if f.endswith((".sql", ".gz", ".tar", ".zip"))]
            if files:
                newest = max(os.path.getmtime(f) for f in files)
        if newest is None:
            add("Backups", "warning", "No backup found yet. Create one from the Backups tab.")
        else:
            import time
            age_days = (time.time() - newest) / 86400
            if age_days <= 7:
                add("Backups", "ok", f"Last backup was {int(age_days)} day{'s' if int(age_days) != 1 else ''} ago.")
            else:
                add("Backups", "warning", f"Last backup was {int(age_days)} days ago. Consider making a fresh one.")
    except Exception:
        add("Backups", "warning", "Could not check backups.")

    # 6. Core secrets (rolled up; VPN/operator items live in Advanced)
    try:
        jwt = settings.JWT_SECRET or ""
        db_url = settings.DATABASE_URL or ""
        weak = []
        if len(jwt) < 32 or jwt in ("your-super-secret-jwt-key", "changeme"):
            weak.append("sign-in secret")
        if "labpass" in db_url or not db_url:
            weak.append("database password")
        if weak:
            add("Core secrets", "warning", f"Using a default {', '.join(weak)}. Fine for an isolated classroom, but rotate before internet use (see Advanced).")
        else:
            add("Core secrets", "ok", "Sign-in secret and database password are set.")
    except Exception:
        add("Core secrets", "warning", "Could not check secrets.")

    statuses = [i["status"] for i in items]
    overall = "error" if "error" in statuses else ("warning" if "warning" in statuses else "ok")
    return {"items": items, "overall": overall, "edition": entitlement.edition_name()}


@router.post("/stress-test")
async def start_stress_test(
    body: dict,
    admin: User = Depends(get_current_admin_user),
):
    """
    Launch a stress test in the background.

    Body:
        level: 1|2|3
        users: int (default 45)
        concurrent_spawns: int (default 5, level 3 only)
        lab_slug: str|null
    """
    # Check if a test is already running
    active_id, _ = _stress_find_active()
    if active_id:
        raise HTTPException(status_code=409, detail="A stress test is already running")

    level = body.get("level", 1)
    if level not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Level must be 1, 2, 3, or 4")

    num_users = body.get("users", 45)
    if num_users < 1 or num_users > 200:
        raise HTTPException(status_code=400, detail="Users must be between 1 and 200")

    concurrent_spawns = body.get("concurrent_spawns", 5)
    lab_slug = body.get("lab_slug") or None

    run_id = str(_uuid.uuid4())[:8]

    # Custom cancel flag that also checks for a sentinel file on disk.
    # This handles the multi-worker case: the cancel request may land on
    # a different uvicorn worker than the one running the test thread.
    class _CancelFlag:
        def __init__(self, rid):
            self._event = threading.Event()
            self._path = os.path.join(_STRESS_DIR, f"{rid}_cancel")
        def set(self):
            self._event.set()
        def is_set(self):
            if self._event.is_set():
                return True
            if os.path.exists(self._path):
                self._event.set()  # latch so file check is one-time
                return True
            return False

    cancel_flag = _CancelFlag(run_id)
    _stress_cancel_flags[run_id] = cancel_flag

    # Clean up old events/state files
    os.makedirs(_STRESS_DIR, exist_ok=True)
    for fname in os.listdir(_STRESS_DIR):
        try:
            os.remove(os.path.join(_STRESS_DIR, fname))
        except Exception:
            pass

    _stress_write_state(run_id, {
        "status": "running",
        "level": level,
        "users": num_users,
        "concurrent_spawns": concurrent_spawns,
        "lab_slug": lab_slug,
        "results": None,
        "started_at": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "admin_id": admin.id,
    })

    def event_callback(event):
        _stress_append_event(run_id, event)
        if event.get("type") == "complete":
            state = _stress_read_state(run_id)
            state["results"] = event.get("results")
            state["status"] = "cancelled" if event.get("results", {}).get("cancelled") else "completed"
            _stress_write_state(run_id, state)

    def _run_in_thread():
        try:
            from stress_test import run_stress_test
            result = run_stress_test(
                level=level,
                users=num_users,
                concurrent_spawns=concurrent_spawns,
                lab_slug=lab_slug,
                event_callback=event_callback,
                cancel_flag=cancel_flag,
            )
            state = _stress_read_state(run_id)
            if state.get("status") == "running":
                state["results"] = result
                state["status"] = "cancelled" if result.get("cancelled") else "completed"
                _stress_write_state(run_id, state)
        except Exception as exc:
            logger.error("Stress test error for run %s: %s", run_id, exc)
            state = _stress_read_state(run_id)
            state["status"] = "error"
            _stress_write_state(run_id, state)
            _stress_append_event(run_id, {
                "type": "line",
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "level": "error",
                "message": f"Stress test crashed: {str(exc)[:200]}",
            })
        finally:
            _stress_cancel_flags.pop(run_id, None)

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()

    return {"run_id": run_id, "level": level, "users": num_users, "status": "running"}


@router.get("/stress-test/active")
async def get_active_stress_test(
    admin: User = Depends(get_current_admin_user),
):
    """Return the currently active stress test (if any)."""
    rid, state = _stress_find_active()
    if rid and state:
        return {
            "run_id": rid,
            "status": state["status"],
            "level": state.get("level", 1),
            "users": state.get("users", 0),
            "started_at": state.get("started_at", ""),
            "event_count": _stress_count_events(rid),
        }
    return {"run_id": None, "status": "idle"}


@router.get("/stress-test/events/{run_id}")
async def get_stress_test_events(
    run_id: str,
    after: int = 0,
    admin: User = Depends(get_current_admin_user),
):
    """Return events for a stress test run starting after index `after`."""
    state = _stress_read_state(run_id)
    if not state:
        return {"run_id": run_id, "error": "not_found", "events": []}
    events = _stress_read_events(run_id, after)
    event_count = after + len(events)
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "level": state.get("level", 1),
        "users": state.get("users", 0),
        "event_count": event_count,
        "events": events,
        "results": state.get("results") if state.get("status") != "running" else None,
    }


@router.post("/stress-test/cancel")
async def cancel_stress_test(
    body: dict,
    admin: User = Depends(get_current_admin_user),
):
    """Cancel a running stress test."""
    run_id = body.get("run_id", "")
    # Try local cancel flag first (works if this is the worker that started it)
    flag = _stress_cancel_flags.get(run_id)
    if flag:
        flag.set()
        return {"cancelled": True, "run_id": run_id}
    # If not found locally, write a cancel sentinel file for the other worker
    cancel_path = os.path.join(_STRESS_DIR, f"{run_id}_cancel")
    try:
        os.makedirs(_STRESS_DIR, exist_ok=True)
        with open(cancel_path, "w") as f:
            f.write("cancel")
        return {"cancelled": True, "run_id": run_id}
    except Exception:
        return {"cancelled": False, "message": "Run not found or already completed"}


@router.post("/stress-test/report")
async def generate_stress_report_pdf(
    body: dict,
    admin: User = Depends(get_current_admin_user),
):
    """Generate a PDF report from stress test results."""
    from fastapi.responses import Response
    try:
        try:
            from app.services.stress_report import generate_stress_report
        except ImportError:
            raise HTTPException(status_code=404, detail="Stress reporting is not available in this edition")
        pdf_bytes = generate_stress_report(body)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="stress_test_report.pdf"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate stress test report: %s", e)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/stress-test/last-result")
async def get_last_stress_result(
    admin: User = Depends(get_current_admin_user),
):
    """Return the most recent completed/cancelled stress test results."""
    try:
        for fname in sorted(os.listdir(_STRESS_DIR), reverse=True):
            if fname.endswith("_state.json"):
                rid = fname.replace("_state.json", "")
                state = _stress_read_state(rid)
                if state.get("status") in ("completed", "cancelled") and state.get("results"):
                    return {
                        "run_id": rid,
                        "status": state["status"],
                        "level": state.get("level", 1),
                        "users": state.get("users", 0),
                        "started_at": state.get("started_at", ""),
                        "results": state["results"],
                    }
    except FileNotFoundError:
        pass
    return {"run_id": None, "status": "none", "results": None}


@router.post("/stress-test/cleanup")
async def stress_test_cleanup(
    admin: User = Depends(get_current_admin_user),
):
    """Clean up stress test users and data from the database."""
    try:
        from stress_test import cleanup_test_data
        messages = []

        def emit(msg, level="info"):
            messages.append(msg)

        cleanup_test_data(emit=emit)
        return {"success": True, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")





import json
import docker























































