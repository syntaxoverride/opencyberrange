"""
Curriculum management API router (admin-only).
CRUD operations for tracks and levels.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.auth import get_current_admin_user
from app.models import User, Track, Level, Lab
from app.schemas import TrackCreate, TrackUpdate, LevelCreate, LevelUpdate, ReorderRequest
from app.services.audit import log_admin_action, AuditActions

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


# ==================== Tracks ====================

@router.get("/tracks")
async def list_tracks(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all tracks with level and lab counts."""
    tracks = db.query(Track).order_by(Track.sort_order).all()
    result = []
    for t in tracks:
        levels_data = []
        lab_count = 0
        for lev in sorted(t.levels, key=lambda l: l.level_number):
            lev_labs = len(lev.labs) if lev.labs else 0
            lab_count += lev_labs
            levels_data.append({
                "id": lev.id,
                "level_number": lev.level_number,
                "name": lev.name,
                "description": lev.description,
                "sort_order": lev.sort_order,
                "lab_count": lev_labs,
            })
        result.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "description": t.description,
            "icon": t.icon,
            "color": t.color,
            "sort_order": t.sort_order,
            "is_active": t.is_active,
            "level_count": len(t.levels),
            "lab_count": lab_count,
            "levels": levels_data,
        })
    return result


@router.post("/tracks")
@limiter.limit("10/minute")
async def create_track(
    request: Request,
    payload: TrackCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new track."""
    existing = db.query(Track).filter(Track.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Track slug already exists")

    max_order = db.query(func.max(Track.sort_order)).scalar() or 0
    track = Track(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        sort_order=max_order + 1,
        is_active=True,
    )
    db.add(track)
    db.commit()
    db.refresh(track)

    log_admin_action(
        action=AuditActions.TRACK_CREATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="track",
        target_id=track.id,
        target_identifier=track.slug,
        details={"name": track.name, "slug": track.slug},
        ip_address=request.client.host if request.client else None
    )

    return {"message": f"Track '{track.name}' created", "id": track.id}


@router.put("/tracks/reorder")
async def reorder_tracks(
    payload: ReorderRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update track sort order from an ordered list of IDs."""
    for idx, track_id in enumerate(payload.ordered_ids):
        track = db.query(Track).filter(Track.id == track_id).first()
        if track:
            track.sort_order = idx
    db.commit()
    return {"message": "Track order updated"}


@router.put("/tracks/{track_id}")
async def update_track(
    track_id: int,
    payload: TrackUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update a track."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    for field in ["name", "description", "icon", "color", "is_active"]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(track, field, val)

    db.commit()
    return {"message": f"Track '{track.name}' updated"}


@router.delete("/tracks/{track_id}")
async def delete_track(
    request: Request,
    track_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Hard-delete a track, its levels, and unassign any labs."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    track_name = track.name
    track_slug = track.slug

    # Collect level IDs belonging to this track
    level_ids = [lev.id for lev in track.levels]

    # Unassign labs from these levels (set level_id to NULL, don't delete labs)
    if level_ids:
        db.query(Lab).filter(Lab.level_id.in_(level_ids)).update(
            {Lab.level_id: None}, synchronize_session="fetch"
        )

    # Delete all levels in this track
    for level in track.levels:
        db.delete(level)

    # Delete the track itself
    db.delete(track)
    db.commit()

    log_admin_action(
        action=AuditActions.TRACK_DELETED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="track",
        target_id=track_id,
        target_identifier=track_slug,
        details={"name": track_name, "levels_removed": len(level_ids)},
        ip_address=request.client.host if request.client else None
    )

    return {"message": f"Track '{track_name}' and its {len(level_ids)} levels deleted"}


# ==================== Levels ====================

@router.post("/tracks/{track_id}/levels")
@limiter.limit("10/minute")
async def create_level(
    request: Request,
    track_id: int,
    payload: LevelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new level within a track."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    max_num = db.query(func.max(Level.level_number)).filter(
        Level.track_id == track_id
    ).scalar() or 0

    level = Level(
        track_id=track_id,
        level_number=max_num + 1,
        name=payload.name,
        description=payload.description,
        sort_order=max_num + 1,
    )
    db.add(level)
    db.commit()
    db.refresh(level)

    log_admin_action(
        action=AuditActions.LEVEL_CREATED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="level",
        target_id=level.id,
        target_identifier=f"{track.slug} L{level.level_number}",
        details={"track_id": track_id, "name": level.name},
        ip_address=request.client.host if request.client else None
    )

    return {"message": f"Level '{level.name}' created", "id": level.id, "level_number": level.level_number}


@router.put("/levels/{level_id}")
async def update_level(
    level_id: int,
    payload: LevelUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update a level."""
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    if payload.name is not None:
        level.name = payload.name
    if payload.description is not None:
        level.description = payload.description

    db.commit()
    return {"message": f"Level '{level.name}' updated"}


@router.delete("/levels/{level_id}")
async def delete_level(
    level_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete a level. Fails if labs are assigned to it."""
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    lab_count = db.query(Lab).filter(Lab.level_id == level_id).count()
    if lab_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete level with {lab_count} assigned labs. Reassign or remove labs first."
        )

    log_admin_action(
        action=AuditActions.LEVEL_DELETED,
        admin_user_id=admin.id,
        admin_username=admin.username,
        target_type="level",
        target_id=level.id,
        target_identifier=level.name,
    )

    db.delete(level)
    db.commit()
    return {"message": f"Level '{level.name}' deleted"}


@router.put("/tracks/{track_id}/levels/reorder")
async def reorder_levels(
    track_id: int,
    payload: ReorderRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Update level sort order and level numbers from an ordered list of IDs."""
    for idx, level_id in enumerate(payload.ordered_ids):
        level = db.query(Level).filter(Level.id == level_id, Level.track_id == track_id).first()
        if level:
            level.sort_order = idx
            level.level_number = idx + 1
    db.commit()
    return {"message": "Level order updated"}
