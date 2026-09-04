"""
Dashboard API routes for instructor and student dashboard views.
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text

from app.database import get_db
from app.models import (
    User, Lab, LabSession, LabCompletion, FlagAttempt, WireGuardConfig,
    Course, CourseEnrollment, CourseLabAssignment, ActivityEvent,
    Track, Level,
)
from app.auth import get_current_active_user, get_current_admin_user, get_current_instructor_user
from app.services.activity import EVENT_LABELS
from app.services.pdf_report import generate_dashboard_report

REPORT_LOCAL_TZ = ZoneInfo("America/Chicago")

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Helpers ====================

def _admin_user_ids(db: Session) -> set:
    """Return the set of user IDs with admin role (diagnostic actors)."""
    rows = db.query(User.id).filter(User.role == 'admin').all()
    return {r[0] for r in rows}


def _exclude_diagnostic(q, actor_col, db: Session):
    """Exclude admin-actor rows from a query."""
    admin_ids = _admin_user_ids(db)
    if admin_ids:
        q = q.filter(~actor_col.in_(admin_ids))
    return q


def _resolve_student_scope(db: Session, current_user: User,
                           course_id: Optional[int] = None,
                           user_id: Optional[int] = None):
    """Return a set of student IDs the current user is allowed to see,
    optionally narrowed by course_id and/or user_id.

    Returns None when no filtering should be applied (admin, no filters).
    Returns an empty set when the filter matches nobody (results in no data).
    """
    is_admin = current_user.role == 'admin'

    # Build base query for visible student IDs
    if is_admin and not course_id and not user_id:
        return None  # admin with no filters = everything

    if course_id:
        # Validate instructor owns this course (skip for admin)
        if not is_admin:
            course = db.query(Course).filter(
                Course.id == course_id,
                Course.instructor_id == current_user.id,
            ).first()
            if not course:
                raise HTTPException(status_code=403, detail="Not your course")
        enrolled = db.query(CourseEnrollment.user_id).filter(
            CourseEnrollment.course_id == course_id,
        ).distinct().all()
        student_ids = {r[0] for r in enrolled}
    elif is_admin:
        student_ids = None  # admin without course filter
    else:
        # Instructor without course filter: all their students
        rows = db.query(CourseEnrollment.user_id).join(
            Course, Course.id == CourseEnrollment.course_id,
        ).filter(
            Course.instructor_id == current_user.id,
            Course.is_active == True,
        ).distinct().all()
        student_ids = {r[0] for r in rows}

    # Narrow to specific user
    if user_id:
        if student_ids is None:
            # Admin: trust the user_id directly
            student_ids = {user_id}
        elif user_id in student_ids:
            student_ids = {user_id}
        else:
            raise HTTPException(status_code=403, detail="User not in scope")

    return student_ids


# ==================== Instructor Endpoints ====================

@router.get("/instructor/stats")
async def instructor_stats(
    tz_offset: int = Query(0, description="Client UTC offset in minutes (e.g. -300 for CDT)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Rich stat card data for the instructor Ops Center.

    Admins see platform-wide stats.  Instructors see only students
    enrolled in courses they own.  *tz_offset* (minutes) adjusts
    "today" to the client's local midnight.
    """
    now = datetime.now(timezone.utc)
    # Compute local midnight in UTC terms
    local_now = now + timedelta(minutes=tz_offset)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(minutes=tz_offset)
    yesterday_start = today_start - timedelta(days=1)

    # ── Scope: which student IDs does this user see? ─────────
    # Admins see everyone; instructors see their enrolled students.
    student_ids = None  # None means "no filter"
    if current_user.role != 'admin':
        rows = db.query(CourseEnrollment.user_id).join(
            Course, Course.id == CourseEnrollment.course_id,
        ).filter(
            Course.instructor_id == current_user.id,
            Course.is_active == True,
        ).distinct().all()
        student_ids = {r[0] for r in rows}

    admin_ids = _admin_user_ids(db)

    def _scoped(q, user_col):
        """Apply student scope filter and exclude admin/diagnostic actors."""
        if student_ids is not None:
            q = q.filter(user_col.in_(student_ids)) if student_ids else q.filter(False)
        if admin_ids:
            q = q.filter(~user_col.in_(admin_ids))
        return q

    # ── Flags Today ──────────────────────────────────────────
    q = db.query(func.count(FlagAttempt.id)).filter(
        FlagAttempt.is_correct == True,
        FlagAttempt.attempted_at >= today_start,
    )
    flags_today = _scoped(q, FlagAttempt.user_id).scalar() or 0

    q = db.query(func.count(FlagAttempt.id)).filter(
        FlagAttempt.is_correct == True,
        FlagAttempt.attempted_at >= yesterday_start,
        FlagAttempt.attempted_at < today_start,
    )
    flags_yesterday = _scoped(q, FlagAttempt.user_id).scalar() or 0

    q = db.query(func.count(func.distinct(FlagAttempt.user_id))).filter(
        FlagAttempt.is_correct == True,
        FlagAttempt.attempted_at >= today_start,
    )
    flag_students_today = _scoped(q, FlagAttempt.user_id).scalar() or 0

    # Last 7 days sparkline
    week_start = today_start - timedelta(days=6)
    q = db.query(
        func.date_trunc('day', FlagAttempt.attempted_at).label('day'),
        func.count(FlagAttempt.id),
    ).filter(
        FlagAttempt.is_correct == True,
        FlagAttempt.attempted_at >= week_start,
    )
    spark_rows = _scoped(q, FlagAttempt.user_id).group_by('day').order_by('day').all()
    spark_map = {r[0].date(): r[1] for r in spark_rows}
    flags_sparkline = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).date()
        flags_sparkline.append(spark_map.get(d, 0))

    # ── Active Exercises ─────────────────────────────────────
    q = db.query(LabSession, User.username).join(
        User, User.id == LabSession.user_id
    ).filter(LabSession.status == "running")
    if student_ids is not None:
        q = q.filter(LabSession.user_id.in_(student_ids)) if student_ids else q.filter(False)
    if admin_ids:
        q = q.filter(~LabSession.user_id.in_(admin_ids))
    active_sessions = q.all()

    active_users = [
        {"username": username, "lab_id": s.lab_id}
        for s, username in active_sessions
    ]

    # ── Avg Completion ───────────────────────────────────────
    q = db.query(func.avg(LabCompletion.time_spent_minutes)).filter(
        LabCompletion.completed_at >= today_start,
        LabCompletion.time_spent_minutes.isnot(None),
        LabCompletion.time_spent_minutes > 0,
    )
    avg_time_today = _scoped(q, LabCompletion.user_id).scalar()

    month_start = today_start - timedelta(days=30)
    q = db.query(func.avg(LabCompletion.time_spent_minutes)).filter(
        LabCompletion.completed_at >= month_start,
        LabCompletion.time_spent_minutes.isnot(None),
        LabCompletion.time_spent_minutes > 0,
    )
    avg_time_typical = _scoped(q, LabCompletion.user_id).scalar()

    return {
        "flags_today": flags_today,
        "flags_yesterday": flags_yesterday,
        "flag_students_today": flag_students_today,
        "flags_sparkline": flags_sparkline,
        "active_count": len(active_users),
        "active_users": active_users,
        "avg_completion_min": round(avg_time_today) if avg_time_today else None,
        "avg_completion_typical": round(avg_time_typical) if avg_time_typical else None,
    }


@router.get("/instructor/pulse")
async def instructor_pulse(
    start: Optional[str] = Query(None, description="ISO 8601 start datetime"),
    end: Optional[str] = Query(None, description="ISO 8601 end datetime"),
    course_id: Optional[int] = Query(None, description="Filter to a specific course"),
    user_id: Optional[int] = Query(None, description="Filter to a specific user"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Hourly or daily data points for The Pulse chart."""
    now = datetime.now(timezone.utc)

    # Parse start/end or default to last 24 hours
    if start:
        try:
            range_start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start datetime format")
    else:
        range_start = now - timedelta(hours=24)

    if end:
        try:
            range_end = datetime.fromisoformat(end.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end datetime format")
    else:
        range_end = now

    # Determine bucket granularity: hours if range <= 48h, else days
    total_hours = (range_end - range_start).total_seconds() / 3600
    use_days = total_hours > 48
    trunc_unit = 'day' if use_days else 'hour'

    # Scope to visible students (respects course_id / user_id filters)
    student_ids = _resolve_student_scope(db, current_user, course_id, user_id)

    # Query activity_events grouped by bucket
    q = db.query(
        func.date_trunc(trunc_unit, ActivityEvent.created_at).label('bucket'),
        ActivityEvent.event_type,
        func.count(ActivityEvent.id).label('cnt'),
    ).filter(
        ActivityEvent.created_at >= range_start,
        ActivityEvent.created_at <= range_end,
    )
    q = _exclude_diagnostic(q, ActivityEvent.actor_id, db)
    if student_ids is not None:
        q = q.filter(ActivityEvent.actor_id.in_(student_ids)) if student_ids else q.filter(False)
    rows = q.group_by(
        func.date_trunc(trunc_unit, ActivityEvent.created_at),
        ActivityEvent.event_type,
    ).all()

    # Build bucket keys
    bucket_data = {}
    if use_days:
        num_days = int(total_hours // 24) + 1
        for i in range(num_days):
            d = (range_start + timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            key = d.strftime("%Y-%m-%dT00:00:00Z")
            bucket_data[key] = {"concurrent_labs": 0, "flags_submitted": 0}
    else:
        num_hours = int(total_hours) + 1
        for i in range(num_hours):
            h = (range_start + timedelta(hours=i)).replace(
                minute=0, second=0, microsecond=0
            )
            key = h.strftime("%Y-%m-%dT%H:00:00Z")
            bucket_data[key] = {"concurrent_labs": 0, "flags_submitted": 0}

    for row in rows:
        if use_days:
            bucket_key = row.bucket.strftime("%Y-%m-%dT00:00:00Z") if row.bucket else None
        else:
            bucket_key = row.bucket.strftime("%Y-%m-%dT%H:00:00Z") if row.bucket else None
        if bucket_key and bucket_key in bucket_data:
            if row.event_type == "lab_started":
                bucket_data[bucket_key]["concurrent_labs"] += row.cnt
            elif row.event_type in ("flag_correct", "flag_incorrect"):
                bucket_data[bucket_key]["flags_submitted"] += row.cnt

    data = [
        {"hour": k, "concurrent_labs": v["concurrent_labs"], "flags_submitted": v["flags_submitted"]}
        for k, v in bucket_data.items()
    ]

    return {"data": data, "granularity": trunc_unit}


@router.get("/instructor/feed")
async def instructor_feed(
    limit: int = 50,
    offset: int = 0,
    start: Optional[str] = Query(None, description="ISO 8601 start datetime"),
    end: Optional[str] = Query(None, description="ISO 8601 end datetime"),
    course_id: Optional[int] = Query(None, description="Filter to a specific course"),
    user_id: Optional[int] = Query(None, description="Filter to a specific user"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Paginated activity event feed for the instructor dashboard."""
    query = db.query(ActivityEvent).options(
        joinedload(ActivityEvent.actor)
    )

    # Scope to visible students (respects course_id / user_id filters)
    student_ids = _resolve_student_scope(db, current_user, course_id, user_id)
    if student_ids is not None:
        if student_ids:
            query = query.filter(ActivityEvent.actor_id.in_(student_ids))
        else:
            query = query.filter(False)

    if start:
        try:
            range_start = datetime.fromisoformat(start.replace('Z', '+00:00'))
            query = query.filter(ActivityEvent.created_at >= range_start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start datetime format")

    if end:
        try:
            range_end = datetime.fromisoformat(end.replace('Z', '+00:00'))
            query = query.filter(ActivityEvent.created_at <= range_end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end datetime format")

    events = query.order_by(
        ActivityEvent.created_at.desc()
    ).offset(offset).limit(limit).all()

    result = []
    for e in events:
        result.append({
            "id": e.id,
            "event_type": e.event_type,
            "event_label": EVENT_LABELS.get(e.event_type, e.event_type),
            "actor_id": e.actor_id,
            "actor_username": e.actor.username if e.actor else None,
            "actor_role": e.actor.role if e.actor else None,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "target_label": e.target_label,
            "detail": e.detail,
            "created_at": (e.created_at.isoformat() + "Z") if e.created_at else None,
        })

    return {"events": result, "limit": limit, "offset": offset}


@router.get("/instructor/filter-options")
async def instructor_filter_options(
    course_id: Optional[int] = Query(None, description="Get students for a specific course"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Return courses and students available to the current user for filtering."""
    is_admin = current_user.role == 'admin'

    # Courses
    if is_admin:
        courses = db.query(Course).filter(Course.is_active == True).order_by(Course.code).all()
    else:
        courses = db.query(Course).filter(
            Course.instructor_id == current_user.id,
            Course.is_active == True,
        ).order_by(Course.code).all()

    # Students (all visible, or filtered by course)
    if course_id:
        if not is_admin:
            owns = db.query(Course).filter(
                Course.id == course_id, Course.instructor_id == current_user.id
            ).first()
            if not owns:
                raise HTTPException(status_code=403, detail="Not your course")
        students_q = db.query(User).join(
            CourseEnrollment, CourseEnrollment.user_id == User.id
        ).filter(
            CourseEnrollment.course_id == course_id,
            User.role == 'student',
        ).order_by(User.username)
    elif is_admin:
        students_q = db.query(User).filter(User.role == 'student').order_by(User.username)
    else:
        students_q = db.query(User).join(
            CourseEnrollment, CourseEnrollment.user_id == User.id
        ).join(
            Course, Course.id == CourseEnrollment.course_id
        ).filter(
            Course.instructor_id == current_user.id,
            Course.is_active == True,
            User.role == 'student',
        ).distinct().order_by(User.username)

    students = students_q.all()

    return {
        "courses": [{"id": c.id, "code": c.code, "name": c.name} for c in courses],
        "students": [{"id": s.id, "username": s.username} for s in students],
    }


@router.get("/instructor/report")
async def instructor_report(
    format: str = Query("pdf", description="Report format: 'pdf' or 'csv'"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    course_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    range_label: Optional[str] = Query(None, description="Human label for window e.g. 'Last 7 days'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Download a report of the currently filtered dashboard view.

    Includes: student details (or per-student summary), an activity graphic,
    and the filtered activity log.
    """
    fmt = (format or "pdf").lower()
    if fmt not in ("pdf", "csv"):
        raise HTTPException(status_code=400, detail="format must be 'pdf' or 'csv'")

    # Parse range (default last 24 h)
    now = datetime.now(timezone.utc)
    try:
        range_start = datetime.fromisoformat(start.replace('Z', '+00:00')) if start else now - timedelta(hours=24)
        range_end = datetime.fromisoformat(end.replace('Z', '+00:00')) if end else now
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    student_ids = _resolve_student_scope(db, current_user, course_id, user_id)

    admin_ids = _admin_user_ids(db)

    def _scope(q, col):
        if student_ids is not None:
            q = q.filter(col.in_(student_ids)) if student_ids else q.filter(False)
        if admin_ids:
            q = q.filter(~col.in_(admin_ids))
        return q

    # ── Fetch events ─────────────────────────────────────────
    ev_q = db.query(ActivityEvent).options(joinedload(ActivityEvent.actor)).filter(
        ActivityEvent.created_at >= range_start,
        ActivityEvent.created_at <= range_end,
    )
    ev_q = _scope(ev_q, ActivityEvent.actor_id)
    events_rows = ev_q.order_by(ActivityEvent.created_at.desc()).limit(5000).all()

    events = []
    for e in events_rows:
        events.append({
            "id": e.id,
            "event_type": e.event_type,
            "event_label": EVENT_LABELS.get(e.event_type, e.event_type),
            "actor_username": e.actor.username if e.actor else None,
            "actor_role": e.actor.role if e.actor else None,
            "target_label": e.target_label,
            "detail": e.detail,
            "created_at": e.created_at,
        })

    # ── Scope / labels ───────────────────────────────────────
    course = db.query(Course).filter(Course.id == course_id).first() if course_id else None
    target_user = db.query(User).filter(User.id == user_id).first() if user_id else None

    scope_parts = []
    if course:
        scope_parts.append(f"{course.code} - {course.name}")
    if target_user:
        scope_parts.append(f"Student: {target_user.username}")
    if not scope_parts:
        scope_parts.append("All visible activity")
    scope_label = " / ".join(scope_parts)

    filters = {
        "range_label": range_label or f"{range_start.isoformat()} to {range_end.isoformat()}",
        "start_local": range_start.astimezone(REPORT_LOCAL_TZ).strftime("%Y-%m-%d %H:%M"),
        "end_local": range_end.astimezone(REPORT_LOCAL_TZ).strftime("%Y-%m-%d %H:%M"),
        "scope_label": scope_label,
        "course_code": course.code if course else None,
    }

    # ── Per-student summary (always computed; used for both single + list) ──
    def _summary_for(uid: int) -> dict:
        flags_c = db.query(func.count(FlagAttempt.id)).filter(
            FlagAttempt.user_id == uid,
            FlagAttempt.is_correct == True,
            FlagAttempt.attempted_at >= range_start,
            FlagAttempt.attempted_at <= range_end,
        ).scalar() or 0
        flags_w = db.query(func.count(FlagAttempt.id)).filter(
            FlagAttempt.user_id == uid,
            FlagAttempt.is_correct == False,
            FlagAttempt.attempted_at >= range_start,
            FlagAttempt.attempted_at <= range_end,
        ).scalar() or 0
        labs_done = db.query(func.count(LabCompletion.id)).filter(
            LabCompletion.user_id == uid,
            LabCompletion.completed_at >= range_start,
            LabCompletion.completed_at <= range_end,
        ).scalar() or 0
        sess = db.query(func.count(LabSession.id)).filter(
            LabSession.user_id == uid,
            LabSession.started_at >= range_start,
            LabSession.started_at <= range_end,
        ).scalar() or 0
        return {
            "flags_correct": flags_c,
            "flags_wrong": flags_w,
            "labs_completed": labs_done,
            "sessions_started": sess,
        }

    student_detail = None
    students_summary = []
    if target_user:
        s = _summary_for(target_user.id)
        student_detail = {
            "username": target_user.username,
            "email": target_user.email,
            "role": target_user.role,
            **s,
        }
    else:
        # Find students active in the window within scope
        active_q = db.query(User).join(
            ActivityEvent, ActivityEvent.actor_id == User.id
        ).filter(
            ActivityEvent.created_at >= range_start,
            ActivityEvent.created_at <= range_end,
        )
        if student_ids is not None:
            active_q = active_q.filter(User.id.in_(student_ids)) if student_ids else active_q.filter(False)
        active_users = active_q.distinct().order_by(User.username).all()
        for u in active_users:
            row = {"username": u.username, **_summary_for(u.id)}
            students_summary.append(row)

    # ── Pulse buckets (reuse logic from instructor_pulse) ────
    total_hours = (range_end - range_start).total_seconds() / 3600
    use_days = total_hours > 48
    trunc_unit = 'day' if use_days else 'hour'

    pq = db.query(
        func.date_trunc(trunc_unit, ActivityEvent.created_at).label('bucket'),
        ActivityEvent.event_type,
        func.count(ActivityEvent.id).label('cnt'),
    ).filter(
        ActivityEvent.created_at >= range_start,
        ActivityEvent.created_at <= range_end,
    )
    pq = _scope(pq, ActivityEvent.actor_id)
    pulse_rows = pq.group_by(
        func.date_trunc(trunc_unit, ActivityEvent.created_at),
        ActivityEvent.event_type,
    ).all()

    bucket_data = {}
    if use_days:
        num_days = int(total_hours // 24) + 1
        for i in range(num_days):
            d = (range_start + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            key = d.strftime("%Y-%m-%dT00:00:00Z")
            bucket_data[key] = {"hour": key, "concurrent_labs": 0, "flags_submitted": 0}
    else:
        num_hours = int(total_hours) + 1
        for i in range(num_hours):
            h = (range_start + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
            key = h.strftime("%Y-%m-%dT%H:00:00Z")
            bucket_data[key] = {"hour": key, "concurrent_labs": 0, "flags_submitted": 0}

    for row in pulse_rows:
        if use_days:
            bkey = row.bucket.strftime("%Y-%m-%dT00:00:00Z") if row.bucket else None
        else:
            bkey = row.bucket.strftime("%Y-%m-%dT%H:00:00Z") if row.bucket else None
        if bkey and bkey in bucket_data:
            if row.event_type == "lab_started":
                bucket_data[bkey]["concurrent_labs"] += row.cnt
            elif row.event_type in ("flag_correct", "flag_incorrect"):
                bucket_data[bkey]["flags_submitted"] += row.cnt

    pulse = list(bucket_data.values())

    # ── Build filename ───────────────────────────────────────
    stamp = datetime.now(REPORT_LOCAL_TZ).strftime("%Y%m%d_%H%M")
    name_parts = ["ops_report", stamp]
    if course:
        name_parts.append(course.code.replace(" ", "_"))
    if target_user:
        name_parts.append(target_user.username)
    base_name = "_".join(name_parts)

    if fmt == "pdf":
        pdf_bytes = generate_dashboard_report(
            filters=filters,
            student=student_detail,
            students=students_summary,
            pulse=pulse,
            pulse_granularity=trunc_unit,
            events=events,
        )
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'},
        )

    # CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["# OpenCyberRange Ops Center Report"])
    writer.writerow(["# Scope", scope_label])
    writer.writerow(["# Range", filters["range_label"]])
    writer.writerow(["# Window (CT)", f"{filters['start_local']} to {filters['end_local']}"])
    writer.writerow([])

    if student_detail:
        writer.writerow(["# Student Details"])
        writer.writerow(["username", "email", "role", "flags_correct", "flags_wrong", "labs_completed", "sessions_started"])
        writer.writerow([
            student_detail["username"], student_detail.get("email") or "",
            student_detail.get("role") or "", student_detail["flags_correct"],
            student_detail["flags_wrong"], student_detail["labs_completed"],
            student_detail["sessions_started"],
        ])
        writer.writerow([])
    elif students_summary:
        writer.writerow(["# Students in Window"])
        writer.writerow(["username", "flags_correct", "flags_wrong", "labs_completed", "sessions_started"])
        for s in students_summary:
            writer.writerow([s["username"], s["flags_correct"], s["flags_wrong"],
                             s["labs_completed"], s["sessions_started"]])
        writer.writerow([])

    writer.writerow(["# Activity Pulse"])
    writer.writerow(["bucket", "concurrent_labs", "flags_submitted"])
    for p in pulse:
        writer.writerow([p["hour"], p["concurrent_labs"], p["flags_submitted"]])
    writer.writerow([])

    writer.writerow(["# Activity Log"])
    writer.writerow(["time_ct", "user", "role", "event", "target", "detail"])
    for e in events:
        ts = e["created_at"]
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_str = ts.astimezone(REPORT_LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = str(ts or "")
        writer.writerow([
            ts_str,
            e.get("actor_username") or "System",
            e.get("actor_role") or "",
            e.get("event_label") or e.get("event_type") or "",
            e.get("target_label") or "",
            (e.get("detail") or "").replace("\n", " ") if isinstance(e.get("detail"), str) else (e.get("detail") or ""),
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{base_name}.csv"'},
    )


# ==================== ICS Attack Coverage ====================

import os as _os
import yaml as _yaml

# Canonical taxonomy lives alongside the backend (app/data) so this endpoint and
# tools/ics-coverage/coverage_matrix.py read a single source.
_ICS_TAXONOMY_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "data", "ics_attack_taxonomy.yaml",
)


def _load_ics_taxonomy():
    """Return (tactic_order, tactic_names, id_to_meta) from the canonical taxonomy.

    tactic_order preserves kill-chain order; id_to_meta maps a technique id to
    {tactic, name, aliases}.
    """
    with open(_ICS_TAXONOMY_PATH) as fh:
        data = _yaml.safe_load(fh) or {}
    tactics = data.get("tactics", {})
    tactic_order = list(tactics.keys())
    tactic_names = {k: v.get("name", k) for k, v in tactics.items()}
    id_to_meta = {}
    for tkey, tval in tactics.items():
        for tech in tval.get("techniques", []):
            id_to_meta[tech["id"]] = {
                "tactic": tkey,
                "name": tech["name"],
                "aliases": tech.get("aliases", []),
            }
    return tactic_order, tactic_names, id_to_meta


@router.get("/instructor/ics-coverage")
async def ics_attack_coverage(
    track: Optional[str] = Query(None, description="Track slug to scope to; default all tracks with tags"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """ICS ATT&CK coverage matrix per track, computed from lab ics_techniques tags.

    For each track: labs tagged vs total, techniques covered vs taxonomy total,
    a per-tactic heatmap (covered/total + lab count), the covered techniques with
    the labs that teach them, the gaps (taxonomy techniques no lab covers), and
    the untagged labs. Drives the instructor coverage view.
    """
    tactic_order, tactic_names, id_to_meta = _load_ics_taxonomy()

    tactic_techs = {t: [] for t in tactic_order}
    for tid, meta in id_to_meta.items():
        tactic_techs[meta["tactic"]].append(tid)
    total_tech = len(id_to_meta)

    q = (
        db.query(Lab.slug, Lab.name, Lab.ics_techniques, Track.slug, Track.name)
        .join(Level, Lab.level_id == Level.id)
        .join(Track, Level.track_id == Track.id)
    )
    if track:
        q = q.filter(Track.slug == track)

    tracks = {}
    for lab_slug, lab_name, ics_json, tslug, tname in q.all():
        tr = tracks.setdefault(tslug, {"slug": tslug, "name": tname, "labs": []})
        tr["labs"].append({"slug": lab_slug, "name": lab_name, "ics": ics_json})

    results = []
    for tslug, tr in tracks.items():
        tech_to_labs = {}
        tagged, untagged = [], []
        for lab in tr["labs"]:
            try:
                tags = json.loads(lab["ics"]) if lab["ics"] else []
            except (ValueError, TypeError):
                tags = []
            if not tags:
                untagged.append({"slug": lab["slug"], "name": lab["name"]})
                continue
            tagged.append(lab["slug"])
            for entry in tags:
                tid = entry.get("technique_id")
                if not tid:
                    continue
                tech_to_labs.setdefault(tid, []).append(
                    {"slug": lab["slug"], "name": lab["name"], "note": entry.get("note", "")}
                )

        # A track with no tagged labs is noise unless the caller asked for it.
        if not tagged and not track:
            continue

        tactics_out, gaps = [], []
        for t in tactic_order:
            techs = tactic_techs[t]
            covered_ids = [tid for tid in techs if tid in tech_to_labs]
            missing_ids = [tid for tid in techs if tid not in tech_to_labs]
            lab_set = {l["slug"] for tid in covered_ids for l in tech_to_labs[tid]}
            tactics_out.append({
                "key": t,
                "name": tactic_names[t],
                "covered": len(covered_ids),
                "total": len(techs),
                "lab_count": len(lab_set),
                "techniques": [
                    {
                        "id": tid,
                        "name": id_to_meta[tid]["name"],
                        "aliases": id_to_meta[tid]["aliases"],
                        "labs": tech_to_labs[tid],
                    }
                    for tid in covered_ids
                ],
            })
            if missing_ids:
                gaps.append({
                    "tactic": tactic_names[t],
                    "techniques": [{"id": tid, "name": id_to_meta[tid]["name"]} for tid in missing_ids],
                })

        results.append({
            "slug": tslug,
            "name": tr["name"],
            "labs_total": len(tr["labs"]),
            "labs_tagged": len(tagged),
            "techniques_covered": sum(1 for tid in id_to_meta if tid in tech_to_labs),
            "techniques_total": total_tech,
            "tactics_total": len(tactic_order),
            "tactics_touched": sum(1 for to in tactics_out if to["covered"] > 0),
            "tactics": tactics_out,
            "gaps": gaps,
            "untagged_labs": untagged,
        })

    results.sort(key=lambda r: r["slug"])
    return {"tracks": results}


# ==================== Student Endpoint ====================

@router.get("/student")
async def student_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Student dashboard: next objective, progress, VPN, rank."""

    # --- Progress ---
    tracks = db.query(Track).options(
        joinedload(Track.levels).joinedload(Level.labs)
    ).filter(Track.is_active == True).all()

    # Get accessible exclusive labs
    now_utc = datetime.now(timezone.utc)
    exclusive_rows = db.query(CourseLabAssignment.lab_id).join(
        CourseEnrollment,
        CourseEnrollment.course_id == CourseLabAssignment.course_id,
    ).join(
        Course,
        Course.id == CourseLabAssignment.course_id,
    ).filter(
        CourseEnrollment.user_id == current_user.id,
        Course.end_date >= now_utc,
        Course.is_active == True,
    ).all()
    accessible_exclusive_ids = {r[0] for r in exclusive_rows}

    completed_ids = {
        r[0] for r in db.query(LabCompletion.lab_id).filter(
            LabCompletion.user_id == current_user.id,
            LabCompletion.flag_submitted.isnot(None),
            LabCompletion.flag_submitted != "",
        ).all()
    }

    total_labs = 0
    completed_labs = 0
    next_objective = None

    for track in tracks:
        for level in sorted(track.levels, key=lambda l: l.level_number):
            for lab in sorted(level.labs, key=lambda l: l.sort_order):
                # Visibility check
                if not current_user.is_admin:
                    if not lab.is_active:
                        continue
                    if getattr(lab, 'is_course_exclusive', False) and lab.id not in accessible_exclusive_ids:
                        continue
                total_labs += 1
                if lab.id in completed_ids:
                    completed_labs += 1
                elif next_objective is None:
                    next_objective = {
                        "lab_id": lab.id,
                        "lab_name": lab.name,
                        "lab_slug": lab.slug,
                        "track_name": track.name,
                        "track_slug": track.slug,
                        "level_name": level.name,
                    }

    progress_percent = round(completed_labs / total_labs * 100) if total_labs > 0 else 0

    # --- VPN status ---
    wg_config = db.query(WireGuardConfig).filter(
        WireGuardConfig.user_id == current_user.id
    ).first()

    vpn_status = {
        "has_config": wg_config is not None,
        "vpn_registered": current_user.vpn_registered if wg_config else False,
        "client_ip": wg_config.client_ip if wg_config else None,
    }

    # --- Scoreboard rank (first enrolled active course) ---
    scoreboard_rank = None
    course_name = None

    enrollment = db.query(CourseEnrollment).join(
        Course
    ).filter(
        CourseEnrollment.user_id == current_user.id,
        Course.is_active == True,
    ).first()

    if enrollment:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            course_name = f"{course.code}"

            # Get assigned lab IDs
            assigned_lab_ids = [
                r[0] for r in db.query(CourseLabAssignment.lab_id).filter(
                    CourseLabAssignment.course_id == course.id,
                ).all()
            ]

            if assigned_lab_ids:
                # Single aggregated query: compute scores for all enrolled
                # students in one pass instead of N separate queries.
                from sqlalchemy import case, literal_column
                score_expr = (
                    func.count(LabCompletion.id) * 100
                    + func.sum(case((LabCompletion.hints_used == 0, 25), else_=0))
                    + func.sum(case((LabCompletion.attempts == 1, 25), else_=0))
                )
                score_rows = (
                    db.query(CourseEnrollment.user_id, func.coalesce(score_expr, 0).label("total_score"))
                    .outerjoin(
                        LabCompletion,
                        (LabCompletion.user_id == CourseEnrollment.user_id)
                        & LabCompletion.lab_id.in_(assigned_lab_ids)
                        & LabCompletion.flag_submitted.isnot(None)
                        & (LabCompletion.flag_submitted != ""),
                    )
                    .filter(CourseEnrollment.course_id == course.id)
                    .group_by(CourseEnrollment.user_id)
                    .order_by(func.coalesce(score_expr, 0).desc())
                    .all()
                )
                for rank, (uid, score) in enumerate(score_rows, 1):
                    if uid == current_user.id:
                        scoreboard_rank = rank
                        break

    return {
        "next_objective": next_objective,
        "progress_percent": progress_percent,
        "total_labs": total_labs,
        "completed_labs": completed_labs,
        "vpn_status": vpn_status,
        "scoreboard_rank": scoreboard_rank,
        "course_name": course_name,
    }
