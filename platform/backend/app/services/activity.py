"""
Activity event logging service for dashboard feeds and analytics.
"""

import json
import logging
from sqlalchemy.orm import Session
from app.models import ActivityEvent

logger = logging.getLogger(__name__)


class EventTypes:
    LAB_STARTED = "lab_started"
    LAB_STOPPED = "lab_stopped"
    LAB_COMPLETED = "lab_completed"
    FLAG_CORRECT = "flag_correct"
    FLAG_INCORRECT = "flag_incorrect"
    HINT_USED = "hint_used"
    USER_REGISTERED = "user_registered"
    USER_APPROVED = "user_approved"
    SESSION_EXPIRED = "session_expired"
    VPN_DOWNLOADED = "vpn_downloaded"
    COURSE_ENROLLED = "course_enrolled"
    ACHIEVEMENT_AWARDED = "achievement_awarded"
    IMPERSONATION_START = "impersonation_start"
    IMPERSONATION_END = "impersonation_end"


# Human-readable labels for the feed
EVENT_LABELS = {
    EventTypes.LAB_STARTED: "Started Lab",
    EventTypes.LAB_STOPPED: "Stopped Lab",
    EventTypes.LAB_COMPLETED: "Completed Lab",
    EventTypes.FLAG_CORRECT: "Solved",
    EventTypes.FLAG_INCORRECT: "Wrong Flag",
    EventTypes.HINT_USED: "Used Hint",
    EventTypes.USER_REGISTERED: "Registered",
    EventTypes.USER_APPROVED: "Approved",
    EventTypes.SESSION_EXPIRED: "Session Expired",
    EventTypes.VPN_DOWNLOADED: "Downloaded VPN",
    EventTypes.COURSE_ENROLLED: "Enrolled in Course",
    EventTypes.ACHIEVEMENT_AWARDED: "Achievement Earned",
    EventTypes.IMPERSONATION_START: "Started Impersonation",
    EventTypes.IMPERSONATION_END: "Ended Impersonation",
}


def log_activity(
    db: Session,
    event_type: str,
    actor_id: int = None,
    target_type: str = None,
    target_id: int = None,
    target_label: str = None,
    detail: dict = None,
    ip_address: str = None,
    commit: bool = True,
):
    """Log an activity event to the database."""
    try:
        event = ActivityEvent(
            event_type=event_type,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            detail=json.dumps(detail) if detail else None,
            ip_address=ip_address,
        )
        db.add(event)
        if commit:
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to log activity event {event_type}: {e}")
        if commit:
            try:
                db.rollback()
            except Exception:
                pass
