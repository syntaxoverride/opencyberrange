"""
Exercises routes for learning tracks, progress tracking, and flag submission
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import hashlib
import hmac
import json
import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db, SessionLocal
from app.models import (
    User,
    Track,
    Level,
    Lab,
    LabCompletion,
    FlagAttempt,
    LabSession,
    Course,
    CourseEnrollment,
    CourseLabAssignment,
    CourseCompletionReset,
)
from app.auth import get_current_active_user
from app.services.docker_manager import DockerManager
from app.services.activity import log_activity, EventTypes
from app.services import settings_service



logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

docker_manager = DockerManager()


# ==================== Helper Functions ====================

def get_user_completions(db: Session, user_id: int) -> set:
    """Get set of completed lab IDs for user (only counts actual flag submissions)"""
    completions = db.query(LabCompletion.lab_id).filter(
        LabCompletion.user_id == user_id,
        LabCompletion.flag_submitted.isnot(None),
        LabCompletion.flag_submitted != ""
    ).all()
    return {c.lab_id for c in completions}


def is_lab_unlocked(db: Session, user_id: int, lab: Lab, completed_ids: set, user_is_admin: bool = False) -> bool:
    """Check if user can access this lab based on prerequisites"""
    
    # Admin users bypass all prerequisites
    if user_is_admin:
        return True
    
    if not lab.level_id:
        # Labs without levels are always unlocked
        return True

    level = lab.level

    # Non-sequential tracks unlock all labs regardless of completion
    if not getattr(level.track, 'sequential', True):
        return True

    track_levels = sorted(level.track.levels, key=lambda l: l.level_number)
    
    # Get all ACTIVE labs in this level, ordered (skip inactive labs for prerequisite checking)
    level_labs = sorted([l for l in level.labs if l.is_active], key=lambda l: l.sort_order)
    
    # If no active labs in level, unlock this lab (edge case)
    if not level_labs:
        return True
    
    # First active lab in first level is always unlocked
    if level == track_levels[0] and lab == level_labs[0]:
        return True
    
    # Find this lab's position in the active labs list
    lab_index = next((i for i, l in enumerate(level_labs) if l.id == lab.id), -1)
    
    # If lab not found in active labs, it might be inactive - unlock it for admins, lock for others
    if lab_index == -1:
        return False
    
    # If not first in level, previous ACTIVE lab must be completed
    if lab_index > 0:
        prev_lab = level_labs[lab_index - 1]
        if prev_lab.id not in completed_ids:
            return False
    
    # If first in level, check if previous level's ACTIVE labs are all complete
    if lab_index == 0:
        level_index = next((i for i, l in enumerate(track_levels) if l.id == level.id), -1)
        if level_index > 0:
            prev_level = track_levels[level_index - 1]
            # Only check active labs in previous level
            prev_level_active_lab_ids = {l.id for l in prev_level.labs if l.is_active}
            if prev_level_active_lab_ids and not prev_level_active_lab_ids.issubset(completed_ids):
                return False
    
    return True


def get_current_lab(db: Session, user_id: int, track: Track, completed_ids: set) -> Optional[int]:
    """Get the ID of the next lab to complete in a track"""
    for level in sorted(track.levels, key=lambda l: l.level_number):
        for lab in sorted(level.labs, key=lambda l: l.sort_order or 9999):
            if lab.id not in completed_ids:
                return lab.id
    return None


def get_accessible_exclusive_lab_ids(db: Session, user_id: int) -> set:
    """Get IDs of labs assigned to courses this user is enrolled in or instructs.

    Used for visibility checks on labs with visibility 'course' or 'pending_public',
    as well as legacy labs with is_course_exclusive=True.  The query is based purely
    on CourseLabAssignment + enrollment/ownership, so it works regardless of the
    visibility field on the lab itself.
    """
    now = datetime.now(timezone.utc)
    # Labs from courses the user is enrolled in
    enrolled_rows = db.query(CourseLabAssignment.lab_id).join(
        CourseEnrollment,
        CourseEnrollment.course_id == CourseLabAssignment.course_id,
    ).join(
        Course,
        Course.id == CourseLabAssignment.course_id,
    ).filter(
        CourseEnrollment.user_id == user_id,
        Course.end_date >= now,
        Course.is_active == True,
    ).all()
    # Labs from courses the user instructs
    instructed_rows = db.query(CourseLabAssignment.lab_id).join(
        Course,
        Course.id == CourseLabAssignment.course_id,
    ).filter(
        Course.instructor_id == user_id,
    ).all()
    return {r[0] for r in enrolled_rows} | {r[0] for r in instructed_rows}


def _is_lab_visible(lab, user, accessible_course_lab_ids: set, *, course_context: bool = False) -> bool:
    """Check if a lab should be visible to the current user.

    When *course_context* is False (the default — main exercise list), labs with
    visibility 'course' are hidden so they only appear inside their course view.
    When *course_context* is True, course-visibility labs are shown if the user
    is enrolled in a course that assigned them.

    Admins follow the same course-context rule: course-only labs stay out of
    the main exercise list for everyone. Admin management access is unaffected
    because the /admin/labs endpoints query Lab directly and never call this
    helper; admins still see inactive and draft labs here for testing.
    """
    vis = getattr(lab, 'visibility', 'public')
    if user.role == 'admin':
        if vis in ('course', 'pending_public') and not course_context:
            return False
        return True
    if not lab.is_active:
        return False
    if vis == 'public':
        return True
    if vis == 'draft':
        return getattr(lab, 'created_by', None) == user.id
    if vis in ('course', 'pending_public'):
        # In the main exercise list, hide course-only labs entirely
        if not course_context:
            return False
        if getattr(lab, 'created_by', None) == user.id:
            return True
        return lab.id in accessible_course_lab_ids
    return False


def check_rate_limit(db: Session, user_id: int, lab_id: int) -> bool:
    """Check if user is rate limited for flag submissions"""
    one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
    
    recent_attempts = db.query(func.count(FlagAttempt.id)).filter(
        FlagAttempt.user_id == user_id,
        FlagAttempt.lab_id == lab_id,
        FlagAttempt.attempted_at >= one_minute_ago
    ).scalar()
    
    return recent_attempts >= 10


def _wrong_flag_hint(submitted_flag: str, expected_hash: Optional[str]) -> str:
    """Build a format/case hint for an incorrect flag without leaking the answer.

    Hashes a few common mangles of the submission (case slips, missing OCR{...}
    wrapper, stray quotes) against the expected hash so the hint can point at
    the exact mistake. When none of the mangles match, a generic format
    reminder comes back instead. Only the submitted string is ever echoed or
    transformed; the correct flag never leaves the server.
    """
    generic = (
        "Flags are case-sensitive and must match exactly. Check the format "
        "shown in the workbook, usually OCR{...}, with no extra spaces or quotes."
    )
    if not expected_hash:
        return generic

    def _matches(candidate: str) -> bool:
        cand_hash = hashlib.sha256(candidate.encode()).hexdigest()
        return hmac.compare_digest(cand_hash, expected_hash)

    if _matches(submitted_flag.lower()) or _matches(submitted_flag.upper()):
        return "Check the letter case; flags are case-sensitive."
    if not (submitted_flag.startswith("OCR{") and submitted_flag.endswith("}")):
        if _matches("OCR{" + submitted_flag + "}"):
            return "Submit the complete flag, including the OCR{...} wrapper."
    unquoted = submitted_flag.strip("\"'")
    if unquoted != submitted_flag and _matches(unquoted):
        return "Drop the surrounding quotes and submit the bare flag."
    return generic


# ==================== Track Endpoints ====================

@router.get("/workbooks")
async def list_workbooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Workbook landing data: every shipped track that has a workbook, with the
    URL of its workbook root. Derived from lab.workbook fields, so it reflects
    exactly what this install ships (edition-correct with no extra config)."""
    from sqlalchemy import text
    # Per (track, wiki-root) counts. A track can span more than one wiki root
    # (e.g. a few leftover labs pointing at a renamed course wiki); pick the
    # root the most labs use so the tile links to the track's real workbook.
    rows = db.execute(text(
        "SELECT t.id, t.name, t.slug, t.sort_order, "
        "  (regexp_match(l.workbook, '^(wiki/(range|course)/[^/]+)/'))[1] AS root, "
        "  count(*) AS n "
        "FROM tracks t "
        "JOIN levels lv ON lv.track_id = t.id "
        "JOIN labs l ON l.level_id = lv.id "
        "WHERE l.workbook LIKE 'wiki/%' "
        "GROUP BY t.id, t.name, t.slug, t.sort_order, root"
    )).fetchall()

    by_track = {}
    for tid, name, slug, sort_order, root, n in rows:
        if not root:
            continue
        e = by_track.setdefault(tid, {
            "id": tid, "name": name, "slug": slug,
            "sort_order": sort_order if sort_order is not None else 10**9,
            "roots": {}, "total": 0,
        })
        e["roots"][root] = e["roots"].get(root, 0) + int(n)
        e["total"] += int(n)

    out = []
    for e in sorted(by_track.values(), key=lambda x: (x["sort_order"], x["name"])):
        if not e["roots"]:
            continue
        best = max(e["roots"].items(), key=lambda kv: kv[1])[0]
        out.append({
            "id": e["id"],
            "name": e["name"],
            "slug": e["slug"],
            "url": "/" + best + "/",
            "type": "course" if "/course/" in best else "range",
            "exercises": e["total"],
        })
    return {"workbooks": out}


@router.get("/tracks")
async def list_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all tracks with user progress"""
    tracks = db.query(Track).filter(Track.is_active == True).order_by(Track.sort_order).all()
    completed_ids = get_user_completions(db, current_user.id)
    accessible_course_lab_ids = get_accessible_exclusive_lab_ids(db, current_user.id)

    result = []
    for track in tracks:
        # Count only visible labs
        total_labs = sum(
            len([l for l in level.labs if _is_lab_visible(l, current_user, accessible_course_lab_ids)])
            for level in track.levels
        )
        completed_labs = sum(
            1 for level in track.levels
            for lab in level.labs
            if _is_lab_visible(lab, current_user, accessible_course_lab_ids) and lab.id in completed_ids
        )

        # Find current level (only considering visible labs)
        current_level = None
        for level in sorted(track.levels, key=lambda l: l.level_number):
            level_lab_ids = {l.id for l in level.labs if _is_lab_visible(l, current_user, accessible_course_lab_ids)}
            if level_lab_ids and not level_lab_ids.issubset(completed_ids):
                current_level = level.level_number
                break
        
        # Hide tracks where no labs are visible to this user
        if total_labs == 0:
            continue

        result.append({
            "id": track.id,
            "name": track.name,
            "slug": track.slug,
            "description": track.description,
            "icon": track.icon,
            "color": track.color,
            "total_labs": total_labs,
            "completed_labs": completed_labs,
            "current_level": current_level,
            "progress_percent": round(completed_labs / total_labs * 100) if total_labs > 0 else 0,
            "is_complete": completed_labs == total_labs and total_labs > 0
        })
    
    return {"tracks": result}


@router.get("/tracks/{track_slug}")
async def get_track(
    track_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get track details with levels and labs"""
    track = db.query(Track).options(
        joinedload(Track.levels).joinedload(Level.labs)
    ).filter(Track.slug == track_slug).first()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # is_active hides a track from the PUBLIC range browse list; it must not cut
    # a student off from labs their course assigns. The Course page deep-links
    # through here (/exercises?labId=..&courseId=.. resolves the lab's track and
    # redirects), so filtering is_active in the query made every course whose
    # track was hidden bounce back to the dashboard with no explanation.
    # Staff always pass; a learner passes when a course they are enrolled in
    # assigns a lab in this track.
    if not track.is_active:
        staff = bool(getattr(current_user, "is_admin", False)) or \
            getattr(current_user, "role", "") in ("admin", "instructor")
        if not staff:
            level_ids = [lv.id for lv in track.levels]
            has_course_access = False
            if level_ids:
                has_course_access = db.query(CourseLabAssignment.id).join(
                    Lab, Lab.id == CourseLabAssignment.lab_id
                ).join(
                    CourseEnrollment,
                    CourseEnrollment.course_id == CourseLabAssignment.course_id,
                ).filter(
                    Lab.level_id.in_(level_ids),
                    CourseEnrollment.user_id == current_user.id,
                ).first() is not None
            if not has_course_access:
                raise HTTPException(status_code=404, detail="Track not found")
    
    completed_ids = get_user_completions(db, current_user.id)
    current_lab_id = get_current_lab(db, current_user.id, track, completed_ids)
    accessible_course_lab_ids = get_accessible_exclusive_lab_ids(db, current_user.id)

    # Get active session if any
    active_session = db.query(LabSession).filter(
        LabSession.user_id == current_user.id,
        LabSession.status == "running"
    ).first()

    levels_data = []
    for level in sorted(track.levels, key=lambda l: l.level_number):
        labs_data = []
        for lab in sorted(level.labs, key=lambda l: l.sort_order or 9999):
            # Hide labs that aren't visible to this user
            if not _is_lab_visible(lab, current_user, accessible_course_lab_ids):
                continue
            
            is_completed = lab.id in completed_ids
            is_unlocked = is_lab_unlocked(db, current_user.id, lab, completed_ids, current_user.is_admin)
            is_current = lab.id == current_lab_id
            is_active = active_session and active_session.lab_id == lab.id
            
            # Parse JSON fields
            try:
                objectives = json.loads(lab.objectives) if lab.objectives else []
            except Exception:
                objectives = []
            
            try:
                tools = json.loads(lab.tools) if lab.tools else []
            except Exception:
                tools = []
            
            # Generate scenario_brief if not set (first 150 chars of scenario)
            scenario_brief = lab.scenario_brief if lab.scenario_brief else None
            if not scenario_brief and lab.scenario:
                scenario_brief = lab.scenario[:150] + "..." if len(lab.scenario) > 150 else lab.scenario
            
            labs_data.append({
                "id": lab.id,
                "name": lab.name,
                "slug": lab.slug,
                "description": lab.description,
                "scenario_brief": scenario_brief,
                "difficulty": lab.difficulty,
                # The SOC track routes Launch by category (soc-triage ->
                # /soc/triage, soc-ruletest -> /soc/ruletest, else /soc/hunt).
                # Omitting it made every socir exercise fall through to the hunt
                # console, so triage and ruletest scenarios 404'd as "Hunt
                # Unavailable".
                "category": lab.category,
                "duration_minutes": lab.duration_minutes,
                "objectives": objectives,
                "tools": tools,
                "is_completed": is_completed,
                "is_unlocked": is_unlocked,
                "is_current": is_current,
                "is_active": is_active,
                "is_lab_active": lab.is_active,  # Lab's active status (different from session active)
                "workbook": lab.workbook,
                "requires_kvm": bool(getattr(lab, 'requires_kvm', False)),
            })
        
        # Only include levels that have at least one lab (after filtering inactive labs)
        if len(labs_data) == 0:
            continue

        level_completed = sum(1 for l in labs_data if l["is_completed"])
        levels_data.append({
            "id": level.id,
            "level_number": level.level_number,
            "name": level.name,
            "description": level.description,
            "total_labs": len(labs_data),
            "completed_labs": level_completed,
            "is_complete": level_completed == len(labs_data),
            "labs": labs_data,
        })
    
    # Count only active labs from the filtered labs_data (or all for admins)
    total_labs = sum(len(level_data["labs"]) for level_data in levels_data)
    completed_labs = sum(
        level_data["completed_labs"] for level_data in levels_data
    )
    
    track_shared_containers = []

    return {
        "track": {
            "id": track.id,
            "name": track.name,
            "slug": track.slug,
            "description": track.description,
            "icon": track.icon,
            "color": track.color,
            "total_labs": total_labs,
            "completed_labs": completed_labs,
            "progress_percent": round(completed_labs / total_labs * 100) if total_labs > 0 else 0,
            "levels": levels_data,
            "shared_containers": track_shared_containers,
            "kvm_available": _track_kvm_available(levels_data),
        }
    }


def _track_kvm_available(levels_data) -> bool:
    """True unless a lab in this track needs KVM and the host lacks it.

    The probe only runs for tracks that contain shared-VM labs, so plain
    Docker tracks never pay the container-probe cost.
    """
    any_kvm_lab = any(
        lab.get("requires_kvm") for level in levels_data for lab in level["labs"]
    )
    if not any_kvm_lab:
        return True
    from app.services.docker_manager import host_kvm_available
    return host_kvm_available()


# ==================== Progress Endpoints ====================

@router.get("/progress")
async def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's overall progress across all tracks"""
    tracks = db.query(Track).options(
        joinedload(Track.levels).joinedload(Level.labs)
    ).filter(Track.is_active == True).all()
    
    completed_ids = get_user_completions(db, current_user.id)
    accessible_course_lab_ids = get_accessible_exclusive_lab_ids(db, current_user.id)

    total_labs = 0
    total_completed = 0
    track_progress = []

    for track in tracks:
        # Count only visible labs
        track_labs = sum(
            len([l for l in level.labs if _is_lab_visible(l, current_user, accessible_course_lab_ids)])
            for level in track.levels
        )
        track_completed = sum(
            1 for level in track.levels
            for lab in level.labs
            if _is_lab_visible(lab, current_user, accessible_course_lab_ids) and lab.id in completed_ids
        )
        total_labs += track_labs
        total_completed += track_completed
        
        track_progress.append({
            "track_id": track.id,
            "track_name": track.name,
            "track_slug": track.slug,
            "total_labs": track_labs,
            "completed_labs": track_completed,
            "progress_percent": round(track_completed / track_labs * 100) if track_labs > 0 else 0
        })
    
    # Get recent completions
    recent = db.query(LabCompletion).options(
        joinedload(LabCompletion.lab)
    ).filter(
        LabCompletion.user_id == current_user.id
    ).order_by(LabCompletion.completed_at.desc()).limit(5).all()
    
    return {
        "total_labs": total_labs,
        "total_completed": total_completed,
        "overall_progress": round(total_completed / total_labs * 100) if total_labs > 0 else 0,
        "tracks": track_progress,
        "recent_completions": [{
            "lab_name": c.lab.name,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None
        } for c in recent]
    }


# ==================== Flag Submission ====================

def _assert_lab_accessible(db: Session, user, lab):
    """Raise 404 if `lab` is not visible to `user` (mirrors get_lab_details).

    Endpoints that load a lab by client-supplied id -- hints, flag submission --
    must apply the same visibility rules as the detail view, or a user can read
    hints for / brute-force flags against inactive, draft, or course-exclusive
    labs they are not entitled to see.
    """
    if not lab.is_active and not user.is_admin:
        raise HTTPException(status_code=404, detail="Lab not found")
    vis = getattr(lab, 'visibility', 'public')
    is_legacy_exclusive = getattr(lab, 'is_course_exclusive', False)
    if not user.is_admin and (vis in ('course', 'pending_public') or is_legacy_exclusive):
        if lab.id not in get_accessible_exclusive_lab_ids(db, user.id):
            raise HTTPException(status_code=404, detail="Lab not found")
    if not user.is_admin and vis == 'draft':
        if getattr(lab, 'created_by', None) != user.id:
            raise HTTPException(status_code=404, detail="Lab not found")


@router.post("/labs/{lab_id}/submit-flag")
@limiter.limit("10/minute")
async def submit_flag(
    request: Request,
    lab_id: int,
    flag_data: dict,
    background_tasks: BackgroundTasks,
    course_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit flag for validation. Pass course_id to allow resubmission for course credit."""

    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    _assert_lab_accessible(db, current_user, lab)

    # Get flag_hash directly from database to ensure we have the latest value
    from sqlalchemy import text
    flag_hash_result = db.execute(
        text("SELECT flag_hash FROM labs WHERE id = :lab_id"),
        {"lab_id": lab_id}
    ).fetchone()
    db_flag_hash = flag_hash_result[0] if flag_hash_result else None

    # Per-student flag: when the launch path seeded a unique flag into this
    # student's session containers, its hash lives on the LabSession row
    # (seeded_flag_hash) and becomes the grading key. The shared lab hash is
    # only the fallback, so a copied classmate flag will not grade correct on
    # a lab that seeds per-student values.
    seeded_row = db.query(LabSession.seeded_flag_hash).filter(
        LabSession.user_id == current_user.id,
        LabSession.lab_id == lab_id,
        LabSession.seeded_flag_hash.isnot(None),
    ).order_by(LabSession.started_at.desc()).first()
    expected_hash = seeded_row[0] if seeded_row else db_flag_hash

    # Check if already completed (only count completions with actual flag submissions)
    existing = db.query(LabCompletion).filter(
        LabCompletion.user_id == current_user.id,
        LabCompletion.lab_id == lab_id,
        LabCompletion.flag_submitted.isnot(None),
        LabCompletion.flag_submitted != ""
    ).first()

    # Course-aware resubmission: allow if completion is stale in course context
    allow_resubmit = False
    attempt_cutoff = None
    if existing and course_id is not None:
        from app.routers.courses import is_completed_in_course
        if not is_completed_in_course(db, current_user.id, course_id, lab_id):
            allow_resubmit = True
            # Determine cutoff: max(enrolled_at, latest_reset_at)
            enrollment = db.query(CourseEnrollment).filter(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.user_id == current_user.id,
            ).first()
            if enrollment:
                attempt_cutoff = enrollment.enrolled_at
                latest_reset = db.query(func.max(CourseCompletionReset.reset_at)).filter(
                    CourseCompletionReset.course_id == course_id,
                    CourseCompletionReset.user_id == current_user.id,
                    CourseCompletionReset.lab_id == lab_id,
                ).scalar()
                if latest_reset and latest_reset > attempt_cutoff:
                    attempt_cutoff = latest_reset

    if existing and not allow_resubmit:
        # Still auto-stop any running session to free resources
        session = db.query(LabSession).filter(
            LabSession.user_id == current_user.id,
            LabSession.lab_id == lab_id,
            LabSession.status.in_(["running", "starting"])
        ).first()
        if session:
            session.status = "stopped"
            db.commit()
            def _cleanup_already_completed(user_id: int, lab_slug: str):
                try:
                    docker_manager.destroy_lab_environment(user_id=user_id, lab_slug=lab_slug)
                    logger.info(f"Auto-stopped lab {lab_slug} after re-submission (already completed)")
                except Exception as e:
                    logger.warning(f"Failed to auto-stop lab {lab_slug}: {e}")
            background_tasks.add_task(_cleanup_already_completed, current_user.id, lab.slug)
        return {
            "correct": True,
            "message": "You have already completed this lab!",
            "already_completed": True
        }
    
    # Check rate limit
    if check_rate_limit(db, current_user.id, lab_id):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait 60 seconds."
        )
    
    # Get and normalize flag (strip whitespace only, preserve case)
    submitted_flag = flag_data.get("flag", "").strip()
    
    if not submitted_flag:
        raise HTTPException(status_code=400, detail="Flag is required")
    
    # Hash submitted flag
    submitted_hash = hashlib.sha256(submitted_flag.encode()).hexdigest()
    
    # Get attempt count (only count incorrect attempts to show accurate attempt number)
    attempt_query = db.query(func.count(FlagAttempt.id)).filter(
        FlagAttempt.user_id == current_user.id,
        FlagAttempt.lab_id == lab_id,
        FlagAttempt.is_correct == False
    )
    if attempt_cutoff:
        attempt_query = attempt_query.filter(FlagAttempt.attempted_at >= attempt_cutoff)
    attempt_count = attempt_query.scalar() + 1
    
    # Check if correct using constant-time comparison to prevent timing attacks
    is_correct = bool(expected_hash) and hmac.compare_digest(submitted_hash, expected_hash)
    
    # Log attempt
    attempt = FlagAttempt(
        user_id=current_user.id,
        lab_id=lab_id,
        flag_submitted=submitted_flag[:50],  # Truncate for storage
        is_correct=is_correct
    )
    db.add(attempt)
    
    if is_correct:
        # Time on task, measured from the FIRST session this user opened for
        # this lab rather than from whichever one happens to be running now.
        #
        # Measuring from the running session made the number reset every time a
        # student restarted a lab, so anyone who restarted before submitting
        # looked instantaneous: a student with four sessions and six hours of
        # windows on one exercise was reported at one minute, and a 33-second
        # gap between a restart and a submit truncated to a flat zero. Read as
        # engagement, that is not merely wrong, it invites an accusation.
        #
        # Restarts are ordinary. A session expires, a lab is reset, a student
        # comes back the next evening. None of that means the work restarted.
        # Sum the session windows rather than measuring wall clock from the
        # first start. Plain elapsed time counts the days a student spends away
        # between sittings: across this platform's completions it leaves the
        # median untouched at 18.7 minutes but drags the mean to 225, because a
        # handful of learners start on Monday and finish on Wednesday. Summing
        # windows gives the same median and a mean of 37.
        #
        # A window runs from a session's start to whichever comes first: the
        # next session's start, its own expiry, or now.
        sessions = db.query(LabSession).filter(
            LabSession.user_id == current_user.id,
            LabSession.lab_id == lab_id,
        ).order_by(LabSession.started_at.asc()).all()

        now_utc = datetime.now(timezone.utc)

        def _utc(value):
            return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value

        time_spent = None
        started_at_value = None
        total_seconds = 0.0
        for index, sess in enumerate(sessions):
            start = _utc(sess.started_at)
            if not start or start > now_utc:
                continue
            if started_at_value is None:
                started_at_value = sess.started_at
            candidates = [now_utc]
            expires = _utc(sess.expires_at)
            if expires:
                candidates.append(expires)
            if index + 1 < len(sessions):
                nxt = _utc(sessions[index + 1].started_at)
                if nxt:
                    candidates.append(nxt)
            end = min(candidates)
            if end > start:
                total_seconds += (end - start).total_seconds()

        if started_at_value is not None:
            # Round rather than truncate. int() turned every sub-minute solve
            # into a zero, which reads as "did no work" instead of "was quick".
            time_spent = max(1, round(total_seconds / 60))

        # Still elapsed time inside those windows, not attention: nothing
        # records when a session actually ends (stopped_at is set on 11 of 153
        # rows), so a student who walks away mid-session is counted as present.
        # An honest upper bound, which is what the column has always claimed.
        
        # Get hints used
        hints_query = db.query(func.count(FlagAttempt.id)).filter(
            FlagAttempt.user_id == current_user.id,
            FlagAttempt.lab_id == lab_id,
            FlagAttempt.flag_submitted.like("HINT%")
        )
        if attempt_cutoff:
            hints_query = hints_query.filter(FlagAttempt.attempted_at >= attempt_cutoff)
        hints_used = hints_query.scalar()
        
        # Check if there's an existing completion record (possibly with empty flag_submitted)
        # This can happen if hints created a placeholder completion
        existing_completion = db.query(LabCompletion).filter(
            LabCompletion.user_id == current_user.id,
            LabCompletion.lab_id == lab_id
        ).first()
        
        if existing_completion:
            # Update the existing completion record
            existing_completion.flag_submitted = submitted_flag
            existing_completion.attempts = attempt_count
            existing_completion.hints_used = hints_used
            existing_completion.time_spent_minutes = time_spent
            # Keep the earliest start we have ever seen for this completion.
            if started_at_value and not existing_completion.started_at:
                existing_completion.started_at = started_at_value
            existing_completion.completed_at = datetime.now(timezone.utc)
        else:
            # Create new completion
            completion = LabCompletion(
                user_id=current_user.id,
                lab_id=lab_id,
                flag_submitted=submitted_flag,
                attempts=attempt_count,
                hints_used=hints_used,
                time_spent_minutes=time_spent,
                # Record it, so the number above can be checked rather than
                # trusted. It was NULL on 73 of 79 completions.
                started_at=started_at_value
            )
            db.add(completion)
        db.commit()

        # Check and award course achievements in background
        # (uses its own DB session since the request session closes after response)
        def _run_achievement_check(user_id: int, lab_id_inner: int):
            bg_db = SessionLocal()
            try:
                from app.services.achievements import check_achievements
                check_achievements(bg_db, user_id, lab_id_inner)
            except Exception as e:
                logger.warning(f"Achievement check failed for user {user_id} lab {lab_id_inner}: {e}")
            finally:
                bg_db.close()

        background_tasks.add_task(_run_achievement_check, current_user.id, lab_id)

        # Auto-stop the lab to save resources (background — Docker cleanup can take 45s+).
        # session is bound only in the already-completed branch above, which
        # returns early; on a first correct submission it was never assigned, so
        # every first solve raised UnboundLocalError after the completion had
        # already committed -- a 500 and a "Submission failed" toast for a solve
        # that actually counted. Look it up here.
        session = db.query(LabSession).filter(
            LabSession.user_id == current_user.id,
            LabSession.lab_id == lab_id,
            LabSession.status.in_(["running", "starting"])
        ).first()
        if session:
            session.status = "stopped"
            db.commit()

            def _cleanup_lab(user_id: int, lab_slug: str):
                try:
                    docker_manager.destroy_lab_environment(
                        user_id=user_id, lab_slug=lab_slug,
                    )
                    logger.info(f"Auto-stopped lab {lab_slug} after flag submission")
                except Exception as e:
                    logger.warning(f"Failed to auto-stop lab {lab_slug}: {e}")

            background_tasks.add_task(_cleanup_lab, current_user.id, lab.slug)
        
        # Get next lab
        next_lab = None
        if lab.level:
            completed_ids = get_user_completions(db, current_user.id)
            next_lab_id = get_current_lab(db, current_user.id, lab.level.track, completed_ids)
            if next_lab_id:
                next = db.query(Lab).filter(Lab.id == next_lab_id).first()
                if next:
                    next_lab = {"id": next.id, "name": next.name, "slug": next.slug}
        
        logger.info(f"User {current_user.username} completed lab {lab.slug}")

        time_to_solve = None
        if session and session.started_at:
            delta = datetime.now(timezone.utc) - session.started_at.replace(tzinfo=timezone.utc)
            time_to_solve = int(delta.total_seconds())

        log_activity(db, EventTypes.FLAG_CORRECT,
                      actor_id=current_user.id, target_type="lab",
                      target_id=lab.id, target_label=lab.name,
                      detail={"time_to_solve_seconds": time_to_solve,
                              "attempts": attempt_count,
                              "hints_used": hints_used},
                      commit=False)
        log_activity(db, EventTypes.LAB_COMPLETED,
                      actor_id=current_user.id, target_type="lab",
                      target_id=lab.id, target_label=lab.name,
                      commit=False)
        db.commit()

        return {
            "correct": True,
            "message": "🎉 Congratulations! Flag accepted!",
            "next_lab": next_lab
        }
    else:
        log_activity(db, EventTypes.FLAG_INCORRECT,
                      actor_id=current_user.id, target_type="lab",
                      target_id=lab.id, target_label=lab.name,
                      commit=False)
        db.commit()

        # Provide feedback based on attempt count
        hint_available = attempt_count >= 3

        format_hint = _wrong_flag_hint(submitted_flag, expected_hash)
        return {
            "correct": False,
            "message": f"Incorrect flag. Attempt #{attempt_count}. {format_hint}",
            "format_hint": format_hint,
            "attempts": attempt_count,
            "hint_available": hint_available
        }


# ==================== Hints ====================

@router.get("/labs/{lab_id}/hint")
async def get_hint(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get next hint for a lab (with time-based unlocking support)"""
    
    try:
        lab = db.query(Lab).filter(Lab.id == lab_id).first()
        if not lab:
            raise HTTPException(status_code=404, detail="Lab not found")
        _assert_lab_accessible(db, current_user, lab)

        # Parse hints (support both old string format and new object format)
        try:
            hints = json.loads(lab.hints) if lab.hints else []
        except Exception:
            hints = []

        if not hints:
            return {"hint": None, "message": "No hints available for this lab"}

        # Normalize hints to object format
        normalized_hints = []
        for hint in hints:
            if isinstance(hint, str):
                # Old format: plain string
                normalized_hints.append({
                    "text": hint,
                    "unlock_after_minutes": 0
                })
            else:
                # New format: object with text and unlock_after_minutes
                normalized_hints.append(hint)

        # Get lab start time
        lab_completion = db.query(LabCompletion).filter(
            LabCompletion.user_id == current_user.id,
            LabCompletion.lab_id == lab_id
        ).first()

        if lab_completion and lab_completion.started_at:
            lab_started_at = lab_completion.started_at
            # Ensure timezone-aware datetime
            if lab_started_at.tzinfo is None:
                lab_started_at = lab_started_at.replace(tzinfo=timezone.utc)
        else:
            # Fallback: use first flag attempt or hint request time
            first_attempt = db.query(FlagAttempt.attempted_at).filter(
                FlagAttempt.user_id == current_user.id,
                FlagAttempt.lab_id == lab_id
            ).order_by(FlagAttempt.attempted_at.asc()).first()

            if first_attempt:
                lab_started_at = first_attempt[0]
                # Ensure timezone-aware datetime
                if lab_started_at.tzinfo is None:
                    lab_started_at = lab_started_at.replace(tzinfo=timezone.utc)
            else:
                # First interaction - set start time now
                lab_started_at = datetime.now(timezone.utc)

            # Create or update LabCompletion record with started_at
            if not lab_completion:
                lab_completion = LabCompletion(
                    user_id=current_user.id,
                    lab_id=lab_id,
                    started_at=lab_started_at,
                    attempts=0,
                    hints_used=0
                )
                db.add(lab_completion)
            else:
                lab_completion.started_at = lab_started_at

            db.commit()

        # Calculate elapsed time in minutes
        minutes_elapsed = (datetime.now(timezone.utc) - lab_started_at).total_seconds() / 60

        # Filter hints available based on time
        available_hints = [
            h for h in normalized_hints
            if h.get("unlock_after_minutes", 0) <= minutes_elapsed
        ]

        if not available_hints:
            # No hints unlocked yet
            next_hint = normalized_hints[0]
            minutes_until_unlock = next_hint.get("unlock_after_minutes", 0) - minutes_elapsed
            seconds_until_unlock = max(0, int(minutes_until_unlock * 60))
            return {
                "hint": None,
                "message": f"First hint unlocks in {int(minutes_until_unlock)} minutes",
                "next_unlock_in_minutes": int(minutes_until_unlock),
                "next_unlock_in_seconds": seconds_until_unlock,
                "hints_available": 0,
                "hints_total": len(normalized_hints)
            }

        # Count hints already given (stored as HINT_REQUEST attempts)
        hints_given = db.query(func.count(FlagAttempt.id)).filter(
            FlagAttempt.user_id == current_user.id,
            FlagAttempt.lab_id == lab_id,
            FlagAttempt.flag_submitted.like("HINT_REQUEST%")
        ).scalar()

        # Check if all available hints have been given
        if hints_given >= len(available_hints):
            # All available hints have been revealed
            if len(available_hints) < len(normalized_hints):
                # There are more hints, but they're locked
                next_locked_hints = [h for h in normalized_hints if h.get("unlock_after_minutes", 0) > minutes_elapsed]
                if next_locked_hints:
                    next_unlock = min(h.get("unlock_after_minutes", 0) for h in next_locked_hints)
                    minutes_until_unlock = next_unlock - minutes_elapsed
                    seconds_until_unlock = max(0, int(minutes_until_unlock * 60))
                    return {
                        "hint": None,  # Don't return a hint, just the message
                        "message": f"All available hints have been revealed. Next hint unlocks in {int(minutes_until_unlock)} minutes",
                        "next_unlock_in_minutes": int(minutes_until_unlock),
                        "next_unlock_in_seconds": seconds_until_unlock,
                        "hints_available": len(available_hints),
                        "hints_revealed": hints_given,
                        "hints_total": len(normalized_hints)
                    }

            return {
                "hint": None,  # Don't return a hint
                "hint_number": len(available_hints),
                "hints_remaining": 0,
                "message": "No more hints available",
                "hints_available": len(available_hints),
                "hints_total": len(normalized_hints)
            }

        log_activity(db, EventTypes.HINT_USED,
                      actor_id=current_user.id, target_type="lab",
                      target_id=lab_id, target_label=lab.name,
                      detail={"hint_number": hints_given + 1},
                      commit=False)

        # Log hint request BEFORE returning (so we track it correctly)
        hint_request = FlagAttempt(
            user_id=current_user.id,
            lab_id=lab_id,
            flag_submitted=f"HINT_REQUEST_{hints_given + 1}",
            is_correct=False
        )
        db.add(hint_request)
        db.commit()

        # Calculate when next hint unlocks (if any)
        next_unlock_info = {}
        # After logging, hints_given + 1 is the current hint number
        current_hint_index = hints_given  # This is the index of the hint we're about to return
        
        if current_hint_index + 1 < len(available_hints):
            # More available hints to reveal immediately
            next_unlock_info["hints_remaining"] = len(available_hints) - current_hint_index - 1
        elif len(available_hints) < len(normalized_hints):
            # Next hint is time-locked
            next_locked_hints = [h for h in normalized_hints if h.get("unlock_after_minutes", 0) > minutes_elapsed]
            if next_locked_hints:
                next_unlock = min(h.get("unlock_after_minutes", 0) for h in next_locked_hints)
                minutes_until_unlock = next_unlock - minutes_elapsed
                seconds_until_unlock = max(0, int(minutes_until_unlock * 60))
                next_unlock_info["next_unlock_in_minutes"] = int(minutes_until_unlock)
                next_unlock_info["next_unlock_in_seconds"] = seconds_until_unlock

        current_hint = available_hints[current_hint_index]
        return {
            "hint": current_hint["text"],
            "hint_number": current_hint_index + 1,
            "point_cost": current_hint.get("point_cost", 0),
            "hints_available": len(available_hints),
            "hints_total": len(normalized_hints),
            **next_unlock_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hint for lab {lab_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve hint. Please try again or contact an administrator."
        )







# ==================== Lab Launch (Extended) ====================

@router.get("/labs/{lab_id}")
async def get_lab_details(
    lab_id: int,
    course_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed lab info for active lab view"""

    lab = db.query(Lab).options(
        joinedload(Lab.level).joinedload(Level.track)
    ).filter(Lab.id == lab_id).first()

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Hide inactive labs from non-admin users (admins can access all labs for testing)
    if not lab.is_active and not current_user.is_admin:
        raise HTTPException(
            status_code=404,
            detail="Lab not found"
        )

    # Block course/pending_public labs for non-enrolled users (also check legacy is_course_exclusive)
    vis = getattr(lab, 'visibility', 'public')
    is_legacy_exclusive = getattr(lab, 'is_course_exclusive', False)
    if not current_user.is_admin and (vis in ('course', 'pending_public') or is_legacy_exclusive):
        accessible = get_accessible_exclusive_lab_ids(db, current_user.id)
        if lab.id not in accessible:
            raise HTTPException(status_code=404, detail="Lab not found")
    # Block draft labs for non-owners
    if not current_user.is_admin and vis == 'draft':
        if getattr(lab, 'created_by', None) != current_user.id:
            raise HTTPException(status_code=404, detail="Lab not found")

    # Bypass sequential track locking when accessing via a course assignment
    course_bypass = False
    if not current_user.is_admin:
        if course_id:
            # Explicit course_id passed (from course view deep-link)
            enrolled = db.query(CourseEnrollment).filter(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.user_id == current_user.id,
            ).first()
            assigned = db.query(CourseLabAssignment).filter(
                CourseLabAssignment.course_id == course_id,
                CourseLabAssignment.lab_id == lab_id,
            ).first()
            if enrolled and assigned:
                course_bypass = True
        else:
            # No course_id passed — auto-detect for course-visibility labs
            # so students enrolled in a course can always open their assigned labs
            vis = getattr(lab, 'visibility', 'public')
            if vis in ('course', 'pending_public'):
                accessible = get_accessible_exclusive_lab_ids(db, current_user.id)
                if lab.id in accessible:
                    course_bypass = True

    completed_ids = get_user_completions(db, current_user.id)
    is_unlocked = is_lab_unlocked(db, current_user.id, lab, completed_ids, current_user.is_instructor)

    if not is_unlocked and not course_bypass and not current_user.is_instructor:
        raise HTTPException(
            status_code=403,
            detail="This lab is locked. Complete previous labs first."
        )
    
    # Get active session
    session = db.query(LabSession).filter(
        LabSession.user_id == current_user.id,
        LabSession.lab_id == lab_id,
        LabSession.status == "running"
    ).first()
    
    # Parse JSON fields
    try:
        objectives = json.loads(lab.objectives) if lab.objectives else []
    except Exception:
        objectives = []
    
    try:
        tools = json.loads(lab.tools) if lab.tools else []
    except Exception:
        tools = []
    
    try:
        hints = json.loads(lab.hints) if lab.hints else []
    except Exception:
        hints = []
    
    # Parse hostnames. When show_target_ips is set, surface the computed IP so
    # the scenario page can pre-fill the /etc/hosts block; otherwise the IP stays
    # hidden (ip=None) and the student discovers it by scanning.
    hostnames_data = []
    try:
        hostnames_raw = json.loads(lab.hostnames) if lab.hostnames else []
        if session and hostnames_raw:
            reveal_ips = bool(getattr(lab, 'show_target_ips', False) and session.network_subnet)
            subnet_base = ".".join(session.network_subnet.split("/")[0].split(".")[:3]) if reveal_ips else None
            for hostname_entry in hostnames_raw:
                hostname = hostname_entry.get('hostname', '')
                description = hostname_entry.get('description', '')
                offset = hostname_entry.get('ip_offset', '')
                ip = f"{subnet_base}.{offset}" if (subnet_base and offset) else None

                hostnames_data.append({
                    "hostname": hostname,
                    "description": description,
                    "ip": ip
                })
    except Exception as e:
        logger.warning(f"Failed to parse hostnames for lab {lab_id}: {e}")
        hostnames_data = []
    
    # Get hint count used (only if hints exist)
    hints_used = 0
    available_hints_count = len(hints)
    
    if hints:
        hints_used = db.query(func.count(FlagAttempt.id)).filter(
            FlagAttempt.user_id == current_user.id,
            FlagAttempt.lab_id == lab_id,
            FlagAttempt.flag_submitted.like("HINT_REQUEST%")
        ).scalar()
        
        # Calculate available hints based on time (only if hints have time-based unlocking)
        try:
            normalized_hints = []
            has_time_based = False
            for hint in hints:
                if isinstance(hint, str):
                    normalized_hints.append({"text": hint, "unlock_after_minutes": 0})
                else:
                    normalized_hints.append(hint)
                    if hint.get("unlock_after_minutes", 0) > 0:
                        has_time_based = True
            
            # Only calculate time-based availability if hints have unlock times
            if has_time_based:
                lab_completion = db.query(LabCompletion).filter(
                    LabCompletion.user_id == current_user.id,
                    LabCompletion.lab_id == lab_id
                ).first()
                
                if lab_completion and lab_completion.started_at:
                    lab_started_at = lab_completion.started_at
                    if lab_started_at.tzinfo is None:
                        lab_started_at = lab_started_at.replace(tzinfo=timezone.utc)
                    minutes_elapsed = (datetime.now(timezone.utc) - lab_started_at).total_seconds() / 60
                    available_hints_count = len([h for h in normalized_hints if h.get("unlock_after_minutes", 0) <= minutes_elapsed])
        except Exception:
            pass  # Fallback to total count if calculation fails
    
    # Generate scenario_brief if not set (first 150 chars of scenario)
    scenario_brief = lab.scenario_brief if lab.scenario_brief else None
    if not scenario_brief and lab.scenario:
        scenario_brief = lab.scenario[:150] + "..." if len(lab.scenario) > 150 else lab.scenario
    
    # Get all previously requested hints
    requested_hints = []
    if hints and hints_used > 0:
        try:
            # Normalize hints
            normalized_hints = []
            for hint in hints:
                if isinstance(hint, str):
                    normalized_hints.append({"text": hint, "unlock_after_minutes": 0})
                else:
                    normalized_hints.append(hint)
            
            # Calculate which hints were available (for time-based unlocking)
            available_hints_list = normalized_hints
            if any(h.get("unlock_after_minutes", 0) > 0 for h in normalized_hints):
                lab_completion = db.query(LabCompletion).filter(
                    LabCompletion.user_id == current_user.id,
                    LabCompletion.lab_id == lab_id
                ).first()
                
                if lab_completion and lab_completion.started_at:
                    lab_started_at = lab_completion.started_at
                    if lab_started_at.tzinfo is None:
                        lab_started_at = lab_started_at.replace(tzinfo=timezone.utc)
                    minutes_elapsed = (datetime.now(timezone.utc) - lab_started_at).total_seconds() / 60
                    available_hints_list = [h for h in normalized_hints if h.get("unlock_after_minutes", 0) <= minutes_elapsed]
            
            # Get the first N hints that were requested (hints are given in order)
            for i in range(min(hints_used, len(available_hints_list))):
                requested_hints.append({
                    "text": available_hints_list[i]["text"],
                    "number": i + 1
                })
        except Exception as e:
            logger.warning(f"Failed to reconstruct requested hints: {e}")
    
    # Compute target IPs when show_target_ips is set and session is active
    target_ips = []
    if getattr(lab, 'show_target_ips', False) and session and session.network_subnet:
        try:
            topo_nodes_raw = json.loads(lab.topology_nodes) if lab.topology_nodes else []
            # Parse subnet base: "10.100.6.0/24" -> "10.100.6"
            subnet_base = ".".join(session.network_subnet.split("/")[0].split(".")[:3])
            for node in topo_nodes_raw:
                offset = node.get("ip_offset", "")
                if offset:
                    target_ips.append({
                        "id": node.get("id", ""),
                        "label": node.get("label", ""),
                        "ip": f"{subnet_base}.{offset}"
                    })
        except Exception as e:
            logger.warning(f"Failed to compute target IPs for lab {lab_id}: {e}")

    return {
        "lab": {
            "id": lab.id,
            "name": lab.name,
            "slug": lab.slug,
            "description": lab.description,
            "scenario": lab.scenario if lab.scenario else None,
            "scenario_brief": scenario_brief,
            "difficulty": lab.difficulty,
            "category": lab.category,
            "duration_minutes": lab.duration_minutes,
            "objectives": objectives,
            "tools": tools,
            "hints_total": len(hints),
            "hints_available": available_hints_count,
            "hints_used": hints_used,
            "hint_point_costs": [h.get("point_cost", 0) for h in hints if isinstance(h, dict)],
            "requested_hints": requested_hints,  # All previously requested hints
            "is_completed": lab.id in completed_ids,
            "workbook": lab.workbook,
            "ics_techniques": json.loads(lab.ics_techniques) if getattr(lab, 'ics_techniques', None) else []
        },
        "track": {
            "name": lab.level.track.name if lab.level else None,
            "slug": lab.level.track.slug if lab.level else None,
            "color": lab.level.track.color if lab.level else None
        } if lab.level else None,
        "level": {
            "number": lab.level.level_number if lab.level else None,
            "name": lab.level.name if lab.level else None
        } if lab.level else None,
        "session": {
            "id": session.id,
            "status": session.status,
            "network_subnet": session.network_subnet,
            "rangebox_enabled": session.rangebox_enabled,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "expires_at": (session.expires_at.isoformat() + "Z") if session.expires_at else None,
            "time_remaining_seconds": max(0, int((session.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds())) if session.expires_at else 0,
            "duration_minutes": lab.duration_minutes or 120
        } if session else None,
        "hostnames": hostnames_data,
        "target_ips": target_ips,
    }
