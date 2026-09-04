"""
Platform settings API router.
All endpoints require admin authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.auth import get_current_admin_user
from app.models import User
from app.schemas import SettingsBulkUpdate
from app.services import settings_service
from app.services.audit import log_admin_action, AuditActions

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/")
async def get_all_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Return all platform settings grouped by category. Secret values are masked."""
    return settings_service.get_all_settings(db)


@router.get("/{category}")
async def get_settings_by_category(
    category: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Return settings for a specific category."""
    valid_categories = ["general", "security", "labs", "vpn", "appearance", "modules"]
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {valid_categories}"
        )
    return settings_service.get_settings_by_category(db, category)


@router.put("/")
# Toggles persist on click, so a normal admin session writes one setting at a
# time instead of batching everything behind one Save. Ten a minute is below
# what flipping a few switches costs and would reject legitimate use. This is an
# authenticated admin-only route; the limit is a runaway guard, not a gate.
@limiter.limit("60/minute")
async def update_settings(
    request: Request,
    payload: SettingsBulkUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Bulk update platform settings."""
    # Filter out masked secret values so admins don't accidentally overwrite
    clean = {k: v for k, v in payload.settings.items() if v != "••••••••"}
    if not clean:
        return {"message": "No settings to update", "count": 0}

    count = settings_service.bulk_update_settings(db, clean)

    log_admin_action(
        action=AuditActions.SETTINGS_UPDATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="settings",
        details={"keys_updated": list(clean.keys()), "count": count},
        ip_address=request.client.host if request.client else None
    )

    return {"message": f"Updated {count} settings", "count": count}
