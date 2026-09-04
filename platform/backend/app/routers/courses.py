"""
Course management routes: CRUD, enrollment, lab assignment, scoreboard,
achievements, and PDF reports.
"""

import io
import json
import os
import re
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import (
    User, Lab, LabCompletion, Course, CourseEnrollment,
    CourseLabAssignment, Achievement, CourseCompletionReset,
    Assignment, AssignmentLab, FlagAttempt,
)
from app.auth import get_current_active_user, get_current_instructor_user, get_current_admin_user
from app import entitlement
from app.schemas import (
    CourseCreate, CourseUpdate, CourseResponse, CourseJoinRequest,
    CourseLabAssignRequest, CourseLabReorderRequest, CourseLabUpdateRequest, AssignmentReorderRequest,
    BulkEnrollRequest,
    ScoreboardEntry, ScoreboardResponse, AchievementResponse,
    AssignmentCreate, AssignmentUpdate, AssignmentLabsRequest,
)
from app.services.achievements import ACHIEVEMENT_LABELS
from app.services.activity import log_activity, EventTypes
from app.services.course_wiki import rebuild_course_wiki

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Helpers ====================

def _generate_invite_code() -> str:
    return secrets.token_urlsafe(6)[:8]


WIKI_THEME_PALETTE = [
    "red", "pink", "purple", "deep-purple", "indigo", "blue",
    "light-blue", "cyan", "teal", "green", "light-green", "lime",
    "yellow", "amber", "orange", "deep-orange",
]


def _reserved_track_slugs() -> set:
    """Track slugs from the generated wiki registry (app/wiki_registry.json,
    emitted from wikis.yaml and shipped with the backend). A course wiki_slug
    must never collide with a track slug, or the /wiki/range/ and /wiki/course/
    namespaces clash (root cause of the original adpt collision). Fails open
    (empty set) if the registry is missing, so course creation is never blocked."""
    registry = os.path.join(os.path.dirname(__file__), "..", "wiki_registry.json")
    try:
        with open(os.path.abspath(registry)) as f:
            return set(json.load(f).get("tracks", {}).keys())
    except Exception:
        return set()


def _generate_wiki_slug(code: str, db: Session) -> str:
    """Generate a unique wiki slug from a course code (never colliding with a
    track slug or another course)."""
    base = re.sub(r'[^a-z0-9]', '', code.lower())
    if not base:
        base = "course"
    reserved = _reserved_track_slugs()
    slug = base
    suffix = 2
    while (slug in reserved
           or db.query(Course.id).filter(Course.wiki_slug == slug).first()):
        slug = f"{base}{suffix}"
        suffix += 1
    return slug


def _auto_assign_theme_color(db: Session) -> str:
    """Pick the next color from the palette, cycling through."""
    count = db.query(func.count(Course.id)).scalar() or 0
    return WIKI_THEME_PALETTE[count % len(WIKI_THEME_PALETTE)]


def _course_response(course: Course, db: Session) -> dict:
    """Build a CourseResponse dict from a Course model."""
    student_count = db.query(func.count(CourseEnrollment.id)).filter(
        CourseEnrollment.course_id == course.id
    ).scalar()
    lab_count = db.query(func.count(CourseLabAssignment.id)).filter(
        CourseLabAssignment.course_id == course.id
    ).scalar()
    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "semester": course.semester,
        "description": course.description,
        "invite_code": course.invite_code,
        "instructor_id": course.instructor_id,
        "instructor_name": course.instructor.username if course.instructor else None,
        "start_date": course.start_date,
        "end_date": course.end_date,
        "is_active": course.is_active,
        "is_archived": getattr(course, 'is_archived', False),
        "wiki_slug": getattr(course, 'wiki_slug', None),
        "wiki_theme_color": getattr(course, 'wiki_theme_color', 'blue'),
        "created_at": course.created_at,
        "student_count": student_count,
        "lab_count": lab_count,
    }


def _require_instructor(course: Course, user: User):
    if user.role == 'admin':
        return  # Admins can manage any course
    if course.instructor_id == user.id:
        return  # Course owner can manage their own course
    raise HTTPException(status_code=403, detail="Not authorized to manage this course")


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _ensure_scope_token(db: Session, enrollment: CourseEnrollment) -> str:
    """
    Assign a unique 4-char scope token to an enrollment if it doesn't already
    have one. Tokens are namespaced by course; tokens never collide with any
    OTHER active enrollment in the same course. Used by per-token-scoped
    tracks like ADPT (svc_kerb_<token>, etc.).

    Returns the token (existing or newly assigned).
    """
    if enrollment.scope_token:
        return enrollment.scope_token

    from sqlalchemy import text

    existing = {
        row[0] for row in db.execute(
            text("SELECT scope_token FROM course_enrollments "
                 "WHERE course_id = :cid AND scope_token IS NOT NULL"),
            {"cid": enrollment.course_id},
        ).fetchall()
        if row[0]
    }
    # 4-char lowercase alphanumeric, ~1.7M values; collision probability per
    # course negligible at any realistic class size.
    alphabet = "abcdefghijkmnpqrstuvwxyz23456789"  # avoid 0/o/1/l/i ambiguity
    for _ in range(100):
        candidate = "".join(secrets.choice(alphabet) for _ in range(4))
        if candidate not in existing:
            enrollment.scope_token = candidate
            return candidate
    raise HTTPException(status_code=500, detail="Could not allocate unique scope token after 100 attempts")


def get_course_completed_lab_ids(
    db: Session,
    user_id: int,
    course_id: int,
    assigned_lab_ids: set[int],
) -> set[int]:
    """Return lab IDs that count as completed within a course context.

    A lab is completed-in-course only if:
    - completed_at >= enrolled_at  AND
    - completed_at > latest reset_at (if any reset exists)
    """
    if not assigned_lab_ids:
        return set()

    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == user_id,
    ).first()
    if not enrollment:
        return set()

    enrolled_at = enrollment.enrolled_at

    completions = db.query(LabCompletion).filter(
        LabCompletion.user_id == user_id,
        LabCompletion.lab_id.in_(assigned_lab_ids),
        LabCompletion.flag_submitted.isnot(None),
        LabCompletion.flag_submitted != "",
    ).all()

    if not completions:
        return set()

    resets = db.query(CourseCompletionReset).filter(
        CourseCompletionReset.course_id == course_id,
        CourseCompletionReset.user_id == user_id,
    ).all()
    reset_map = {}
    for r in resets:
        if r.lab_id not in reset_map or r.reset_at > reset_map[r.lab_id]:
            reset_map[r.lab_id] = r.reset_at

    result = set()
    for c in completions:
        if c.completed_at is None:
            continue
        if c.completed_at < enrolled_at:
            continue
        latest_reset = reset_map.get(c.lab_id)
        if latest_reset and c.completed_at <= latest_reset:
            continue
        result.add(c.lab_id)

    return result


def is_completed_in_course(
    db: Session,
    user_id: int,
    course_id: int,
    lab_id: int,
) -> bool:
    """Check if a single lab counts as completed in course context."""
    return lab_id in get_course_completed_lab_ids(db, user_id, course_id, {lab_id})


def calculate_lab_score(
    completion: Optional[LabCompletion],
    lab: Lab,
    course_id: int,
    db: Session,
    first_blood_user_id: Optional[int] = None,
) -> int:
    """Calculate score for a single lab completion within a course.

    If first_blood_user_id is provided, it's used directly instead of querying.
    """
    if not completion or not completion.flag_submitted:
        return 0

    score = 100  # Base

    # Hint scoring: per-hint deduction if hints define point_cost, else flat bonus
    hint_deduction = 0
    if completion.hints_used > 0:
        try:
            hints = json.loads(lab.hints) if lab.hints else []
            costs = [h.get("point_cost", 0) for h in hints if isinstance(h, dict)]
            if any(c > 0 for c in costs):
                # Deduct point_cost for each hint used (in order)
                for i in range(min(completion.hints_used, len(costs))):
                    hint_deduction += costs[i]
        except Exception:
            pass

    if hint_deduction > 0:
        score -= hint_deduction
    elif completion.hints_used == 0:
        score += 25

    # First attempt bonus
    if completion.attempts == 1:
        score += 25

    # Speed bonus
    if completion.time_spent_minutes and lab.duration_minutes:
        ratio = completion.time_spent_minutes / lab.duration_minutes
        if ratio <= 0.25:
            score += 50
        elif ratio <= 0.50:
            score += 30
        elif ratio <= 0.75:
            score += 10

    # First blood bonus
    if first_blood_user_id is not None:
        if first_blood_user_id == completion.user_id:
            score += 50
    else:
        # Fallback: query DB (used when called outside scoreboard context)
        first = db.query(LabCompletion.user_id).join(
            CourseEnrollment,
            CourseEnrollment.user_id == LabCompletion.user_id,
        ).filter(
            CourseEnrollment.course_id == course_id,
            LabCompletion.lab_id == lab.id,
            LabCompletion.flag_submitted.isnot(None),
            LabCompletion.flag_submitted != "",
        ).order_by(LabCompletion.completed_at.asc()).first()
        if first and first[0] == completion.user_id:
            score += 50

    return score


# ==================== Course CRUD ====================

@router.post("/", status_code=201)
async def create_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create a new course. Admin only."""
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    # Entitlement cap: non-archived courses count against the edition limit
    course_limit = entitlement.active_course_limit()
    if course_limit is not None:
        active_count = db.query(Course).filter(Course.is_archived.isnot(True)).count()
        if active_count >= course_limit:
            edition = f"OCR-{entitlement.edition_name().capitalize()}"
            raise HTTPException(
                status_code=403,
                detail=(
                    f"{edition} includes {course_limit} active courses and this "
                    f"install has {active_count}. Archive a finished course to "
                    f"free a slot, or upgrade for unlimited courses (see LICENSING.md)."
                ),
            )

    owner_id = current_user.id
    if current_user.role == 'admin' and data.instructor_id is not None:
        target = db.query(User).filter(User.id == data.instructor_id).first()
        if not target or target.role not in ('instructor', 'admin'):
            raise HTTPException(status_code=400, detail="Selected instructor not found or does not have instructor/admin role")
        owner_id = target.id

    course = Course(
        name=data.name,
        code=data.code,
        semester=data.semester,
        description=data.description,
        invite_code=_generate_invite_code(),
        instructor_id=owner_id,
        start_date=data.start_date,
        end_date=data.end_date,
        is_active=False,
        wiki_slug=_generate_wiki_slug(data.code, db),
        wiki_theme_color=data.wiki_theme_color or _auto_assign_theme_color(db),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    logger.info(f"Course created: {course.code} by {current_user.username}")
    return _course_response(course, db)


@router.get("/")
async def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List courses. Admins see all; instructors see own courses; students see enrolled only."""
    if current_user.role == 'admin':
        courses = db.query(Course).order_by(Course.created_at.desc()).all()
    elif current_user.role == 'instructor':
        courses = db.query(Course).filter(
            Course.instructor_id == current_user.id,
        ).order_by(Course.created_at.desc()).all()
    else:
        courses = db.query(Course).join(
            CourseEnrollment,
            CourseEnrollment.course_id == Course.id,
        ).filter(
            CourseEnrollment.user_id == current_user.id,
            Course.is_active == True,
        ).order_by(Course.created_at.desc()).all()

    return {"courses": [_course_response(c, db) for c in courses]}


@router.get("/{course_id}")
async def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get course detail with assigned labs."""
    course = _get_course_or_404(db, course_id)

    # Must be admin, course owner, or enrolled
    is_instructor = (current_user.role == 'admin') or (course.instructor_id == current_user.id)
    is_enrolled = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == current_user.id,
    ).first() is not None

    if not is_instructor and not is_enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # Get assigned labs with completion status
    assignments = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id,
    ).order_by(CourseLabAssignment.sort_order).all()

    assigned_lab_ids = {a.lab_id for a in assignments}

    # Course-aware: only count completions after enrollment (+ respecting resets)
    if is_enrolled:
        completed_ids = get_course_completed_lab_ids(
            db, current_user.id, course_id, assigned_lab_ids,
        )
    else:
        # Admin viewing without enrollment — show global completions
        completed_ids = {
            r[0] for r in db.query(LabCompletion.lab_id).filter(
                LabCompletion.user_id == current_user.id,
                LabCompletion.flag_submitted.isnot(None),
                LabCompletion.flag_submitted != "",
            ).all()
        }

    # Find lab IDs that belong to locked or not-yet-open assignments (for students)
    locked_lab_ids: set[int] = set()
    if not is_instructor:
        now_utc = datetime.now(timezone.utc)
        all_asns = db.query(Assignment).filter(
            Assignment.course_id == course_id,
        ).all()
        for asn in all_asns:
            # Manually locked
            if asn.locked:
                for al in asn.assignment_labs:
                    locked_lab_ids.add(al.lab_id)
                continue
            # Not yet open (future start_date)
            if asn.start_date:
                sd = asn.start_date
                if sd.tzinfo is None:
                    sd = sd.replace(tzinfo=timezone.utc)
                if sd > now_utc:
                    for al in asn.assignment_labs:
                        locked_lab_ids.add(al.lab_id)

    labs = []
    for a in assignments:
        lab = a.lab
        if not lab:
            continue
        is_lab_locked = lab.id in locked_lab_ids
        track_name = lab.level.track.name if lab.level and lab.level.track else "Course Assessments"
        track_slug = lab.level.track.slug if lab.level and lab.level.track else None
        level_name = lab.level.name if lab.level else "Assessments"
        labs.append({
            "id": lab.id,
            "name": a.display_name or lab.name,
            "slug": lab.slug,
            "description": lab.description,
            "difficulty": lab.difficulty,
            "category": lab.category,
            "duration_minutes": lab.duration_minutes,
            "sort_order": a.sort_order,
            "is_completed": lab.id in completed_ids,
            "is_active": lab.is_active,
            "is_course_exclusive": lab.is_course_exclusive,
            "track_name": track_name,
            "track_slug": track_slug,
            "level_name": level_name,
            "display_name": a.display_name,
            "locked": is_lab_locked,
            "workbook": lab.workbook,
        })

    now = datetime.now(timezone.utc)
    course_end = course.end_date
    if course_end.tzinfo is None:
        course_end = course_end.replace(tzinfo=timezone.utc)
    is_ended = now > course_end

    return {
        "course": _course_response(course, db),
        "labs": labs,
        "is_instructor": is_instructor,
        "is_enrolled": is_enrolled,
        "is_ended": is_ended,
    }


@router.put("/{course_id}")
async def update_course(
    course_id: int,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Update a course. Must be the instructor."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    update_data = data.model_dump(exclude_unset=True)

    if 'instructor_id' in update_data:
        if current_user.role != 'admin':
            update_data.pop('instructor_id')
        else:
            new_instructor = db.query(User).filter(User.id == update_data['instructor_id']).first()
            if not new_instructor or new_instructor.role not in ('instructor', 'admin'):
                raise HTTPException(status_code=400, detail="Selected instructor not found or does not have instructor/admin role")

    for key, value in update_data.items():
        setattr(course, key, value)

    db.commit()
    db.refresh(course)
    return _course_response(course, db)


@router.delete("/{course_id}")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Delete a course. Must be the instructor."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)
    db.delete(course)
    db.commit()
    return {"message": "Course deleted"}


@router.post("/{course_id}/regenerate-invite")
async def regenerate_invite(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Regenerate the invite code for a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)
    course.invite_code = _generate_invite_code()
    db.commit()
    return {"invite_code": course.invite_code}


@router.post("/{course_id}/toggle-active")
async def toggle_course_active(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Toggle course active/inactive status."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)
    if getattr(course, 'is_archived', False):
        raise HTTPException(status_code=400, detail="Cannot toggle active status of an archived course. Unarchive first.")
    course.is_active = not course.is_active
    db.commit()
    db.refresh(course)
    return _course_response(course, db)


@router.post("/{course_id}/archive")
async def archive_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Archive a course. Sets is_archived=True and is_active=False."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)
    course.is_archived = True
    course.is_active = False
    db.commit()
    db.refresh(course)
    logger.info(f"Course {course.code} archived by {current_user.username}")
    return _course_response(course, db)


@router.post("/{course_id}/unarchive")
async def unarchive_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Unarchive a course. Sets is_archived=False but keeps is_active=False."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)
    course.is_archived = False
    db.commit()
    db.refresh(course)
    logger.info(f"Course {course.code} unarchived by {current_user.username}")
    return _course_response(course, db)


# ==================== Enrollment ====================

@router.post("/join")
async def join_course(
    data: CourseJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Join a course via invite code."""
    course = db.query(Course).filter(
        Course.invite_code == data.invite_code,
        Course.is_active == True,
        Course.is_archived == False,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Invalid invite code or course is not active")

    now = datetime.now(timezone.utc)
    end = course.end_date
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if now > end:
        raise HTTPException(status_code=403, detail="This course has ended")

    existing = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course.id,
        CourseEnrollment.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    enrollment = CourseEnrollment(
        course_id=course.id,
        user_id=current_user.id,
    )
    db.add(enrollment)
    db.flush()  # so _ensure_scope_token can see the row
    _ensure_scope_token(db, enrollment)
    db.commit()
    logger.info(f"User {current_user.username} enrolled in {course.code} (scope_token={enrollment.scope_token})")

    log_activity(db, EventTypes.COURSE_ENROLLED,
                  actor_id=current_user.id, target_type="course",
                  target_id=course.id, target_label=course.code)

    return {"message": f"Enrolled in {course.code}", "course_id": course.id}


@router.post("/{course_id}/enroll-bulk")
async def enroll_students_bulk(
    course_id: int,
    data: BulkEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Admin bulk-enrolls multiple students in a course."""
    course = _get_course_or_404(db, course_id)

    if not data.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")

    already_enrolled = {
        e.user_id for e in db.query(CourseEnrollment.user_id).filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id.in_(data.user_ids),
        ).all()
    }

    students = db.query(User).filter(
        User.id.in_(data.user_ids),
        User.role == "student",
        User.is_active == True,
    ).all()
    valid_ids = {s.id for s in students}

    enrolled = []
    skipped = []
    new_enrollments = []
    for uid in data.user_ids:
        if uid not in valid_ids:
            skipped.append({"user_id": uid, "reason": "not found or not an active student"})
        elif uid in already_enrolled:
            skipped.append({"user_id": uid, "reason": "already enrolled"})
        else:
            ce = CourseEnrollment(course_id=course_id, user_id=uid)
            db.add(ce)
            new_enrollments.append(ce)
            enrolled.append(uid)

    if enrolled:
        db.flush()
        for ce in new_enrollments:
            _ensure_scope_token(db, ce)
        db.commit()
        for uid in enrolled:
            log_activity(db, EventTypes.COURSE_ENROLLED,
                         actor_id=uid, target_type="course",
                         target_id=course_id, target_label=course.code)

    return {
        "enrolled_count": len(enrolled),
        "skipped_count": len(skipped),
        "skipped": skipped,
    }


@router.delete("/{course_id}/enroll/{user_id}")
async def remove_student(
    course_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Remove a student from a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == user_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not enrolled")

    db.delete(enrollment)
    db.commit()
    return {"message": "Student removed from course"}


@router.get("/{course_id}/students")
async def list_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """List enrolled students."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    enrollments = db.query(CourseEnrollment).options(
        joinedload(CourseEnrollment.user)
    ).filter(
        CourseEnrollment.course_id == course_id,
    ).all()

    students = []
    for e in enrollments:
        u = e.user
        students.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "student_id": u.student_id,
            "enrolled_at": e.enrolled_at,
        })
    return {"students": students}


# ==================== Lab Assignment ====================

@router.post("/{course_id}/labs")
async def assign_labs(
    course_id: int,
    data: CourseLabAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Assign labs to a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    # Get existing assignments
    existing_lab_ids = {
        a.lab_id for a in db.query(CourseLabAssignment).filter(
            CourseLabAssignment.course_id == course_id
        ).all()
    }

    # Get max sort_order
    max_order = db.query(func.max(CourseLabAssignment.sort_order)).filter(
        CourseLabAssignment.course_id == course_id
    ).scalar() or 0

    added = 0
    for lab_id in data.lab_ids:
        if lab_id in existing_lab_ids:
            continue
        lab = db.query(Lab).filter(Lab.id == lab_id).first()
        if not lab:
            continue
        max_order += 1
        db.add(CourseLabAssignment(
            course_id=course_id,
            lab_id=lab_id,
            sort_order=max_order,
        ))
        added += 1

    db.commit()
    rebuild_course_wiki(db, course)
    return {"message": f"{added} lab(s) assigned"}


@router.delete("/{course_id}/labs/{lab_id}")
async def remove_lab(
    course_id: int,
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Remove a lab from a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id,
        CourseLabAssignment.lab_id == lab_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Lab not assigned to this course")

    db.delete(assignment)
    db.commit()
    rebuild_course_wiki(db, course)
    return {"message": "Lab removed from course"}


@router.put("/{course_id}/labs/reorder")
async def reorder_labs(
    course_id: int,
    data: CourseLabReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Reorder labs in a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    for item in data.lab_order:
        assignment = db.query(CourseLabAssignment).filter(
            CourseLabAssignment.course_id == course_id,
            CourseLabAssignment.lab_id == item["lab_id"],
        ).first()
        if assignment:
            assignment.sort_order = item["sort_order"]

    db.commit()
    rebuild_course_wiki(db, course)
    return {"message": "Lab order updated"}


@router.put("/{course_id}/labs/{lab_id}")
async def update_course_lab(
    course_id: int,
    lab_id: int,
    data: CourseLabUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Update a course lab assignment (e.g. display_name). Instructor only."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id,
        CourseLabAssignment.lab_id == lab_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Lab not assigned to this course")

    if data.display_name is not None:
        # Empty string means reset to original lab name
        assignment.display_name = data.display_name if data.display_name.strip() else None

    db.commit()
    return {
        "message": "Course lab updated",
        "display_name": assignment.display_name,
        "lab_name": assignment.lab.name if assignment.lab else None,
    }


# ==================== Scoreboard ====================

@router.get("/{course_id}/scoreboard")
async def get_scoreboard(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get course scoreboard. Must be enrolled or instructor."""
    course = _get_course_or_404(db, course_id)

    # Check access: enrolled, admin, or course owner
    is_enrolled = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == current_user.id,
    ).first() is not None
    is_instructor = (current_user.role == 'admin') or (course.instructor_id == current_user.id)

    if not is_enrolled and not is_instructor:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # Get assigned labs
    assignments = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id,
    ).order_by(CourseLabAssignment.sort_order).all()

    labs = []
    lab_map = {}
    for a in assignments:
        lab = a.lab
        if lab:
            labs.append({"id": lab.id, "name": a.display_name or lab.name, "slug": lab.slug})
            lab_map[lab.id] = lab

    # Get enrolled students
    enrollments = db.query(CourseEnrollment).options(
        joinedload(CourseEnrollment.user)
    ).filter(
        CourseEnrollment.course_id == course_id,
    ).all()

    # Get all completions for enrolled users + assigned labs
    enrolled_user_ids = [e.user_id for e in enrollments]
    assigned_lab_ids_set = set(lab_map.keys())

    completions_raw = {}
    if enrolled_user_ids and assigned_lab_ids_set:
        rows = db.query(LabCompletion).filter(
            LabCompletion.user_id.in_(enrolled_user_ids),
            LabCompletion.lab_id.in_(assigned_lab_ids_set),
        ).all()
        for c in rows:
            completions_raw[(c.user_id, c.lab_id)] = c

    # Build enrollment map and reset map for course-aware filtering
    enrollment_map = {e.user_id: e.enrolled_at for e in enrollments}
    reset_map = {}  # (user_id, lab_id) -> latest reset_at
    if enrolled_user_ids:
        resets = db.query(CourseCompletionReset).filter(
            CourseCompletionReset.course_id == course_id,
            CourseCompletionReset.user_id.in_(enrolled_user_ids),
        ).all()
        for r in resets:
            key = (r.user_id, r.lab_id)
            if key not in reset_map or r.reset_at > reset_map[key]:
                reset_map[key] = r.reset_at

    def _is_valid_in_course(c: LabCompletion, uid: int) -> bool:
        """Check if a completion counts within this course."""
        if not c or not c.flag_submitted or not c.completed_at:
            return False
        enrolled_at = enrollment_map.get(uid)
        if not enrolled_at or c.completed_at < enrolled_at:
            return False
        latest_reset = reset_map.get((uid, c.lab_id))
        if latest_reset and c.completed_at <= latest_reset:
            return False
        return True

    # Filter completions to only course-valid ones
    completions = {}
    for key, c in completions_raw.items():
        if _is_valid_in_course(c, key[0]):
            completions[key] = c

    # Compute per-lab first blood from course-valid completions
    first_blood_map = {}  # lab_id -> user_id (earliest valid completer)
    for (uid, lid), c in completions.items():
        if lid not in first_blood_map or c.completed_at < completions[(first_blood_map[lid], lid)].completed_at:
            first_blood_map[lid] = uid

    # Get achievements for this course (both aggregate and per-lab)
    user_achievements = {}       # user_id -> [achievement_type, ...]
    user_lab_achievements = {}   # (user_id, lab_id) -> [achievement_type, ...]
    if enrolled_user_ids:
        ach_rows = db.query(Achievement).filter(
            Achievement.course_id == course_id,
            Achievement.user_id.in_(enrolled_user_ids),
        ).all()
        for a in ach_rows:
            user_achievements.setdefault(a.user_id, []).append(a.achievement_type)
            if a.lab_id is not None:
                user_lab_achievements.setdefault((a.user_id, a.lab_id), []).append(a.achievement_type)

    # Build scoreboard entries
    entries = []
    for enrollment in enrollments:
        user = enrollment.user
        total_score = 0
        labs_completed = 0
        lab_scores = {}

        for lab_id, lab in lab_map.items():
            completion = completions.get((user.id, lab_id))
            score = calculate_lab_score(
                completion, lab, course_id, db,
                first_blood_user_id=first_blood_map.get(lab_id),
            )
            total_score += score

            completed = completion is not None
            if completed:
                labs_completed += 1

            lab_scores[str(lab_id)] = {
                "score": score,
                "completed": completed,
                "time_minutes": completion.time_spent_minutes if completion else None,
                "attempts": completion.attempts if completion else 0,
                "hints_used": completion.hints_used if completion else 0,
                "achievements": user_lab_achievements.get((user.id, lab_id), []),
            }

        entries.append({
            "user_id": user.id,
            "username": user.username,
            "student_id": user.student_id,
            "total_score": total_score,
            "labs_completed": labs_completed,
            "achievements": list(set(user_achievements.get(user.id, []))),
            "lab_scores": lab_scores,
        })

    # Sort by total_score descending, then by labs_completed
    entries.sort(key=lambda e: (-e["total_score"], -e["labs_completed"]))

    # Add ranks
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return {
        "course": {"id": course.id, "name": course.name, "code": course.code},
        "labs": labs,
        "scoreboard": entries,
    }


# ==================== Achievements ====================

@router.get("/{course_id}/achievements")
async def list_achievements(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all achievements in a course."""
    course = _get_course_or_404(db, course_id)

    is_enrolled = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == current_user.id,
    ).first() is not None
    is_instructor = (current_user.role == 'admin') or (course.instructor_id == current_user.id)

    if not is_enrolled and not is_instructor:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    achievements = db.query(Achievement).options(
        joinedload(Achievement.user),
        joinedload(Achievement.lab),
    ).filter(
        Achievement.course_id == course_id,
    ).order_by(Achievement.awarded_at.desc()).all()

    # Build display_name map for course labs
    cla_rows = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id
    ).all()
    dn_map = {r.lab_id: r.display_name for r in cla_rows}

    result = []
    for a in achievements:
        lab_name = None
        if a.lab:
            lab_name = dn_map.get(a.lab_id) or a.lab.name
        result.append({
            "id": a.id,
            "user_id": a.user_id,
            "username": a.user.username if a.user else None,
            "achievement_type": a.achievement_type,
            "label": ACHIEVEMENT_LABELS.get(a.achievement_type, a.achievement_type),
            "lab_id": a.lab_id,
            "lab_name": lab_name,
            "awarded_at": a.awarded_at,
        })

    return {"achievements": result}


# ==================== Completion Reset ====================

@router.post("/{course_id}/labs/{lab_id}/reset/{user_id}")
async def reset_student_lab(
    course_id: int,
    lab_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Reset a student's lab completion within this course (admin only)."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    # Verify student is enrolled
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == user_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not enrolled in this course")

    # Verify lab is assigned
    assignment = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id,
        CourseLabAssignment.lab_id == lab_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Lab not assigned in this course")

    # Insert reset record
    db.add(CourseCompletionReset(
        course_id=course_id,
        user_id=user_id,
        lab_id=lab_id,
        reset_by=current_user.id,
    ))

    # Delete lab-specific achievements for this student+course+lab
    db.query(Achievement).filter(
        Achievement.course_id == course_id,
        Achievement.user_id == user_id,
        Achievement.lab_id == lab_id,
    ).delete()

    # Delete course-wide achievements (clean_sweep, streak) that may be invalidated
    db.query(Achievement).filter(
        Achievement.course_id == course_id,
        Achievement.user_id == user_id,
        Achievement.lab_id.is_(None),
    ).delete()

    db.commit()

    student = db.query(User).filter(User.id == user_id).first()
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    log_activity(db, EventTypes.ACHIEVEMENT_AWARDED,
                 actor_id=current_user.id, target_type="reset",
                 target_id=lab_id,
                 target_label=f"Reset {student.username if student else user_id} on {lab.name if lab else lab_id}",
                 commit=True)

    logger.info(f"Reset lab {lab_id} for user {user_id} in course {course_id} by {current_user.username}")
    return {"detail": "Lab completion reset for this course"}


# ==================== PDF Reports ====================

@router.get("/{course_id}/report")
async def class_report(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Generate PDF report for entire class."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    from app.services.pdf_report import generate_class_report

    course_dict = _build_course_dict(course)
    students_data = _build_all_students_data(db, course)

    pdf_bytes = generate_class_report(course_dict, students_data)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{course.code}_class.pdf"
        },
    )


@router.get("/{course_id}/report/{user_id}")
async def student_report(
    course_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Generate PDF report for a single student."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    # Verify student is enrolled
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == user_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not enrolled in this course")

    student = db.query(User).filter(User.id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="User not found")

    from app.services.pdf_report import generate_student_report

    course_dict = _build_course_dict(course)
    lab_scores, achievements = _build_student_scores(db, course, student)
    student_dict = {
        "username": student.username,
        "student_id": student.student_id,
        "email": student.email,
    }

    pdf_bytes = generate_student_report(student_dict, course_dict, lab_scores, achievements)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{course.code}_{student.username}.pdf"
        },
    )


# ==================== Report Helpers ====================

def _build_course_dict(course: Course) -> dict:
    return {
        "name": course.name,
        "code": course.code,
        "semester": course.semester,
        "instructor_name": course.instructor.username if course.instructor else "N/A",
        "start_date": course.start_date,
        "end_date": course.end_date,
    }


def _build_student_scores(
    db: Session, course: Course, student: User
) -> tuple:
    """Build lab scores and achievements for a student in a course."""
    assignments = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course.id,
    ).order_by(CourseLabAssignment.sort_order).all()

    # Build display_name map for course labs
    dn_map = {a.lab_id: a.display_name for a in assignments}
    # Pre-compute course-valid completions for this student
    assigned_lab_ids = {a.lab_id for a in assignments}
    valid_completed_ids = get_course_completed_lab_ids(
        db, student.id, course.id, assigned_lab_ids,
    )

    lab_scores = []
    for a in assignments:
        lab = a.lab
        if not lab:
            continue

        completion = db.query(LabCompletion).filter(
            LabCompletion.user_id == student.id,
            LabCompletion.lab_id == lab.id,
        ).first()

        has_flag = (completion and completion.flag_submitted
                    and completion.flag_submitted != ""
                    and lab.id in valid_completed_ids)

        score = calculate_lab_score(completion if has_flag else None, lab, course.id, db) if has_flag else 0

        lab_scores.append({
            "lab_id": lab.id,
            "lab_name": a.display_name or lab.name,
            "score": score,
            "max_score": 250,
            "attempts": completion.attempts if has_flag else 0,
            "hints_used": completion.hints_used if has_flag else 0,
            "time_minutes": completion.time_spent_minutes if has_flag else None,
            "completed_at": completion.completed_at if has_flag else None,
        })

    # Achievements
    ach_rows = db.query(Achievement).options(
        joinedload(Achievement.lab)
    ).filter(
        Achievement.course_id == course.id,
        Achievement.user_id == student.id,
    ).all()

    achievements = []
    for a in ach_rows:
        achievements.append({
            "type": a.achievement_type,
            "label": ACHIEVEMENT_LABELS.get(a.achievement_type, a.achievement_type),
            "lab_name": (dn_map.get(a.lab_id) or a.lab.name) if a.lab else None,
        })

    return lab_scores, achievements


def _build_all_students_data(db: Session, course: Course) -> list:
    """Build report data for all enrolled students."""
    enrollments = db.query(CourseEnrollment).options(
        joinedload(CourseEnrollment.user)
    ).filter(
        CourseEnrollment.course_id == course.id,
    ).all()

    students_data = []
    for e in enrollments:
        student = e.user
        lab_scores, achievements = _build_student_scores(db, course, student)
        students_data.append({
            "student": {
                "username": student.username,
                "student_id": student.student_id,
                "email": student.email,
            },
            "lab_scores": lab_scores,
            "achievements": achievements,
        })

    # Sort by username
    students_data.sort(key=lambda s: s["student"]["username"])
    return students_data


# ==================== Assignment CRUD ====================

@router.get("/{course_id}/assignments")
async def list_assignments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List assignments for a course with labs and completion stats."""
    course = _get_course_or_404(db, course_id)

    is_instructor = (current_user.role == 'admin') or (course.instructor_id == current_user.id)
    is_enrolled = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == current_user.id,
    ).first() is not None

    if not is_instructor and not is_enrolled:
        raise HTTPException(status_code=403, detail="Not authorized")

    assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id,
    ).order_by(Assignment.sort_order, Assignment.created_at).all()

    course_lab_rows = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id
    ).all()
    assigned_lab_ids = {a.lab_id for a in course_lab_rows}
    display_name_map = {a.lab_id: a.display_name for a in course_lab_rows}

    completed_ids = set()
    if not is_instructor:
        completed_ids = get_course_completed_lab_ids(
            db, current_user.id, course_id, assigned_lab_ids
        )

    result = []
    for asn in assignments:
        labs = []
        for al in asn.assignment_labs:
            lab = al.lab
            if not lab:
                continue
            lab_display = display_name_map.get(lab.id)
            labs.append({
                "id": lab.id,
                "name": lab_display or lab.name,
                "slug": lab.slug,
                "difficulty": lab.difficulty,
                "category": lab.category,
                "duration_minutes": lab.duration_minutes,
                "is_completed": lab.id in completed_ids,
                "sort_order": al.sort_order,
                "track_slug": lab.level.track.slug if lab.level and lab.level.track else None,
                "track_name": lab.level.track.name if lab.level and lab.level.track else "Course Assessments",
                "level_name": lab.level.name if lab.level else "Assessments",
            })
        # Determine if assignment is locked:
        #   1. Manually locked by instructor (asn.locked field), OR
        #   2. start_date is in the future (not yet open)
        is_locked = bool(asn.locked)
        not_yet_open = False
        if asn.start_date:
            start_dt = asn.start_date
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if start_dt > datetime.now(timezone.utc):
                not_yet_open = True

        # Determine due date status
        is_ended = False
        if asn.due_date:
            due_dt = asn.due_date
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            if due_dt < datetime.now(timezone.utc):
                is_ended = True

        # Students can see assignment info but not exercise details when locked/not open
        hide_content = (is_locked or not_yet_open) and not is_instructor

        result.append({
            "id": asn.id,
            "name": asn.name,
            "description": asn.description,
            "due_date": asn.due_date,
            "start_date": asn.start_date,
            "sort_order": asn.sort_order,
            "created_at": asn.created_at,
            "locked": is_locked,
            "not_yet_open": not_yet_open,
            "is_ended": is_ended,
            "lab_count": len(labs),
            "completed_count": 0 if hide_content else sum(1 for l in labs if l["is_completed"]),
            "labs": [] if hide_content else labs,
        })

    return {"assignments": result}


@router.post("/{course_id}/assignments", status_code=201)
async def create_assignment(
    course_id: int,
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Create a new assignment within a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    if data.start_date and data.due_date and data.due_date < data.start_date:
        raise HTTPException(status_code=400, detail="Due date cannot be before the availability date")

    max_order = db.query(func.max(Assignment.sort_order)).filter(
        Assignment.course_id == course_id
    ).scalar() or 0

    assignment = Assignment(
        course_id=course_id,
        name=data.name,
        description=data.description,
        due_date=data.due_date,
        start_date=data.start_date,
        locked=data.locked or False,
        sort_order=max_order + 1,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "id": assignment.id,
        "name": assignment.name,
        "description": assignment.description,
        "due_date": assignment.due_date,
        "start_date": assignment.start_date,
        "sort_order": assignment.sort_order,
        "created_at": assignment.created_at,
        "lab_count": 0,
        "completed_count": 0,
        "labs": [],
        "locked": assignment.locked,
        "not_yet_open": False,
        "is_ended": False,
    }


@router.put("/{course_id}/assignments/reorder")
async def reorder_assignments(
    course_id: int,
    data: AssignmentReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Reorder assignments in a course."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    for item in data.assignment_order:
        asn = db.query(Assignment).filter(
            Assignment.course_id == course_id,
            Assignment.id == item["id"],
        ).first()
        if asn:
            asn.sort_order = item["sort_order"]

    db.commit()
    return {"message": "Assignment order updated"}


@router.put("/{course_id}/assignments/{assignment_id}")
async def update_assignment(
    course_id: int,
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Update an assignment's name, description, or due date."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if data.name is not None:
        assignment.name = data.name
    if data.description is not None:
        assignment.description = data.description
    if data.due_date is not None:
        assignment.due_date = data.due_date
    if data.start_date is not None:
        assignment.start_date = data.start_date
    if data.locked is not None:
        assignment.locked = data.locked

    # Validate: due date must not be before start date
    effective_start = assignment.start_date
    effective_due = assignment.due_date
    if effective_start and effective_due and effective_due < effective_start:
        db.rollback()
        raise HTTPException(status_code=400, detail="Due date cannot be before the availability date")

    db.commit()
    return {"message": "Assignment updated", "locked": assignment.locked}


@router.delete("/{course_id}/assignments/{assignment_id}")
async def delete_assignment(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Delete an assignment (labs remain assigned to the course)."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": "Assignment deleted"}


# ==================== Assignment Lab Management ====================

@router.post("/{course_id}/assignments/{assignment_id}/labs")
async def add_labs_to_assignment(
    course_id: int,
    assignment_id: int,
    data: AssignmentLabsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Add labs to an assignment. Auto-assigns labs to the course if needed."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    course_lab_ids = {a.lab_id for a in db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course_id
    ).all()}

    existing = {al.lab_id for al in db.query(AssignmentLab).filter(
        AssignmentLab.assignment_id == assignment_id
    ).all()}

    max_order = db.query(func.max(AssignmentLab.sort_order)).filter(
        AssignmentLab.assignment_id == assignment_id
    ).scalar() or 0

    # Max sort_order for course lab assignments (for auto-assign)
    max_cla_order = db.query(func.coalesce(func.max(CourseLabAssignment.sort_order), 0)).filter(
        CourseLabAssignment.course_id == course_id
    ).scalar()

    added = 0
    for lab_id in data.lab_ids:
        # Auto-assign lab to course if not already there
        if lab_id not in course_lab_ids:
            max_cla_order += 1
            db.add(CourseLabAssignment(
                course_id=course_id,
                lab_id=lab_id,
                sort_order=max_cla_order,
            ))
            course_lab_ids.add(lab_id)
        if lab_id in existing:
            continue
        max_order += 1
        db.add(AssignmentLab(
            assignment_id=assignment_id,
            lab_id=lab_id,
            sort_order=max_order,
        ))
        added += 1

    db.commit()
    return {"message": f"{added} lab(s) added to assignment"}


@router.delete("/{course_id}/assignments/{assignment_id}/labs/{lab_id}")
async def remove_lab_from_assignment(
    course_id: int,
    assignment_id: int,
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Remove a lab from an assignment (lab stays assigned to the course)."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    # Scope the assignment to THIS course. Without this, an instructor who owns
    # any course could pass a foreign assignment_id and delete a lab from
    # another instructor's assignment.
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found in this course")

    al = db.query(AssignmentLab).filter(
        AssignmentLab.assignment_id == assignment_id,
        AssignmentLab.lab_id == lab_id,
    ).first()
    if not al:
        raise HTTPException(status_code=404, detail="Lab not in this assignment")

    db.delete(al)
    db.commit()
    return {"message": "Lab removed from assignment"}



# ==================== Assignment Reports ====================

@router.get("/{course_id}/assignments/{assignment_id}/report")
async def assignment_class_report(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Generate PDF class report scoped to a specific assignment."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment_lab_ids = {al.lab_id for al in db.query(AssignmentLab).filter(
        AssignmentLab.assignment_id == assignment_id
    ).all()}

    from app.services.pdf_report import generate_class_report

    course_dict = _build_course_dict(course)
    course_dict["name"] = f"{course.name} - {assignment.name}"

    all_data = _build_all_students_data(db, course)
    for entry in all_data:
        entry["lab_scores"] = [
            s for s in entry["lab_scores"] if s.get("lab_id") in assignment_lab_ids
        ]

    pdf_bytes = generate_class_report(course_dict, all_data)
    safe_name = assignment.name.replace(" ", "_")[:30]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{course.code}_{safe_name}.pdf"
        },
    )


@router.get("/{course_id}/assignments/{assignment_id}/report/{user_id}")
async def assignment_student_report(
    course_id: int,
    assignment_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Generate PDF student report scoped to a specific assignment."""
    course = _get_course_or_404(db, course_id)
    _require_instructor(course, current_user)

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == user_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student not enrolled in this course")

    student = db.query(User).filter(User.id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="User not found")

    assignment_lab_ids = {al.lab_id for al in db.query(AssignmentLab).filter(
        AssignmentLab.assignment_id == assignment_id
    ).all()}

    from app.services.pdf_report import generate_student_report

    course_dict = _build_course_dict(course)
    course_dict["name"] = f"{course.name} - {assignment.name}"

    lab_scores, achievements = _build_student_scores(db, course, student)
    lab_scores = [s for s in lab_scores if s.get("lab_id") in assignment_lab_ids]

    student_dict = {
        "username": student.username,
        "student_id": student.student_id,
        "email": student.email,
    }
    pdf_bytes = generate_student_report(student_dict, course_dict, lab_scores, achievements)
    safe_name = assignment.name.replace(" ", "_")[:30]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{course.code}_{safe_name}_{student.username}.pdf"
        },
    )


@router.get("/{course_id}/students/{user_id}/labs/{lab_id}/attempts")
async def get_student_lab_attempts(
    course_id: int,
    user_id: int,
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Every flag attempt one student made on one exercise, oldest first.

    The scoreboard shows an attempt count. A count cannot answer the questions
    that actually come up: was the first try right, how far apart were the
    tries, and what did they type. Auditing a suspicious-looking solve without
    that meant reading the database by hand.

    Restricted to the course's instructor and to admins. A student cannot read
    another student's attempts, and cannot read their own here either: the
    submitted strings for an exercise they may not have finished are in this
    payload, so enrolment is not enough.
    """
    course = _get_course_or_404(db, course_id)

    if current_user.role != 'admin' and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only this course's instructor can view a student's attempts",
        )

    # The lab has to belong to this course, otherwise the course id is just a
    # doorway to any exercise in the platform.
    assigned = db.query(CourseLabAssignment.id).filter(
        CourseLabAssignment.course_id == course_id,
        CourseLabAssignment.lab_id == lab_id,
    ).first()
    if not assigned:
        raise HTTPException(status_code=404, detail="Exercise is not assigned to this course")

    enrolled = db.query(CourseEnrollment.id).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == user_id,
    ).first()
    if not enrolled:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this course")

    rows = db.query(FlagAttempt).filter(
        FlagAttempt.user_id == user_id,
        FlagAttempt.lab_id == lab_id,
    ).order_by(FlagAttempt.attempted_at.asc()).all()

    attempts = []
    previous = None
    for row in rows:
        # Gap since the previous attempt. Reading timestamps and subtracting
        # them in your head is exactly the work this endpoint exists to remove.
        gap = None
        if previous is not None and row.attempted_at and previous.attempted_at:
            gap = int((row.attempted_at - previous.attempted_at).total_seconds())
        attempts.append({
            "attempted_at": row.attempted_at,
            "is_correct": bool(row.is_correct),
            "submitted": row.flag_submitted or "",
            "seconds_since_previous": gap,
        })
        previous = row

    return {
        "user_id": user_id,
        "lab_id": lab_id,
        "total": len(attempts),
        "correct": sum(1 for a in attempts if a["is_correct"]),
        "attempts": attempts,
    }
