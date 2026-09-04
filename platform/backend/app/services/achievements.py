"""
Achievement checking and awarding logic.
Called after successful flag submissions to award micro-credentials.
"""

import logging
from sqlalchemy.orm import Session
from app.models import (
    Achievement, Course, CourseEnrollment, CourseLabAssignment,
    CourseCompletionReset, Lab, LabCompletion
)
from app.services.activity import log_activity, EventTypes

logger = logging.getLogger(__name__)

# Achievement type constants
FIRST_BLOOD = "first_blood"
NO_HINTS = "no_hints"
PERFECTIONIST = "perfectionist"
SPEED_DEMON = "speed_demon"
CLEAN_SWEEP = "clean_sweep"
STREAK = "streak"

ACHIEVEMENT_LABELS = {
    FIRST_BLOOD: "First Blood",
    NO_HINTS: "Self-Reliant",
    PERFECTIONIST: "Perfectionist",
    SPEED_DEMON: "Speed Demon",
    CLEAN_SWEEP: "Clean Sweep",
    STREAK: "On a Roll",
}

ACHIEVEMENT_DESCRIPTIONS = {
    FIRST_BLOOD: "First student in the course to complete this lab",
    NO_HINTS: "Completed a lab without using any hints",
    PERFECTIONIST: "Completed a lab on the first flag attempt",
    SPEED_DEMON: "Completed a lab in under half the estimated time",
    CLEAN_SWEEP: "Completed all assigned labs in the course",
    STREAK: "Completed 3+ labs in a row with no hints and first attempt",
}


def _award(db: Session, user_id: int, course_id: int, lab_id: int | None, achievement_type: str):
    """Award an achievement if not already awarded (idempotent)."""
    query = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.course_id == course_id,
        Achievement.achievement_type == achievement_type,
    )
    if lab_id is not None:
        query = query.filter(Achievement.lab_id == lab_id)
    else:
        query = query.filter(Achievement.lab_id.is_(None))

    if query.first():
        return

    db.add(Achievement(
        user_id=user_id,
        course_id=course_id,
        lab_id=lab_id,
        achievement_type=achievement_type,
    ))
    logger.info(
        f"Awarded {achievement_type} to user {user_id} "
        f"in course {course_id} for lab {lab_id}"
    )
    log_activity(db, EventTypes.ACHIEVEMENT_AWARDED,
                  actor_id=user_id, target_type="achievement",
                  target_id=lab_id,
                  target_label=ACHIEVEMENT_LABELS.get(achievement_type, achievement_type),
                  commit=False)


def check_achievements(db: Session, user_id: int, lab_id: int):
    """Check and award achievements for all courses this user+lab belongs to.

    Called after a successful flag submission and db.commit().
    """
    # Find courses where user is enrolled AND this lab is assigned
    course_ids = db.query(CourseEnrollment.course_id).filter(
        CourseEnrollment.user_id == user_id
    ).all()
    course_ids = {r[0] for r in course_ids}

    if not course_ids:
        return

    assignments = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id.in_(course_ids),
        CourseLabAssignment.lab_id == lab_id,
    ).all()

    if not assignments:
        return

    # Get the completion record
    completion = db.query(LabCompletion).filter(
        LabCompletion.user_id == user_id,
        LabCompletion.lab_id == lab_id,
        LabCompletion.flag_submitted.isnot(None),
        LabCompletion.flag_submitted != "",
    ).first()

    if not completion:
        return

    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        return

    for assignment in assignments:
        course_id = assignment.course_id

        # Get enrollment date and resets for course-aware filtering
        enrollment = db.query(CourseEnrollment).filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == user_id,
        ).first()
        if not enrollment:
            continue
        enrolled_at = enrollment.enrolled_at

        # Build reset map for this user+course
        resets = db.query(CourseCompletionReset).filter(
            CourseCompletionReset.course_id == course_id,
            CourseCompletionReset.user_id == user_id,
        ).all()
        reset_map = {}
        for r in resets:
            if r.lab_id not in reset_map or r.reset_at > reset_map[r.lab_id]:
                reset_map[r.lab_id] = r.reset_at

        def _valid_in_course(c):
            """Check if a completion counts in this course context."""
            if not c or not c.completed_at or not c.flag_submitted:
                return False
            if c.completed_at < enrolled_at:
                return False
            lr = reset_map.get(c.lab_id)
            if lr and c.completed_at <= lr:
                return False
            return True

        # Verify current completion is valid in this course
        if not _valid_in_course(completion):
            continue

        # --- first_blood: first in course to complete this lab (course-aware) ---
        all_enrolled_ids = [
            r[0] for r in db.query(CourseEnrollment.user_id).filter(
                CourseEnrollment.course_id == course_id
            ).all()
        ]
        all_completions = db.query(LabCompletion).filter(
            LabCompletion.user_id.in_(all_enrolled_ids),
            LabCompletion.lab_id == lab_id,
            LabCompletion.flag_submitted.isnot(None),
            LabCompletion.flag_submitted != "",
        ).all()

        # Build per-user enrollment dates and resets for first_blood
        enrollment_dates = {
            r.user_id: r.enrolled_at
            for r in db.query(CourseEnrollment).filter(
                CourseEnrollment.course_id == course_id
            ).all()
        }
        all_resets = db.query(CourseCompletionReset).filter(
            CourseCompletionReset.course_id == course_id,
            CourseCompletionReset.lab_id == lab_id,
        ).all()
        all_reset_map = {}
        for r in all_resets:
            key = r.user_id
            if key not in all_reset_map or r.reset_at > all_reset_map[key]:
                all_reset_map[key] = r.reset_at

        first_completer_id = None
        earliest_time = None
        for c in all_completions:
            uid = c.user_id
            ea = enrollment_dates.get(uid)
            if not ea or not c.completed_at or c.completed_at < ea:
                continue
            lr = all_reset_map.get(uid)
            if lr and c.completed_at <= lr:
                continue
            if earliest_time is None or c.completed_at < earliest_time:
                earliest_time = c.completed_at
                first_completer_id = uid

        if first_completer_id == user_id:
            _award(db, user_id, course_id, lab_id, FIRST_BLOOD)

        # --- no_hints: completed with 0 hints ---
        if completion.hints_used == 0:
            _award(db, user_id, course_id, lab_id, NO_HINTS)

        # --- perfectionist: completed on first attempt ---
        if completion.attempts == 1:
            _award(db, user_id, course_id, lab_id, PERFECTIONIST)

        # --- speed_demon: under half the estimated time ---
        if (completion.time_spent_minutes
                and lab.duration_minutes
                and completion.time_spent_minutes < lab.duration_minutes * 0.5):
            _award(db, user_id, course_id, lab_id, SPEED_DEMON)

        # --- clean_sweep: all assigned labs in course completed (course-aware) ---
        course_lab_ids = {
            a.lab_id for a in db.query(CourseLabAssignment).filter(
                CourseLabAssignment.course_id == course_id
            ).all()
        }
        from app.routers.courses import get_course_completed_lab_ids
        user_completed = get_course_completed_lab_ids(db, user_id, course_id, course_lab_ids)
        if course_lab_ids and course_lab_ids.issubset(user_completed):
            _award(db, user_id, course_id, None, CLEAN_SWEEP)

        # --- streak: 3+ completions in a row, all no hints + first attempt (course-aware) ---
        recent_all = db.query(LabCompletion).filter(
            LabCompletion.user_id == user_id,
            LabCompletion.lab_id.in_(course_lab_ids),
            LabCompletion.flag_submitted.isnot(None),
            LabCompletion.flag_submitted != "",
        ).order_by(LabCompletion.completed_at.desc()).all()

        recent_valid = [c for c in recent_all if _valid_in_course(c)][:3]

        if (len(recent_valid) >= 3
                and all(c.hints_used == 0 and c.attempts == 1 for c in recent_valid)):
            _award(db, user_id, course_id, None, STREAK)

    db.commit()
