"""
First-run setup wizard API.
These endpoints do NOT require authentication since no users exist yet.
Guarded by a "setup already complete" check to prevent misuse.
"""

import logging
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import User
from app.schemas import SetupRequest
from app.auth import get_password_hash, create_access_token
from app.services.settings_service import seed_defaults, get_setting, set_setting

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.get("/status")
async def setup_status(db: Session = Depends(get_db)):
    """Check if first-run setup has been completed. No auth required."""
    user_count = db.query(User).count()
    setting = get_setting(db, "setup_complete", "false")
    return {
        "setup_complete": setting == "true" or user_count > 0,
        "has_users": user_count > 0,
        # The wizard shows a token field when the server requires one.
        "setup_token_required": bool(os.environ.get("SETUP_TOKEN")),
    }


@router.get("/config")
async def public_config(db: Session = Depends(get_db)):
    """
    Return non-sensitive platform config for the frontend.
    No auth required — only exposes display-safe values.
    """
    from app.routers.modules import available_modules
    mods = [
        {"id": mid, "label": meta["label"], "description": meta["description"]}
        for mid, meta in available_modules().items()
    ]
    return {
        "available_modules": mods,
    }


@router.post("/complete")
@limiter.limit("3/minute")
async def complete_setup(
    request: Request,
    payload: SetupRequest,
    db: Session = Depends(get_db)
):
    """
    First-run setup. Creates admin user and seeds default settings.
    No auth required — guarded by 'no users exist' check.

    Uses a PostgreSQL advisory lock to prevent race conditions where two
    concurrent requests could both pass the "no users exist" check and
    create duplicate admin accounts.
    """
    # First-run setup is unauthenticated by necessity. When the server sets
    # SETUP_TOKEN (install-platform.sh generates one), require it so a fresh
    # internet-facing install cannot be admin-claimed by whoever reaches it
    # first. Constant-time compare. If SETUP_TOKEN is unset (isolated install),
    # the users>0 guard below is the control.
    expected_token = os.environ.get("SETUP_TOKEN")
    if expected_token:
        if not secrets.compare_digest(payload.setup_token or "", expected_token):
            raise HTTPException(status_code=403, detail="Invalid or missing setup token")

    # Acquire an advisory lock (ID 1) to serialize setup attempts.
    # pg_try_advisory_xact_lock returns immediately — if another transaction
    # already holds the lock we know setup is in progress and reject.
    lock_acquired = db.execute(text("SELECT pg_try_advisory_xact_lock(1)")).scalar()
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Setup is already in progress")

    # Guard: setup can only run once (checked inside the lock — no TOCTOU race)
    existing_users = db.query(User).count()
    if existing_users > 0:
        raise HTTPException(status_code=400, detail="Setup already completed — users exist")

    setting = get_setting(db, "setup_complete")
    if setting == "true":
        raise HTTPException(status_code=400, detail="Setup already completed")

    # Seed default platform settings
    seed_defaults(db)

    # Create admin user (pre-approved, active, admin)
    admin = User(
        username=payload.admin_username,
        email=payload.admin_email,
        hashed_password=get_password_hash(payload.admin_password),
        is_admin=True,
        role="admin",
        is_approved=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Apply optional settings
    if payload.require_approval is not None:
        set_setting(db, "require_approval", str(payload.require_approval).lower())

    # Mark setup as complete
    set_setting(db, "setup_complete", "true")

    # Seed the edition's prebuilt sample class(es) owned by this first admin.
    # (courses.instructor_id is NOT NULL, so this must run now, not at install.)
    try:
        from app.scripts.seed_prebuilt_class import seed_prebuilt_class
        made = seed_prebuilt_class(db, admin.id)
        if made:
            logger.info(f"Seeded prebuilt sample class(es): {made}")
    except Exception as e:
        logger.warning(f"Prebuilt class seeding skipped: {e}")

    logger.info(f"Setup complete — admin user '{admin.username}' created")

    # Generate JWT for immediate login
    token = create_access_token(
        data={"sub": admin.username},
        expires_delta=timedelta(hours=24)
    )

    return {
        "message": "Setup complete",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "role": "admin",
            "is_admin": True,
            "is_approved": True,
            "is_active": True,
        }
    }
