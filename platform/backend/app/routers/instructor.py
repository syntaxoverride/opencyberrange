"""
Instructor-scoped API endpoints.
Instructors can view their own courses, browse labs, upload exercises,
and test their own exercises.
"""

import glob
import hashlib
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

import yaml

from app.database import get_db
from app.models import User, Course, CourseEnrollment, CourseLabAssignment, Lab, LabCompletion, Track, Level
from app.auth import get_current_instructor_user
from app.services.audit import log_admin_action, AuditActions
from app.services.docker_manager import get_track_directory_name
# Lab ZIP upload is an optional authoring capability; absent from editions
# that do not ship it (the upload endpoint 404s when this import fails).
try:
    from app.services.lab_upload import validate_and_extract_lab_zip, generate_slug, ZipValidationError
    _LAB_UPLOAD_AVAILABLE = True
except ImportError:
    _LAB_UPLOAD_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/courses")
async def list_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """List courses owned by the current instructor (admins see all)."""
    query = db.query(Course)
    if current_user.role != 'admin':
        query = query.filter(Course.instructor_id == current_user.id)

    courses = query.order_by(Course.created_at.desc()).all()
    result = []
    for c in courses:
        student_count = db.query(CourseEnrollment).filter(
            CourseEnrollment.course_id == c.id
        ).count()
        lab_count = db.query(CourseLabAssignment).filter(
            CourseLabAssignment.course_id == c.id
        ).count()
        instructor = db.query(User).filter(User.id == c.instructor_id).first()
        result.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "semester": c.semester,
            "description": c.description,
            "invite_code": c.invite_code,
            "instructor_id": c.instructor_id,
            "instructor_name": instructor.username if instructor else None,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "is_active": c.is_active,
            "is_archived": getattr(c, 'is_archived', False),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "student_count": student_count,
            "lab_count": lab_count,
        })
    return result


@router.get("/courses/{course_id}")
async def get_my_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Get detail for a single course (must own it, or be admin)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != 'admin' and course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this course")

    student_count = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course.id
    ).count()
    lab_count = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course.id
    ).count()
    instructor = db.query(User).filter(User.id == course.instructor_id).first()

    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "semester": course.semester,
        "description": course.description,
        "invite_code": course.invite_code,
        "instructor_id": course.instructor_id,
        "instructor_name": instructor.username if instructor else None,
        "start_date": course.start_date.isoformat() if course.start_date else None,
        "end_date": course.end_date.isoformat() if course.end_date else None,
        "is_active": course.is_active,
        "is_archived": getattr(course, 'is_archived', False),
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "student_count": student_count,
        "lab_count": lab_count,
    }


@router.get("/courses/{course_id}/enrollable-users")
async def list_enrollable_users(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """List students not yet enrolled in this course (for enrollment dropdown).
    Only course owner or admin can call this."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != 'admin' and course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this course")

    enrolled_user_ids = {
        e[0] for e in db.query(CourseEnrollment.user_id).filter(
            CourseEnrollment.course_id == course_id
        ).all()
    }

    query = db.query(User).filter(
        User.role == 'student',
        User.is_active == True,
    )
    if enrolled_user_ids:
        query = query.filter(User.id.notin_(enrolled_user_ids))
    users = query.order_by(User.username).all()

    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "student_id": u.student_id or "",
        }
        for u in users
    ]


@router.get("/labs")
async def list_available_labs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """List labs available for course assignment.

    Returns public and course-visible labs, plus any labs created by this instructor.
    Admins see all labs.
    """
    query = db.query(Lab).filter(Lab.is_active == True)
    if current_user.role != 'admin':
        # Instructor sees public + course + their own labs
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Lab.visibility.in_(['public', 'course']),
                Lab.created_by == current_user.id,
            )
        )

    labs = query.order_by(Lab.name).all()

    # Build labs list with track metadata
    lab_list = []
    track_counts = {}  # slug -> count
    for lab in labs:
        track = lab.level.track if lab.level and lab.level.track else None
        is_assessment = not track and getattr(lab, 'visibility', 'public') == 'course'
        t_name = track.name if track else ("Course Assessments" if is_assessment else "Uncategorized")
        t_slug = track.slug if track else ("assessments" if is_assessment else "uncategorized")
        t_color = track.color if track else ("#f59e0b" if is_assessment else "#64748b")

        track_counts[t_slug] = track_counts.get(t_slug, 0) + 1

        lab_list.append({
            "id": lab.id,
            "name": lab.name,
            "slug": lab.slug,
            "description": lab.description,
            "difficulty": lab.difficulty,
            "category": lab.category,
            "duration_minutes": lab.duration_minutes,
            "is_active": lab.is_active,
            "visibility": getattr(lab, 'visibility', 'public'),
            "created_by": getattr(lab, 'created_by', None),
            "track_name": t_name,
            "track_slug": t_slug,
            "track_color": t_color,
            "track_sort_order": track.sort_order if track else 999,
            "level_name": lab.level.name if lab.level else ("Assessments" if is_assessment else "Uncategorized"),
            "level_number": lab.level.level_number if lab.level else 999,
            "sort_order": lab.sort_order if hasattr(lab, 'sort_order') else 0,
        })

    # Build tracks summary (only tracks that have visible labs)
    all_tracks = db.query(Track).filter(Track.is_active == True).order_by(Track.sort_order).all()
    tracks_summary = []
    for t in all_tracks:
        count = track_counts.get(t.slug, 0)
        if count > 0:
            tracks_summary.append({
                "name": t.name,
                "slug": t.slug,
                "color": t.color,
                "icon": t.icon,
                "lab_count": count,
            })

    # Add "Course Assessments" pseudo-track if there are assessment labs
    assessment_count = track_counts.get("assessments", 0)
    if assessment_count > 0:
        tracks_summary.append({
            "name": "Course Assessments",
            "slug": "assessments",
            "color": "#f59e0b",
            "icon": None,
            "lab_count": assessment_count,
        })

    return {
        "tracks": tracks_summary,
        "labs": lab_list,
    }


@router.get("/labs/assignments")
async def lab_course_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Return a mapping of lab_id -> list of courses it's assigned to,
    scoped to the current instructor's courses (admins see all)."""
    course_query = db.query(Course)
    if current_user.role != 'admin':
        course_query = course_query.filter(Course.instructor_id == current_user.id)
    courses = course_query.all()
    course_map = {c.id: {"id": c.id, "name": c.name, "code": c.code} for c in courses}
    course_ids = list(course_map.keys())

    if not course_ids:
        return {}

    assignments = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id.in_(course_ids)
    ).all()

    result = {}
    for a in assignments:
        lab_id = str(a.lab_id)
        if lab_id not in result:
            result[lab_id] = []
        if a.course_id in course_map:
            result[lab_id].append(course_map[a.course_id])
    return result


@router.get("/stats")
async def instructor_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Dashboard stats for the current instructor."""
    # Courses scoped to this instructor (admins see all)
    course_query = db.query(Course)
    if current_user.role != 'admin':
        course_query = course_query.filter(Course.instructor_id == current_user.id)

    courses = course_query.all()
    course_ids = [c.id for c in courses]

    total_courses = len(courses)
    active_courses = sum(1 for c in courses if c.is_active and not getattr(c, 'is_archived', False))

    # Total enrolled students across instructor's courses
    total_students = 0
    if course_ids:
        total_students = db.query(CourseEnrollment).filter(
            CourseEnrollment.course_id.in_(course_ids)
        ).count()

    # Completion rate across assigned labs
    total_assigned = 0
    total_completed = 0
    if course_ids:
        assignments = db.query(CourseLabAssignment).filter(
            CourseLabAssignment.course_id.in_(course_ids)
        ).all()
        total_assigned = len(assignments)

        for assignment in assignments:
            enrollments = db.query(CourseEnrollment).filter(
                CourseEnrollment.course_id == assignment.course_id
            ).all()
            for enrollment in enrollments:
                completion = db.query(LabCompletion).filter(
                    LabCompletion.user_id == enrollment.user_id,
                    LabCompletion.lab_id == assignment.lab_id,
                    LabCompletion.flag_submitted.isnot(None),
                    LabCompletion.flag_submitted != "",
                ).first()
                if completion:
                    total_completed += 1

    return {
        "total_courses": total_courses,
        "active_courses": active_courses,
        "total_students": total_students,
        "total_assigned_labs": total_assigned,
        "total_completions": total_completed,
    }


# ──────────────────────────────────────────────────────────────
# Instructor Exercise Management
# ──────────────────────────────────────────────────────────────

def _get_track_directory_name(track_slug: str) -> str:
    """Resolve track slug to its directory name under /labs/."""
    # Import here to avoid circular imports at module level
    from app.services.docker_manager import get_track_directory_name
    return get_track_directory_name(track_slug)


@router.post("/labs/upload")
async def upload_lab_zip(
    request: Request,
    file: UploadFile = File(...),
    track: str = Form(...),
    level_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Upload a ZIP file containing a lab exercise and register it."""
    if not _LAB_UPLOAD_AVAILABLE:
        raise HTTPException(status_code=404, detail="Lab upload is not available in this edition")
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip file")

    # Cap the raw upload before reading it fully into memory (defense against a
    # huge / zip-bomb upload; the extractor also enforces uncompressed limits).
    MAX_ZIP_BYTES = 25 * 1024 * 1024   # 25 MB
    contents = await file.read(MAX_ZIP_BYTES + 1)
    if len(contents) > MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail=f"ZIP too large (limit {MAX_ZIP_BYTES // (1024 * 1024)} MB)")

    # Validate and extract ZIP (parses lab.yaml + compose inside)
    # We need to generate the slug first to determine the target directory
    # But we need lab.yaml to generate the slug... so do a two-pass:
    # 1) Parse ZIP in memory to get lab_data
    # 2) Generate slug
    # 3) Extract to disk

    import io, zipfile, yaml as yaml_lib

    # Quick pre-parse to get lab name for slug generation
    try:
        zf = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive")

    # Find lab.yaml (handling wrapper directory)
    entries = [n for n in zf.namelist() if not n.startswith("__MACOSX/")]
    top_level = set()
    for name in entries:
        top_level.add(name.split("/")[0])
    strip_prefix = ""
    if len(top_level) == 1:
        candidate = list(top_level)[0]
        if any(n.startswith(candidate + "/") for n in entries):
            strip_prefix = candidate + "/"

    yaml_path = strip_prefix + "lab.yaml"
    if yaml_path not in entries:
        raise HTTPException(status_code=400, detail="ZIP must contain lab.yaml")

    try:
        lab_data_preview = yaml_lib.safe_load(zf.read(yaml_path).decode("utf-8")) or {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid lab.yaml: {e}")

    lab_name = lab_data_preview.get("name", "")
    if not lab_name:
        raise HTTPException(status_code=400, detail="lab.yaml must have a 'name' field")

    # Generate slug
    try:
        slug = generate_slug(lab_name, track)
    except ZipValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check slug uniqueness
    existing = db.query(Lab).filter(Lab.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"An exercise with slug '{slug}' already exists. "
                   f"Choose a different name or delete the existing exercise first."
        )

    # Determine target directory
    try:
        track_dir = _get_track_directory_name(track)
    except Exception:
        # If track directory doesn't exist yet, create using capitalized name
        track_dir = track.capitalize()

    target_dir = f"/labs/{track_dir}/{slug}"

    # Full validation and extraction
    try:
        result = validate_and_extract_lab_zip(contents, target_dir)
    except ZipValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    lab_data = result["lab_data"]
    compose_content = result["compose_content"]

    # Hash the flag
    flag = lab_data.get("flag", "")
    flag_hash = hashlib.sha256(flag.encode()).hexdigest() if flag else None

    # Generate scenario brief
    scenario = lab_data.get("scenario", "")
    scenario_brief = (scenario[:150] + "...") if scenario and len(scenario) > 150 else scenario

    # Validate level_id if provided
    if level_id:
        from app.models import Level
        level = db.query(Level).filter(Level.id == level_id).first()
        if not level:
            # Clean up extracted files
            shutil.rmtree(target_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"Level {level_id} not found")

    # Create Lab record
    lab = Lab(
        name=lab_data.get("name", slug),
        slug=slug,
        description=lab_data.get("description", ""),
        scenario=scenario,
        scenario_brief=scenario_brief,
        difficulty=lab_data.get("difficulty", "beginner"),
        category=lab_data.get("category", "general"),
        duration_minutes=lab_data.get("duration_minutes", 60),
        level_id=level_id,
        compose_file=compose_content,
        objectives=json.dumps(lab_data.get("objectives", [])),
        hints=json.dumps(lab_data.get("hints", [])),
        tools=json.dumps(lab_data.get("tools", [])),
        hostnames=json.dumps(lab_data.get("hostnames", [])),
        flag_hash=flag_hash,
        visibility="draft",
        created_by=current_user.id,
        is_active=True,
        sort_order=0,
    )

    # Set workbook if present
    if lab_data.get("workbook"):
        lab.workbook = lab_data["workbook"]

    db.add(lab)
    db.commit()
    db.refresh(lab)

    logger.info(
        "Instructor %s (id=%d) uploaded lab '%s' (id=%d)",
        current_user.username, current_user.id, slug, lab.id,
    )

    # ── Bundled Workbook walkthrough detection ──
    # If the ZIP contains a walkthrough/ directory with markdown files,
    # extract them into the Workbook and rebuild the wiki automatically.
    walkthrough_result = None
    try:
        walkthrough_prefix = strip_prefix + "walkthrough/"
        walkthrough_files = [
            n for n in entries
            if n.startswith(walkthrough_prefix)
            and n.endswith(".md")
            and not n.startswith("__MACOSX/")
        ]
        if walkthrough_files:
            from app.services import workbook_builder

            # Derive chapter directory from track slug and exercise slug.
            # Convention: CH_<TRACK>_<Exercise_Name>
            # e.g. track="web", slug="web-sql-injection" -> CH_WEB_Sql_Injection
            short_name = slug
            if short_name.startswith(track.lower() + "-"):
                short_name = short_name[len(track) + 1:]
            chapter_suffix = "_".join(
                part.capitalize() for part in short_name.split("-") if part
            )
            chapter_dir = f"CH_{track.upper()}_{chapter_suffix}"

            # Extract walkthrough markdown files into the workbook docs dir
            import tempfile as _tempfile
            docs_target = os.path.join(workbook_builder.DOCS_DIR, chapter_dir)
            os.makedirs(docs_target, exist_ok=True)
            wt_extracted = []
            for wt_path in walkthrough_files:
                basename = os.path.basename(wt_path)
                if not basename:
                    continue
                safe_name = re.sub(r"[^\w.\-]", "_", basename)
                dest = os.path.join(docs_target, safe_name)
                with zf.open(wt_path) as src:
                    with open(dest, "wb") as dst:
                        dst.write(src.read())
                wt_extracted.append(safe_name)

            if wt_extracted:
                # Nav is per-track now (driven by the wiki manifest); rebuilding
                # the track wikis picks the new chapter up from its config.
                build_info = workbook_builder.build_wiki()
                walkthrough_result = {
                    "chapter_dir": chapter_dir,
                    "files_extracted": sorted(wt_extracted),
                    "build": build_info,
                }
                logger.info(
                    "Walkthrough bundled for '%s': %d files -> %s",
                    slug, len(wt_extracted), chapter_dir,
                )
    except Exception as exc:
        logger.warning(
            "Walkthrough processing failed for '%s' (exercise uploaded OK): %s",
            slug, exc, exc_info=True,
        )
        walkthrough_result = {"error": str(exc)}

    response = {
        "message": f"Exercise '{lab.name}' uploaded successfully",
        "id": lab.id,
        "slug": slug,
        "warnings": result["warnings"],
        "file_count": result["file_count"],
    }
    if walkthrough_result is not None:
        response["walkthrough"] = walkthrough_result

    return response


class UpdateLabRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scenario: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    objectives: Optional[str] = None
    hints: Optional[str] = None
    flag: Optional[str] = None
    level_id: Optional[int] = None  # Send explicit null to clear (uncategorize); omit key to leave unchanged


@router.get("/tracks-and-levels")
async def list_tracks_and_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Flat list of all tracks and their levels for the lab re-categorize picker."""
    tracks = db.query(Track).order_by(Track.sort_order, Track.name).all()
    out = []
    for t in tracks:
        levels = sorted(t.levels, key=lambda l: l.level_number)
        out.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "color": t.color,
            "is_active": t.is_active,
            "levels": [
                {"id": lv.id, "name": lv.name, "level_number": lv.level_number}
                for lv in levels
            ],
        })
    return {"tracks": out}


@router.put("/labs/{lab_id}")
async def update_own_lab(
    lab_id: int,
    payload: UpdateLabRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Update metadata on an exercise. Instructors can only edit their own."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if current_user.role != "admin" and lab.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own exercises")

    if payload.name is not None:
        lab.name = payload.name
    if payload.description is not None:
        lab.description = payload.description
    if payload.scenario is not None:
        lab.scenario = payload.scenario
        lab.scenario_brief = (payload.scenario[:150] + "...") if len(payload.scenario) > 150 else payload.scenario
    if payload.difficulty is not None:
        lab.difficulty = payload.difficulty
    if payload.category is not None:
        lab.category = payload.category
    if payload.duration_minutes is not None:
        lab.duration_minutes = payload.duration_minutes
    if payload.objectives is not None:
        lab.objectives = payload.objectives
    if payload.hints is not None:
        lab.hints = payload.hints
    if payload.flag is not None:
        lab.flag_hash = hashlib.sha256(payload.flag.encode()).hexdigest() if payload.flag else None

    # level_id: explicit null clears (moves to "Course Assessments" bucket); omit key to leave alone
    if 'level_id' in payload.model_fields_set:
        new_level_id = payload.level_id
        if new_level_id is not None:
            from app.models import Level
            if not db.query(Level).filter(Level.id == new_level_id).first():
                raise HTTPException(status_code=400, detail=f"Level {new_level_id} not found")
        lab.level_id = new_level_id

    db.commit()
    db.refresh(lab)

    return {"message": f"Exercise '{lab.name}' updated", "id": lab.id}


@router.delete("/labs/{lab_id}")
async def delete_own_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Delete an exercise (DB record + files on disk). Instructors can only delete their own."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if current_user.role != "admin" and lab.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own exercises")

    # Check for active sessions
    from app.models import LabSession
    active_sessions = db.query(LabSession).filter(
        LabSession.lab_id == lab_id,
        LabSession.ended_at.is_(None),
    ).count()
    if active_sessions > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {active_sessions} active session(s) exist for this exercise"
        )

    # Remove from disk
    try:
        track_slug = lab.slug.split("-")[0].lower()
        track_dir = _get_track_directory_name(track_slug)
        lab_dir = f"/labs/{track_dir}/{lab.slug}"
        if os.path.exists(lab_dir):
            shutil.rmtree(lab_dir)
            logger.info("Removed lab directory: %s", lab_dir)
    except Exception as e:
        logger.warning("Failed to remove lab directory for %s: %s", lab.slug, e)

    # Clean up test results
    try:
        from app.models import ExerciseTestResult
        db.query(ExerciseTestResult).filter(
            ExerciseTestResult.lab_slug == lab.slug
        ).delete()
    except Exception:
        pass  # Table might not exist

    # Clean up course assignments
    db.query(CourseLabAssignment).filter(
        CourseLabAssignment.lab_id == lab_id
    ).delete()

    slug = lab.slug
    db.delete(lab)
    db.commit()

    logger.info(
        "Instructor %s (id=%d) deleted lab '%s'",
        current_user.username, current_user.id, slug,
    )

    return {"message": f"Exercise '{slug}' deleted"}


class VisibilityUpdate(BaseModel):
    visibility: str


@router.put("/labs/{lab_id}/visibility")
async def update_lab_visibility(
    lab_id: int,
    body: VisibilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Change exercise visibility. Instructors: draft/course/pending_public only."""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if current_user.role != "admin" and lab.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only change visibility of your own exercises")

    new_vis = body.visibility
    allowed_instructor = {"draft", "course", "pending_public"}
    allowed_admin = {"draft", "course", "pending_public", "public"}

    if current_user.role == "admin":
        if new_vis not in allowed_admin:
            raise HTTPException(status_code=400, detail=f"Invalid visibility: {new_vis}")
    else:
        if new_vis not in allowed_instructor:
            raise HTTPException(
                status_code=403,
                detail=f"Instructors can set visibility to: {', '.join(sorted(allowed_instructor))}. "
                       f"To make an exercise public, set it to 'pending_public' for admin review."
            )

    old_vis = lab.visibility
    lab.visibility = new_vis

    # Sync deprecated boolean fields
    if new_vis == "course":
        lab.is_course_exclusive = True
        lab.is_course_available = True
    elif new_vis == "public":
        lab.is_course_exclusive = False
        lab.is_course_available = True
    elif new_vis == "draft":
        lab.is_course_exclusive = False
        lab.is_course_available = False

    db.commit()

    logger.info(
        "Instructor %s changed lab '%s' visibility: %s -> %s",
        current_user.username, lab.slug, old_vis, new_vis,
    )

    return {"message": f"Visibility changed to '{new_vis}'", "old": old_vis, "new": new_vis}


def _load_lab_yaml(lab_slug: str) -> dict:
    """Read /labs/{Track}/{slug}/lab.yaml.

    Deliberately a local copy rather than an import from the exercise tester:
    that router is an optional dev-tools module and is absent in editions that
    do not ship it, so importing it here would 500 this endpoint on a plain
    install. Returns {} for anything unreadable so a single bad file cannot
    take the endpoint down.
    """
    track_dir = get_track_directory_name(lab_slug.split("-")[0].lower())
    path = f"/labs/{track_dir}/{lab_slug}/lab.yaml"

    if not os.path.isfile(path):
        # The slug-to-track guess takes the text before the first dash, so a
        # two-word track loses half its name: every "windows-server-*" lab
        # resolves to "Windows" and misses its file in "Windows Server". The
        # slug directory is unique across tracks, so look it up directly rather
        # than trusting the guess.
        found = glob.glob(f"/labs/*/{lab_slug}/lab.yaml")
        if not found:
            return {}
        path = found[0]

    try:
        with open(path, "r") as fh:
            return yaml.safe_load(fh) or {}
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("Unreadable lab.yaml for %s (%s): %s", lab_slug, path, exc)
        return {}


@router.get("/labs/{lab_id}/flag")
async def reveal_lab_flag(
    lab_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Reveal a lab's answer flag to the instructor who teaches it.

    The database only ever stores the SHA256 (labs.flag_hash), so the plaintext
    has to come from the lab.yaml on disk. That is also why this endpoint
    reports drift instead of guessing: if the file no longer hashes to the
    column, the flag on disk is NOT what grading accepts, and showing it
    without saying so would send an instructor to argue a student's correct
    submission was wrong.

    Admins see any lab. An instructor sees a lab only when it is assigned to a
    course they own, which keeps one instructor account from being an answer
    key for all 455 labs.
    """
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if current_user.role != 'admin':
        teaches_it = (
            db.query(CourseLabAssignment.id)
            .join(Course, Course.id == CourseLabAssignment.course_id)
            .filter(
                CourseLabAssignment.lab_id == lab_id,
                Course.instructor_id == current_user.id,
            )
            .first()
        )
        if not teaches_it:
            raise HTTPException(
                status_code=403,
                detail="You can only view flags for exercises assigned to your own courses",
            )

    # Reading the answer key is worth a record even when it is the instructor's
    # own exercise, so a leak can be traced later.
    log_admin_action(
        action=AuditActions.LAB_FLAG_REVEALED,
        admin_user_id=current_user.id,
        admin_username=current_user.username,
        target_type="lab",
        target_id=lab.id,
        target_identifier=lab.slug,
        details={"role": current_user.role},
        ip_address=request.client.host if request.client else None,
    )

    flag = (_load_lab_yaml(lab.slug) or {}).get("flag") or ""
    if not flag:
        return {
            "lab_id": lab.id,
            "slug": lab.slug,
            "flag": None,
            "status": "missing",
            "message": "No flag is set in this exercise's lab.yaml.",
        }

    if lab.flag_hash and hashlib.sha256(flag.encode()).hexdigest() != lab.flag_hash:
        return {
            "lab_id": lab.id,
            "slug": lab.slug,
            "flag": flag,
            "status": "drift",
            "message": (
                "The flag in lab.yaml does not match the hash the platform grades "
                "against. Re-run exercise discovery for this lab before relying on it."
            ),
        }

    return {
        "lab_id": lab.id,
        "slug": lab.slug,
        "flag": flag,
        "status": "ok",
        "message": "",
    }
